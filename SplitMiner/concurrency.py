"""
concurrency.py - Detect concurrent activities using Split Miner heuristics
"""
import pm4py
from pm4py import read_xes
from typing import Dict, Set, Tuple, List
from collections import defaultdict


def detect_concurrency(event_log_path: str,
                       dfg: Dict[Tuple[str, str], int],
                       min_support: float = 0.01) -> Set[Tuple[str, str]]:
    """
    Detect concurrent activities using the Split Miner approach.

    Two activities A and B are concurrent if both orderings (A before B
    and B before A) appear in the log with sufficient support.
    """
    event_log_obj = read_xes(event_log_path)
    event_log = pm4py.convert_to_dataframe(event_log_obj)

    successors = defaultdict(set)
    predecessors = defaultdict(set)

    for (src, tgt) in dfg.keys():
        successors[src].add(tgt)
        predecessors[tgt].add(src)

    parallel_candidates = []
    activities = list(successors.keys())

    for i, act1 in enumerate(activities):
        for act2 in activities[i + 1:]:
            common_pred = successors[act1].intersection(successors[act2])
            common_succ = set(predecessors[act1]).intersection(predecessors[act2])
            if common_pred or common_succ:
                parallel_candidates.append((act1, act2))

    concurrent_pairs = set()
    total_cases = len(event_log['case:concept:name'].unique())

    for act1, act2 in parallel_candidates:
        order_12 = 0
        order_21 = 0

        for case_id in event_log['case:concept:name'].unique():
            case_events = event_log[event_log['case:concept:name'] == case_id]
            case_events = case_events.sort_values('time:timestamp')
            activities = case_events['concept:name'].tolist()

            if act1 in activities and act2 in activities:
                idx1 = activities.index(act1)
                idx2 = activities.index(act2)

                if idx1 < idx2:
                    order_12 += 1
                else:
                    order_21 += 1

        if (order_12 / total_cases >= min_support and
                order_21 / total_cases >= min_support):
            concurrent_pairs.add(tuple(sorted([act1, act2])))

    return concurrent_pairs


def is_parallel(act1: str, act2: str,
                concurrent_pairs: Set[Tuple[str, str]]) -> bool:
    return tuple(sorted([act1, act2])) in concurrent_pairs


def get_parallel_groups(concurrent_pairs: Set[Tuple[str, str]]) -> List[Set[str]]:
    if not concurrent_pairs:
        return []

    graph = defaultdict(set)
    for act1, act2 in concurrent_pairs:
        graph[act1].add(act2)
        graph[act2].add(act1)

    visited = set()
    groups = []

    def dfs(node, group):
        visited.add(node)
        group.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, group)

    for node in graph:
        if node not in visited:
            group = set()
            dfs(node, group)
            groups.append(group)

    return groups
