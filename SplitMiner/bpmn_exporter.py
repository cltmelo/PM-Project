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

        Args:
            dfg: Directly-follows graph
            split_gateways: Split gateway types per activity
            join_gateways: Join gateway types per activity
            concurrent_pairs: Concurrent activity pairs
            loop_info: Loop structure information
            output_path: Path to save BPMN file

        Returns:
            output_path: Path to saved file
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

            # Add simple visualization bounds
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
        """Add sequence flow elements."""
        flow_id = 0

        for (src, tgt), freq in sorted(dfg.items(), key=lambda x: -x[1]):
            flow = ET.SubElement(process, '{%s}sequenceFlow' % self.BPMN_NS)
            flow.set('id', f'flow_{flow_id}')
            flow.set('sourceRef', f'task_{src}')
            flow.set('targetRef', f'task_{tgt}')
            flow.set('name', f'{src} → {tgt}')

            flow_id += 1

    def _add_bounds(self, parent: ET.Element, x: int, y: int):
        """Add simple visualization bounds (BPMNDI)."""
        # Simplified - full BPMNDI would require more complex structure
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
                    output_path: str) -> str:
        """
        Export to PNML (Petri Net Markup Language) format.
        Simpler alternative to BPMN.
        """
        pnml = ET.Element('pnml')
        pnml.set('xmlns', 'http://www.pnml.org/version-2009/grammar/pnmlcoremodel')

        net = ET.SubElement(pnml, 'net')
        net.set('id', 'SplitMinerNet')
        net.set('type', 'http://www.pnml.org/version-2009/grammar/ptnet')

        place_id = 0
        transition_id = 0

        # Create places and transitions
        activities = set()
        for (src, tgt) in dfg.keys():
            activities.add(src)
            activities.add(tgt)

        # Add transitions for each activity
        for activity in sorted(activities):
            transition = ET.SubElement(net, 'transition')
            transition.set('id', f't{transition_id}')

            name = ET.SubElement(transition, 'name')
            text = ET.SubElement(name, 'text')
            text.text = activity

            transition_id += 1

        # Add arcs
        arc_id = 0
        # Simplified arc creation - full implementation would need proper Petri net structure

        # Write to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        xml_str = ET.tostring(pnml, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        lines = pretty_xml.split('\n')
        pretty_xml = '\n'.join([line for line in lines if line.strip()])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

        return output_path


def export_model(dfg: Dict[Tuple[str, str], int],
                 split_gateways: Dict[str, str],
                 join_gateways: Dict[str, str],
                 concurrent_pairs: Set[Tuple[str, str]],
                 loop_info: dict,
                 output_dir: str,
                 format: str = 'bpmn') -> str:
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
        return exporter.export_pnml(dfg, output_file)
    else:
        raise ValueError(f"Unsupported format: {format}")
