"""
gateway_discovery.py - Discover XOR/AND split-join gateways using Split Miner heuristics
Based on: Augusto et al., "Split Miner: Automated Discovery of Accurate and Simple
Business Process Models from Event Logs" (2017)
GATEWAY TYPES:
- XOR (exclusive): Only one outgoing/incoming path is taken
- AND (parallel): All outgoing/incoming paths are taken concurrently
- OR (inclusive): One or more paths may be taken (not implemented in basic version)
VALIDATION: Includes validate_and_joins() to ensure AND joins have matching AND splits,
preventing unsound Petri nets where tokens accumulate at unmatched joins [1].
"""
from typing import Dict, Set, Tuple, List, Optional
from collections import defaultdict
from enum import Enum
# =============================================================================
# GATEWAY TYPE ENUMERATION
# =============================================================================
class GatewayType(Enum):
    """Gateway types for BPMN/Petri net modeling."""
    XOR = 'XOR'      # Exclusive gateway (choice/merge)
    AND = 'AND'      # Parallel gateway (split/join)
    OR = 'OR'        # Inclusive gateway (one or more paths)

    def __str__(self):
        return self.value
# =============================================================================
# SPLIT GATEWAY DISCOVERY
# =============================================================================
def discover_split_gateway(activity: str,
                            successors: Set[str],
                            dfg: Dict[Tuple[str, str], int],
                            concurrent_pairs: Set[Tuple[str, str]],
                            activity_freq: Dict[str, int]) -> Optional[GatewayType]:
    """
    Discover split gateway type after an activity.

    A split gateway routes control flow from one activity to multiple successors.

    Decision logic:
    - If len(successors) <= 1: No gateway needed (return None)
    - If ALL successor pairs are concurrent: AND split (parallel branches)
    - Otherwise: XOR split (exclusive choice)

    Args:
        activity: The activity before the split
        successors: Set of direct successor activities
        dfg: Directly-follows graph
        concurrent_pairs: Set of concurrent activity pairs
        activity_freq: Activity frequencies

    Returns:
        GatewayType: AND or XOR, or None if no gateway needed
    """
    # No gateway needed for single successor
    if len(successors) <= 1:
        return None

    successors_list = list(successors)

    # Check if ALL pairs of successors are concurrent
    all_concurrent = True
    for i in range(len(successors_list)):
        for j in range(i + 1, len(successors_list)):
            act1, act2 = successors_list[i], successors_list[j]
            pair = tuple(sorted([act1, act2]))
            if pair not in concurrent_pairs:
                all_concurrent = False
                break
        if not all_concurrent:
            break

    if all_concurrent:
        return GatewayType.AND

    return GatewayType.XOR
# =============================================================================
# JOIN GATEWAY DISCOVERY
# =============================================================================
def discover_join_gateway(activity: str,
                           predecessors: Set[str],
                           dfg: Dict[Tuple[str, str], int],
                           concurrent_pairs: Set[Tuple[str, str]],
                           activity_freq: Dict[str, int]) -> Optional[GatewayType]:
    """
    Discover join gateway type before an activity.

    Similar logic to split gateway discovery but for incoming edges [1].

    A join gateway merges control flow from multiple predecessors into one activity.

    Decision logic:
    - If len(predecessors) <= 1: No gateway needed (return None)
    - If ALL predecessor pairs are concurrent: AND join (synchronize parallel branches)
    - Otherwise: XOR join (merge exclusive choices)

    Args:
        activity: The activity after the join
        predecessors: Set of direct predecessor activities
        dfg: Directly-follows graph
        concurrent_pairs: Set of concurrent activity pairs
        activity_freq: Activity frequencies

    Returns:
        GatewayType: AND or XOR, or None if no gateway needed
    """
    # No gateway needed for single predecessor
    if len(predecessors) <= 1:
        return None

    predecessors_list = list(predecessors)

    # Check if ALL pairs of predecessors are concurrent
    all_concurrent = True
    for i in range(len(predecessors_list)):
        for j in range(i + 1, len(predecessors_list)):
            act1, act2 = predecessors_list[i], predecessors_list[j]
            pair = tuple(sorted([act1, act2]))
            if pair not in concurrent_pairs:
                all_concurrent = False
                break
        if not all_concurrent:
            break

    if all_concurrent:
        return GatewayType.AND

    return GatewayType.XOR
