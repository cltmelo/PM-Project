"""
concurrency.py - Detect concurrent activities using Split Miner heuristics
OPTIMIZED: Uses vectorized pandas operations instead of per-case loops [1]
"""
import pandas as pd
import numpy as np
import pm4py
from pm4py import read_xes
from typing import Dict, Set, Tuple, List, Optional
from collections import defaultdict
# =============================================================================
# MAIN CONCURRENCY DETECTION (VECTORIZED)
# =============================================================================
def detect_concurrency_fast(event_log_df: pd.DataFrame,
                             dfg: Dict[Tuple[str, str], int],
                             min_support: float = 0.01) -> Set[Tuple[str, str]]:
    """
    Detect concurrent activity pairs using VECTORIZED pandas operations.

    This replaces the slow O(pairs × cases) loop-based approach with a
    single-pass vectorized implementation using groupby + shift [1].

    Two activities A and B are concurrent if:
    1. Both (A→B) and (B→A) edges exist in the DFG
    2. Both directions appear in at least min_support proportion of cases

    Args:
        event_log_df: Pre-loaded event log DataFrame (not file path)
        dfg: Filtered directly-follows graph {(src, tgt): frequency}
        min_support: Minimum proportion of cases required (default: 0.01 = 1%)

    Returns:
        concurrent_pairs: Set of canonical pairs {(min(A,B), max(A,B)), ...}
    """
    # Extract all activities that appear as both sources and targets
    sources = {edge[0] for edge in dfg.keys()}
    targets = {edge[1] for edge in dfg.keys()}
    candidate_activities = sources & targets

    # Build set of edges that exist in DFG
    dfg_edges = set(dfg.keys())

    # Find candidate pairs where BOTH (A→B) and (B→A) exist in DFG
    candidate_pairs = []
    for edge in dfg_edges:
        reverse_edge = (edge[1], edge[0])
        if reverse_edge in dfg_edges:
            # Only consider pairs where both directions exist
            if edge[0] != edge[1]:  # Exclude self-loops
                canonical = tuple(sorted([edge[0], edge[1]]))
                candidate_pairs.append(canonical)

    # Remove duplicates
    candidate_pairs = list(set(candidate_pairs))

    if not candidate_pairs:
        return set()

    # Sort by case ID and timestamp (stable sort)
    sorted_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp'],
        kind='mergesort'
    ).copy()

    # Vectorized next_activity creation using groupby + shift
    sorted_df['_next'] = sorted_df.groupby(
        'case:concept:name'
    )['concept:name'].shift(-1)

    # Filter to valid transitions only
    valid_transitions = sorted_df[sorted_df['_next'].notna()].copy()

    # Count DISTINCT CASES for each (src, tgt) pair in ONE pass
    edge_case_counts = valid_transitions.groupby(
        ['concept:name', '_next']
    )['case:concept:name'].nunique()

    # Convert to dict for fast lookup
    edge_case_dict = {
        (row[0], row[1]): int(count)
        for (row, count) in edge_case_counts.items()
    }

    # Total number of cases
    num_cases = event_log_df['case:concept:name'].nunique()
    min_cases_threshold = min_support * num_cases

    # Check each candidate pair
    concurrent_pairs = set()

    for pair in candidate_pairs:
        A, B = pair

        # Count cases containing A→B
        cases_A_to_B = edge_case_dict.get((A, B), 0)

        # Count cases containing B→A
        cases_B_to_A = edge_case_dict.get((B, A), 0)

        # Both directions must meet minimum support threshold
        if (cases_A_to_B >= min_cases_threshold and
            cases_B_to_A >= min_cases_threshold):
            concurrent_pairs.add(pair)

    return concurrent_pairs
# =============================================================================
# DEPRECATED WRAPPER (for backward compatibility)
# =============================================================================
def detect_concurrency(event_log_path: str,
                       dfg: Dict[Tuple[str, str], int],
                       min_support: float = 0.01) -> Set[Tuple[str, str]]:
    """
    DEPRECATED: Use detect_concurrency_fast() instead.

    Old loop-based implementation - slow O(pairs × cases) complexity [1].
    This wrapper loads the DataFrame and calls the optimized version.

    Args:
        event_log_path: Path to XES event log
        dfg: Directly-follows graph
        min_support: Minimum support threshold for concurrency detection

    Returns:
        concurrent_pairs: Set of (activity_a, activity_b) tuples indicating concurrency
    """
    # Load event log and convert to DataFrame
    event_log_obj = read_xes(event_log_path)
    event_log_df = pm4py.convert_to_dataframe(event_log_obj)

    # Call optimized vectorized version
    return detect_concurrency_fast(
        event_log_df=event_log_df,
        dfg=dfg,
        min_support=min_support
    )
# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def is_parallel(act1: str,
                act2: str,
                concurrent_pairs: Set[Tuple[str, str]]) -> bool:
    """
    Check if two activities are concurrent (parallel).

    Args:
        act1: First activity name
        act2: Second activity name
        concurrent_pairs: Set of canonical concurrent pairs

    Returns:
        True if (act1, act2) is a concurrent pair, False otherwise
    """
    # Create canonical pair (smaller first for consistency)
    pair = tuple(sorted([act1, act2]))
    return pair in concurrent_pairs


def get_parallel_groups(concurrent_pairs: Set[Tuple[str, str]]) -> List[Set[str]]:
    """
    Group concurrent activities into connected components via DFS.

    Activities in the same group are all mutually concurrent (directly or transitively).

    Args:
        concurrent_pairs: Set of canonical concurrent pairs

    Returns:
        List of sets, where each set contains activities in one parallel group
    """
    if not concurrent_pairs:
        return []

    # Build adjacency list from concurrent pairs
    adjacency = defaultdict(set)
    all_activities = set()

    for (act1, act2) in concurrent_pairs:
        adjacency[act1].add(act2)
        adjacency[act2].add(act1)
        all_activities.add(act1)
        all_activities.add(act2)

    # Find connected components using DFS
    visited = set()
    groups = []

    def dfs(activity: str, component: Set[str]):
        """Depth-first search to find all activities in same component."""
        visited.add(activity)
        component.add(activity)

        for neighbor in adjacency[activity]:
            if neighbor not in visited:
                dfs(neighbor, component)

    # Process each unvisited activity
    for activity in all_activities:
        if activity not in visited:
            component = set()
            dfs(activity, component)
            groups.append(component)

    return groups
