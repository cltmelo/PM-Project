"""
bpmn_exporter.py - Export the discovered process model to BPMN/PNML format
"""

import os
from typing import Dict, Set, Tuple, List
from collections import defaultdict
import xml.etree.ElementTree as ET
from xml.dom import minidom


class BPMNExporter:
    """Export process model to BPMN 2.0 XML format."""

    BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
    PNML_NS = "http://www.pnml.org/version-2009/grammar/pnmlcoremodel"

    def __init__(self):
        self.process_id = "SplitMinerProcess"
        self.elements = []
        self.flows = []

    def export_bpmn(self,
                    dfg: Dict[Tuple[str, str], int],
                    split_gateways: Dict[str, str],
                    join_gateways: Dict[str, str],
                    concurrent_pairs: Set[Tuple[str, str]],
                    loop_info: dict,
                    output_path: str) -> str:
        """
        Export the discovered process model to BPMN file.
        """
        # Build BPMN XML structure
        definitions = ET.Element('{%s}definitions' % self.BPMN_NS)
        definitions.set('{%s}typeLanguage' % self.XSI_NS,
                       'http://www.w3.org/2001/XMLSchema')
        definitions.set('{%s}expressionLanguage' % self.XSI_NS,
                       'http://www.w3.org/1999/XPath')
        definitions.set('targetNamespace', 'http://splitminer/process')

        process = ET.SubElement(definitions, '{%s}process' % self.BPMN_NS)
        process.set('id', self.process_id)
        process.set('isExecutable', 'false')

        # Add all elements (tasks and gateways)
        self._add_activities(process, dfg)
        self._add_gateways(process, split_gateways, join_gateways, dfg)

        # Add sequence flows
        self._add_sequence_flows(process, dfg, split_gateways, join_gateways)

        # Write to file with pretty formatting
        self._write_xml(definitions, output_path)

        return output_path

    def _add_activities(self, process: ET.Element,
                        dfg: Dict[Tuple[str, str], int]):
        """Add task elements for each activity."""
        activities = set()
        for (src, tgt) in dfg.keys():
            activities.add(src)
            activities.add(tgt)

        for i, activity in enumerate(sorted(activities)):
            task = ET.SubElement(process, '{%s}task' % self.BPMN_NS)
            task.set('id', f'task_{activity}')
            task.set('name', activity)

            # BPMNDI layout omitted
            self._add_bounds(task, i * 200, 100)

    def _add_gateways(self, process: ET.Element,
                      split_gateways: Dict[str, str],
                      join_gateways: Dict[str, str],
                      dfg: Dict[Tuple[str, str], int]):
        """Add gateway elements."""
        gateway_id = 0

        # Add split gateways
        for activity, gw_type in split_gateways.items():
            gw_id = f'gateway_split_{gateway_id}'
            gateway = ET.SubElement(process, '{%s}exclusiveGateway' % self.BPMN_NS
                                   if gw_type == 'XOR'
                                   else '{%s}parallelGateway' % self.BPMN_NS)
            gateway.set('id', gw_id)
            gateway.set('name', f'{gw_type}_split_{activity}')
            gateway_id += 1

        # Add join gateways
        for activity, gw_type in join_gateways.items():
            gw_id = f'gateway_join_{gateway_id}'
            gateway = ET.SubElement(process, '{%s}exclusiveGateway' % self.BPMN_NS
                                   if gw_type == 'XOR'
                                   else '{%s}parallelGateway' % self.BPMN_NS)
            gateway.set('id', gw_id)
            gateway.set('name', f'{gw_type}_join_{activity}')
            gateway_id += 1

    def _add_sequence_flows(self, process: ET.Element,
                            dfg: Dict[Tuple[str, str], int],
                            split_gateways: Dict[str, str],
                            join_gateways: Dict[str, str]):
        """
        Add sequence flow elements WITH GATEWAY ROUTING.

        Routes flows through discovered gateways:
        - If source has split gateway: task_src → split_gateway → ...
        - If target has join gateway: ... → join_gateway → task_tgt

        FIXED: Always emit final arc to target_ref regardless of split gateway presence
        """
        flow_id = 0

        # Pre-build activity to gateway ID mappings
        activity_to_split_gw = {}
        for idx, activity in enumerate(split_gateways.keys()):
            activity_to_split_gw[activity] = f'gateway_split_{idx}'

        # Join gateway IDs start after all split gateways
        join_offset = len(split_gateways)
        activity_to_join_gw = {}
        for idx, activity in enumerate(join_gateways.keys()):
            activity_to_join_gw[activity] = f'gateway_join_{join_offset + idx}'

        for (src, tgt), freq in sorted(dfg.items(), key=lambda x: -x[1]):
            source_ref = f'task_{src}'
            target_ref = f'task_{tgt}'

            has_split = src in activity_to_split_gw
            has_join = tgt in activity_to_join_gw

            # Step 1: If source has split gateway, add arc: task_src → split_gw
            if has_split:
                split_gw_id = activity_to_split_gw[src]

                flow1 = ET.SubElement(process, '{%s}sequenceFlow' % self.BPMN_NS)
                flow1.set('id', f'flow_{flow_id}')
                flow1.set('sourceRef', source_ref)
                flow1.set('targetRef', split_gw_id)
                flow1.set('name', f'{src} → GW_split')
                flow_id += 1

                # Update source_ref to point to split gateway for subsequent arcs
                source_ref = split_gw_id

            # Step 2: Route to target (either through join gateway or directly)
            # FIXED: This ALWAYS executes, whether has_split is True or False
            if has_join:
                join_gw_id = activity_to_join_gw[tgt]

                # Flow: (source_ref may be split_gw or task_src) → join_gateway
                flow2 = ET.SubElement(process, '{%s}sequenceFlow' % self.BPMN_NS)
                flow2.set('id', f'flow_{flow_id}')
                flow2.set('sourceRef', source_ref)
                flow2.set('targetRef', join_gw_id)
                flow2.set('name', f'GW → join_{tgt}')
                flow_id += 1

                # Flow: join_gateway → task_tgt (ALWAYS required)
                flow3 = ET.SubElement(process, '{%s}sequenceFlow' % self.BPMN_NS)
                flow3.set('id', f'flow_{flow_id}')
                flow3.set('sourceRef', join_gw_id)
                flow3.set('targetRef', target_ref)
                flow3.set('name', f'join_{tgt} → {tgt}')
                flow_id += 1
            else:
                # DIRECT flow from source_ref to task_tgt
                # source_ref is either split_gw (if has_split=True) or task_src (if has_split=False)
                flow = ET.SubElement(process, '{%s}sequenceFlow' % self.BPMN_NS)
                flow.set('id', f'flow_{flow_id}')
                flow.set('sourceRef', source_ref)
                flow.set('targetRef', target_ref)
                flow.set('name', f'{src} → {tgt}')
                flow_id += 1

        print(f"  Created {flow_id} sequence flows")

    def _add_bounds(self, parent: ET.Element, x: int, y: int):
        """Add simple visualization bounds (BPMNDI)."""
        # BPMNDI layout omitted - full implementation would require
        # complete BPMNDI section with Diagram, Plane, and Shape elements
        pass

    def _write_xml(self, root: ET.Element, output_path: str):
        """Write XML tree to file with pretty formatting."""
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Convert to string with pretty printing
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Remove extra blank lines
        lines = pretty_xml.split('\n')
        pretty_xml = '\n'.join([line for line in lines if line.strip()])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

    def export_pnml(self,
                    dfg: Dict[Tuple[str, str], int],
                    output_path: str,
                    start_activities: Set[str] = None,
                    end_activities: Set[str] = None,
                    split_gateways: Dict[str, str] = None,
                    join_gateways: Dict[str, str] = None,
                    concurrent_pairs: Set[Tuple[str, str]] = None) -> str:
        """
        Export to PNML format with PROPER Petri net structure for precision calculation.

        FIX Issue 1: Create choice places for XOR splits and parallel places for AND splits
        FIX Bug 1: Track created arcs to avoid duplicates
        """
        activities = set()
        for edge, freq in dfg.items():
            src, tgt = edge
            activities.add(src)
            activities.add(tgt)
        activities = {str(act) for act in activities}

        if start_activities is None:
            targets = {tgt for (_, tgt) in dfg.keys()}
            start_activities = {act for act in activities if act not in targets}

        if end_activities is None:
            sources = {src for (src, _) in dfg.keys()}
            end_activities = {act for act in activities if act not in sources}

        if split_gateways is None:
            split_gateways = {}
        if join_gateways is None:
            join_gateways = {}
        if concurrent_pairs is None:
            concurrent_pairs = set()

        pnml = ET.Element('pnml')
        pnml.set('xmlns', 'http://www.pnml.org/version-2009/grammar/pnmlcoremodel')

        net = ET.SubElement(pnml, 'net')
        net.set('id', 'SplitMinerNet')
        net.set('type', 'http://www.pnml.org/version-2009/grammar/ptnet')

        net_name = ET.SubElement(net, 'name')
        net_text = ET.SubElement(net_name, 'text')
        net_text.text = 'SplitMiner Discovered Process Model'

        trans_id = 0
        arc_id = 0
        place_id = 0

        # ============================================================
        # START PLACE with initial marking
        # ============================================================
        start_place = ET.SubElement(net, 'place')
        start_place.set('id', 'p_start')
        place_id += 1

        start_place_name = ET.SubElement(start_place, 'name')
        start_place_text = ET.SubElement(start_place_name, 'text')
        start_place_text.text = 'Start'

        initial_marking = ET.SubElement(start_place, 'initialMarking')
        im_text = ET.SubElement(initial_marking, 'text')
        im_text.text = '1'

        # ============================================================
        # END PLACE
        # ============================================================
        end_place = ET.SubElement(net, 'place')
        end_place.set('id', 'p_end')
        place_id += 1

        end_place_name = ET.SubElement(end_place, 'name')
        end_place_text = ET.SubElement(end_place_name, 'text')
        end_place_text.text = 'End'

        # ============================================================
        # TRANSITIONS for each activity
        # ============================================================
        activity_to_transition = {}

        for activity in sorted(activities):
            trans = ET.SubElement(net, 'transition')
            trans_id_str = f't{trans_id}'
            trans.set('id', trans_id_str)

            activity_to_transition[activity] = trans_id_str

            trans_name = ET.SubElement(trans, 'name')
            trans_text = ET.SubElement(trans_name, 'text')
            trans_text.text = activity

            trans_id += 1

        # ============================================================
        # PLACES - IMPROVED STRUCTURE FOR PRECISION
        # ============================================================
        edge_to_place = {}
        activity_output_places = {}

        # Build adjacency from DFG
        successors = {}
        for activity in activities:
            successors[activity] = [tgt for (src, tgt) in dfg.keys() if src == activity]

        # Create places for each activity's outputs
        for activity in sorted(activities):
            succs = successors.get(activity, [])

            if len(succs) <= 1:
                # Simple case: one place per edge
                for tgt in succs:
                    place_id_str = f'p_{activity}_{tgt}'
                    edge_to_place[(activity, tgt)] = place_id_str

                    place = ET.SubElement(net, 'place')
                    place.set('id', place_id_str)
                    place_id += 1

                    place_name = ET.SubElement(place, 'name')
                    place_text = ET.SubElement(place_name, 'text')
                    place_text.text = f'{activity}_to_{tgt}'

                    activity_output_places.setdefault(activity, []).append(place_id_str)
            else:
                # Multiple successors - check if it's a split
                gw_type = split_gateways.get(activity, 'XOR')

                if gw_type == 'AND':
                    # AND split: single place with multiple outgoing arcs (parallelism)
                    place_id_str = f'p_split_AND_{activity}'

                    place = ET.SubElement(net, 'place')
                    place.set('id', place_id_str)
                    place_id += 1

                    place_name = ET.SubElement(place, 'name')
                    place_text = ET.SubElement(place_name, 'text')
                    place_text.text = f'AND_split_{activity}'

                    for tgt in succs:
                        edge_to_place[(activity, tgt)] = place_id_str

                    activity_output_places[activity] = [place_id_str]
                else:
                    # XOR split: single place with multiple outgoing arcs (choice)
                    place_id_str = f'p_split_XOR_{activity}'

                    place = ET.SubElement(net, 'place')
                    place.set('id', place_id_str)
                    place_id += 1

                    place_name = ET.SubElement(place, 'name')
                    place_text = ET.SubElement(place_name, 'text')
                    place_text.text = f'XOR_split_{activity}'

                    for tgt in succs:
                        edge_to_place[(activity, tgt)] = place_id_str

                    activity_output_places[activity] = [place_id_str]

        # ============================================================
        # ARCS - FIX BUG 1: Track created arcs to avoid duplicates
        # ============================================================
        created_arcs = set()  # Track (source, target) pairs
        created_src_to_place = set()  # Track (src_trans, place) pairs

        # From START PLACE to START ACTIVITY transitions
        for start_act in start_activities:
            if start_act in activity_to_transition:
                arc_key = ('p_start', activity_to_transition[start_act])
                if arc_key not in created_arcs:
                    arc = ET.SubElement(net, 'arc')
                    arc.set('id', f'arc_start_{arc_id}')
                    arc.set('source', 'p_start')
                    arc.set('target', activity_to_transition[start_act])
                    arc_id += 1
                    created_arcs.add(arc_key)

        # From END ACTIVITY transitions to END PLACE
        for end_act in end_activities:
            if end_act in activity_to_transition:
                arc_key = (activity_to_transition[end_act], 'p_end')
                if arc_key not in created_arcs:
                    arc = ET.SubElement(net, 'arc')
                    arc.set('id', f'arc_end_{arc_id}')
                    arc.set('source', activity_to_transition[end_act])
                    arc.set('target', 'p_end')
                    arc_id += 1
                    created_arcs.add(arc_key)

        # Arcs for DFG edges: transition -> place -> transition
        # FIX BUG 1: Only create ONE arc from source transition to place (not one per edge)
        for (src, tgt), freq in dfg.items():
            src_trans = activity_to_transition.get(src)
            tgt_trans = activity_to_transition.get(tgt)
            place_id_str = edge_to_place.get((src, tgt))

            if src_trans and tgt_trans and place_id_str:
                # Arc: source transition -> place (ONLY ONCE per source-place pair)
                arc_key_src = (src_trans, place_id_str)
                if arc_key_src not in created_src_to_place:
                    arc1 = ET.SubElement(net, 'arc')
                    arc1.set('id', f'arc_{arc_id}')
                    arc1.set('source', src_trans)
                    arc1.set('target', place_id_str)
                    arc_id += 1
                    created_arcs.add(arc_key_src)
                    created_src_to_place.add(arc_key_src)

                # Arc: place -> target transition (one per edge, this is correct)
                arc_key_tgt = (place_id_str, tgt_trans)
                if arc_key_tgt not in created_arcs:
                    arc2 = ET.SubElement(net, 'arc')
                    arc2.set('id', f'arc_{arc_id}')
                    arc2.set('source', place_id_str)
                    arc2.set('target', tgt_trans)
                    arc_id += 1
                    created_arcs.add(arc_key_tgt)

        # ============================================================
        # FINAL MARKING at NET LEVEL
        # ============================================================
        finalmarkings = ET.SubElement(net, 'finalmarkings')
        marking = ET.SubElement(finalmarkings, 'marking')
        place_ref = ET.SubElement(marking, 'place')
        place_ref.set('idref', 'p_end')
        fm_text = ET.SubElement(place_ref, 'text')
        fm_text.text = '1'

        # ============================================================
        # Write to file
        # ============================================================
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        xml_str = ET.tostring(pnml, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")

        lines = pretty_xml.split('\n')
        pretty_xml = '\n'.join([line for line in lines if line.strip()])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

        total_places = place_id
        print(f"  PNML structure: {len(activities)} transitions, {total_places} places, {arc_id} arcs")

        return output_path


def export_model(dfg: Dict[Tuple[str, str], int],
                 split_gateways: Dict[str, str],
                 join_gateways: Dict[str, str],
                 concurrent_pairs: Set[Tuple[str, str]],
                 loop_info: dict,
                 output_dir: str,
                 format: str = 'bpmn',
                 start_activities: Set[str] = None,
                 end_activities: Set[str] = None) -> str:
    """
    Convenience function to export process model.

    Args:
        dfg: Directly-follows graph
        split_gateways: Split gateway mapping
        join_gateways: Join gateway mapping
        concurrent_pairs: Concurrent activity pairs
        loop_info: Loop information
        output_dir: Output directory
        format: 'bpmn' or 'pnml'
        start_activities: Start activities (for PNML export)
        end_activities: End activities (for PNML export)

    Returns:
        output_file: Path to exported file
    """
    exporter = BPMNExporter()

    if format == 'bpmn':
        output_file = os.path.join(output_dir, 'result_split_miner.bpmn')
        return exporter.export_bpmn(
            dfg, split_gateways, join_gateways,
            concurrent_pairs, loop_info, output_file
        )
    elif format == 'pnml':
        output_file = os.path.join(output_dir, 'result_split_miner.pnml')
        return exporter.export_pnml(
            dfg,
            output_file,
            start_activities=start_activities,
            end_activities=end_activities,
            split_gateways=split_gateways,
            join_gateways=join_gateways,
            concurrent_pairs=concurrent_pairs
        )
    else:
        raise ValueError(f"Unsupported format: {format}")
