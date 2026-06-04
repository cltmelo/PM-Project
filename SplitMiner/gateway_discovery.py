"""
gateway_discovery.py - Identify XOR/AND split and join gateways
Core of Split Miner algorithm
"""

from typing import Dict, Set, Tuple, List
from collections import defaultdict


class GatewayType:
    AND = 'AND'
    XOR = 'XOR'
    OR = 'OR'  # Less common, kept for extensibility


def discover_split_gateway(activity: str,
                           successors: Set[str],
                           dfg: Dict[Tuple[str, str], int],
                           concurrent_pairs: Set[Tuple[str, str]],
                           activity_freq: Dict[str, int]) -> str:
    """
    Determine the type of split gateway after an activity.

    Split Miner heuristic:
    - If all successors are pairwise concurrent → AND-split
    - If successors are mutually exclusive → XOR-split
    - Mixed cases require more complex analysis (simplified here)

    Args:
        activity: The activity before the split
        successors: Set of direct successor activities
        dfg: Directly-follows graph
        concurrent_pairs: Set of concurrent activity pairs
        activity_freq: Activity frequencies

    Returns:
        GatewayType: AND or XOR
    """
    if len(successors) <= 1:
        return None  # No gateway needed

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

    # Check for XOR: successors should rarely/mutually exclusively occur
    # Simplified: if not all concurrent, default to XOR
    # In full Split Miner, more sophisticated heuristics apply
    return GatewayType.XOR


def discover_join_gateway(activity: str,
                          predecessors: Set[str],
                          dfg: Dict[Tuple[str, str], int],
                          concurrent_pairs: Set[Tuple[str, str]],
                          activity_freq: Dict[str, int]) -> str:
    """
    Determine the type of join gateway before an activity.

    Similar logic to split gateway discovery but for incoming edges.

    Args:
        activity: The activity after the join
        predecessors: Set of direct predecessor activities
        dfg: Directly-follows graph
        concurrent_pairs: Set of concurrent activity pairs
        activity_freq: Activity frequencies

    Returns:
        GatewayType: AND or XOR
    """
    if len(predecessors) <= 1:
        return None  # No gateway needed

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


def discover_all_gateways(dfg: Dict[Tuple[str, str], int],
                          concurrent_pairs: Set[Tuple[str, str]],
                          activity_freq: Dict[str, int]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Discover all split and join gateways in the process model.

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

    return split_gateways, join_gateways


def get_gateway_id(activity: str, gateway_type: str, is_split: bool) -> str:
    """
    Generate unique gateway ID for BPMN export.
    """
    prefix = 'split' if is_split else 'join'
    return f"{prefix}_{gateway_type}_{activity}"