# =============================================================================
# AND JOIN VALIDATION
# =============================================================================
def validate_and_joins(split_gateways: Dict[str, GatewayType],
                       join_gateways: Dict[str, GatewayType],
                       dfg: Dict[Tuple[str, str], int]) -> Dict[str, GatewayType]:
    """
    Validate AND join gateways and downgrade to XOR when no matching AND split exists.

    This prevents unsound Petri nets where tokens accumulate at AND joins
    that were never preceded by a matching AND split [1].

    Validation logic:
    For each activity that has an AND join gateway:
        1. Get the set of predecessor activities (from the DFG)
        2. Check whether any AND split gateway exists such that its successor set
           contains all of those predecessors
        3. If no such AND split exists → downgrade the join to XOR

    Args:
        split_gateways: Dict mapping activity -> gateway type (after activity)
        join_gateways: Dict mapping activity -> gateway type (before activity)
        dfg: Directly-follows graph

    Returns:
        validated_join_gateways: Join gateways with invalid ANDs downgraded to XOR
    """
    # Build successors dict from DFG for quick lookup
    successors = defaultdict(set)
    for (src, tgt), _ in dfg.items():
        successors[src].add(tgt)

    # Find all activities with AND split gateways and their successor sets
    and_split_successors = {}
    for activity, gateway_type in split_gateways.items():
        if gateway_type == GatewayType.AND:
            and_split_successors[activity] = successors[activity]

    # Validate each AND join gateway
    validated_join_gateways = join_gateways.copy()

    for join_activity, gateway_type in list(join_gateways.items()):
        if gateway_type != GatewayType.AND:
            continue  # Only validate AND joins

        # Get predecessors of the join activity
        predecessors = set()
        for (src, tgt), _ in dfg.items():
            if tgt == join_activity:
                predecessors.add(src)

        # Check if any AND split has a successor set that contains ALL these predecessors
        matching_split_found = False

        for split_activity, split_successors in and_split_successors.items():
            # Check if all predecessors are covered by this AND split's successors
            if predecessors.issubset(split_successors):
                matching_split_found = True
                break

        # Downgrade to XOR if no matching AND split exists
        if not matching_split_found:
            validated_join_gateways[join_activity] = GatewayType.XOR

    return validated_join_gateways
# =============================================================================
# MAIN GATEWAY DISCOVERY FUNCTION
# =============================================================================
def discover_all_gateways(dfg: Dict[Tuple[str, str], int],
                          concurrent_pairs: Set[Tuple[str, str]],
                          activity_freq: Dict[str, int]) -> Tuple[Dict[str, GatewayType], Dict[str, GatewayType]]:
    """
    Discover all split and join gateways in the process model.

    Includes validation pass to ensure AND joins have matching AND splits,
    preventing unsound models with token accumulation [1].

    Pipeline:
    1. Build adjacency structures (successors/predecessors)
    2. Discover split gateways for all activities with multiple successors
    3. Discover join gateways for all activities with multiple predecessors
    4. Validate AND joins and downgrade unmatched ones to XOR

    Args:
        dfg: Directly-follows graph
        concurrent_pairs: Set of concurrent activity pairs
        activity_freq: Activity frequencies

    Returns:
        split_gateways: Dict mapping activity -> gateway type (after activity)
        join_gateways: Dict mapping activity -> gateway type (before activity)
    """
    # Build adjacency structures
    successors = defaultdict(set)
    predecessors = defaultdict(set)

    for (src, tgt), _ in dfg.items():
        successors[src].add(tgt)
        predecessors[tgt].add(src)

    split_gateways = {}
    join_gateways = {}

    # Discover split gateways
    for activity in successors.keys():
        gateway_type = discover_split_gateway(
            activity,
            successors[activity],
            dfg,
            concurrent_pairs,
            activity_freq
        )
        if gateway_type:
            split_gateways[activity] = gateway_type

    # Discover join gateways
    for activity in predecessors.keys():
        gateway_type = discover_join_gateway(
            activity,
            predecessors[activity],
            dfg,
            concurrent_pairs,
            activity_freq
        )
        if gateway_type:
            join_gateways[activity] = gateway_type

    # VALIDATION PASS: Downgrade AND joins without matching AND splits to XOR
    # This ensures the model is structured and sound (no deadlocks) [1]
    join_gateways = validate_and_joins(split_gateways, join_gateways, dfg)

    return split_gateways, join_gateways
# =============================================================================
# HELPER FUNCTIONS FOR EXPORT
# =============================================================================
def get_gateway_id(activity: str, gateway_type: GatewayType, is_split: bool) -> str:
    """
    Generate unique gateway ID for BPMN/PNML export.

    Args:
        activity: Activity associated with the gateway
        gateway_type: Type of gateway (AND/XOR)
        is_split: True for split gateway, False for join gateway

    Returns:
        Unique gateway identifier string
    """
    prefix = 'split' if is_split else 'join'
    return f"{prefix}_{gateway_type.value}_{activity}"
def count_gateway_types(split_gateways: Dict[str, GatewayType],
                        join_gateways: Dict[str, GatewayType]) -> Dict[str, int]:
    """
    Count gateways by type for reporting purposes.

    Args:
        split_gateways: Split gateway dictionary
        join_gateways: Join gateway dictionary

    Returns:
        Dictionary with counts for each gateway type
    """
    counts = {
        'and_splits': 0,
        'xor_splits': 0,
        'and_joins': 0,
        'xor_joins': 0,
        'total': 0
    }

    for gw_type in split_gateways.values():
        if gw_type == GatewayType.AND:
            counts['and_splits'] += 1
        elif gw_type == GatewayType.XOR:
            counts['xor_splits'] += 1
        counts['total'] += 1

    for gw_type in join_gateways.values():
        if gw_type == GatewayType.AND:
            counts['and_joins'] += 1
        elif gw_type == GatewayType.XOR:
            counts['xor_joins'] += 1
        counts['total'] += 1

    return counts
