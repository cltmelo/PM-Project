"""
concurrency.py - Detect concurrent activities using Split Miner heuristics
OPTIMIZED: Uses vectorized pandas operations instead of per-case loops
"""
import pandas as pd
import numpy as np
import pm4py
from pm4py import read_xes
from typing import Dict, Set, Tuple, List, Optional
from collections import defaultdict


def detect_concurrency(event_log_path: str = None,
                       dfg: Dict[Tuple[str, str], int] = None,
                       event_log_df: Optional[pd.DataFrame] = None,
                       min_support: float = 0.01) -> Set[Tuple[str, str]]:
    """
    Detect concurrent activities using VECTORIZED operations.

    Two activities A and B are concurrent if:
    1. They both follow some common predecessor OR precede some common successor
    2. They appear interleaved in traces (A...B and B...A both occur)

    Args:
        event_log_path: Path to XES event log (optional if event_log_df provided)
        dfg: Directly-follows graph
        event_log_df: Pre-loaded DataFrame (avoids reloading)
        min_support: Minimum support threshold for concurrency detection

    Returns:
        concurrent_pairs: Set of (activity_a, activity_b) tuples indicating concurrency
    """
    # Load or use provided DataFrame
    if event_log_df is None:
        if event_log_path is None:
            raise ValueError("Either event_log_path or event_log_df must be provided")
        event_log_obj = read_xes(event_log_path)
        event_log_df = pm4py.convert_to_dataframe(event_log_obj)

    if dfg is None:
        raise ValueError("DFG must be provided")

    total_cases = event_log_df['case:concept:name'].nunique()

    # Get adjacency information from DFG
    successors = defaultdict(set)
    predecessors = defaultdict(set)

    for (src, tgt), freq in dfg.items():
        successors[src].add(tgt)
        predecessors[tgt].add(src)

    # Get all unique activities
    all_activities = set(successors.keys())
    activities_list = list(all_activities)

    # ========== VECTORIZED APPROACH ==========
    # Step 1: For each case, get position index of each activity

    # Sort events by case and timestamp
    event_log_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp'],
        kind='mergesort'
    )

    # Add row index within each case (position in trace)
    event_log_df = event_log_df.copy()
    event_log_df['position'] = event_log_df.groupby('case:concept:name').cumcount()

    # Step 2: Create pivot table - cases x activities with position values
    # This gives us the FIRST occurrence position of each activity per case
    activity_positions = event_log_df.groupby(
        ['case:concept:name', 'concept:name']
    )['position'].first().unstack(fill_value=-1)

    # Step 3: Find candidate pairs (activities with common predecessor or successor)
    parallel_candidates = []

    for i, act1 in enumerate(activities_list):
        for act2 in activities_list[i+1:]:
            common_pred = successors[act1].intersection(successors[act2])
            common_succ = set(predecessors[act1]).intersection(predecessors[act2])

            if common_pred or common_succ:
                parallel_candidates.append((act1, act2))

    # Step 4: VECTORIZED concurrency check for all candidates at once
    concurrent_pairs = set()

    if not parallel_candidates or activity_positions.empty:
        return concurrent_pairs

    for act1, act2 in parallel_candidates:
        # Check if both activities exist in the pivot table
        if act1 not in activity_positions.columns or act2 not in activity_positions.columns:
            continue

        # Get positions where both activities appear in the same case
        act1_pos = activity_positions[act1]
        act2_pos = activity_positions[act2]

        # Cases where both activities appear
        both_present = (act1_pos >= 0) & (act2_pos >= 0)

        if both_present.sum() == 0:
            continue

        # Count orderings (vectorized comparison)
        order_12 = (act1_pos[both_present] < act2_pos[both_present]).sum()
        order_21 = (act1_pos[both_present] > act2_pos[both_present]).sum()

        # Calculate support
        support_12 = order_12 / total_cases
        support_21 = order_21 / total_cases

        # Both orderings must appear with sufficient support
        if support_12 >= min_support and support_21 >= min_support:
            # Normalize pair (smaller first for consistency)
            pair = tuple(sorted([act1, act2]))
            concurrent_pairs.add(pair)

    return concurrent_pairs


def detect_concurrency_fast(event_log_df: pd.DataFrame,
                            dfg: Dict[Tuple[str, str], int],
                            min_support: float = 0.01) -> Set[Tuple[str, str]]:
    """
    FASTEST: Fully vectorized concurrency detection using numpy.

    Recommended for large logs (>100k events).
    """
    total_cases = event_log_df['case:concept:name'].nunique()

    # Sort and add position indices
    event_log_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp']
    ).copy()

    event_log_df['position'] = event_log_df.groupby('case:concept:name').cumcount()

    # Get activities from DFG
    activities = set()
    for (src, tgt) in dfg.keys():
        activities.add(src)
        activities.add(tgt)

    # Create case-activity matrix with first occurrence positions
    pivot = event_log_df.groupby(
        ['case:concept:name', 'concept:name']
    )['position'].first().unstack(fill_value=-1)

    # Filter to only activities in our DFG
    available_cols = [col for col in activities if col in pivot.columns]
    pivot = pivot[available_cols]

    # Build adjacency from DFG
    neighbors = defaultdict(set)
    for (src, tgt) in dfg.keys():
        neighbors[src].add(tgt)
        neighbors[tgt].add(src)

    concurrent_pairs = set()

    # Vectorized pairwise comparison
    for i, act1 in enumerate(available_cols):
        for act2 in available_cols[i+1:]:
            # Quick filter: must share a neighbor in DFG
            if not (neighbors[act1] & neighbors[act2]):
                continue

            pos1 = pivot[act1].values
            pos2 = pivot[act2].values

            # Both present mask
            mask = (pos1 >= 0) & (pos2 >= 0)

            if mask.sum() < 2:
                continue

            # Count both orderings
            order_12 = np.sum((pos1[mask] < pos2[mask]))
            order_21 = np.sum((pos1[mask] > pos2[mask]))

            support_12 = order_12 / total_cases
            support_21 = order_21 / total_cases

            if support_12 >= min_support and support_21 >= min_support:
                pair = tuple(sorted([act1, act2]))
                concurrent_pairs.add(pair)

    return concurrent_pairs


def is_parallel(act1: str, act2: str,
                concurrent_pairs: Set[Tuple[str, str]]) -> bool:
    """
    Check if two activities are in a concurrent relationship.
    """
    pair = tuple(sorted([act1, act2]))
    return pair in concurrent_pairs


def get_parallel_groups(concurrent_pairs: Set[Tuple[str, str]]) -> List[Set[str]]:
    """
    Group concurrent activities into connected components.
    """
    if not concurrent_pairs:
        return []

    # Build graph of concurrent relationships
    graph = defaultdict(set)
    for act1, act2 in concurrent_pairs:
        graph[act1].add(act2)
        graph[act2].add(act1)

    # Find connected components
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
