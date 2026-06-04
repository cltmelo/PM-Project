"""
dfg_builder.py - Build and filter the Process Data Flow Graph (PDFG)
Based on Split Miner algorithm (Augusto et al., 2017)
OPTIMIZED: Uses vectorized pandas operations instead of Python loops
"""
import pandas as pd
import numpy as np
import pm4py
from pm4py import read_xes
from typing import Dict, Tuple, Set
from collections import defaultdict


def build_dfg(log_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], pd.DataFrame]:
    """
    Build Directly-Follows Graph from event log using VECTORIZED operations.

    Args:
        log_path: Path to XES file

    Returns:
        dfg: Dictionary mapping (activity_from, activity_to) -> frequency
        activity_freq: Dictionary mapping activity -> frequency
        event_log_df: Pre-loaded DataFrame for reuse
    """
    # Load event log and convert to DataFrame
    event_log_obj = read_xes(log_path)
    event_log_df = pm4py.convert_to_dataframe(event_log_obj)

    # Sort by case and timestamp (vectorized)
    event_log_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp'],
        kind='mergesort'  # Stable sort
    )

    # Create shifted columns to get next activity within each case (vectorized)
    event_log_df['next_activity'] = event_log_df.groupby('case:concept:name')['concept:name'].shift(-1)
    event_log_df['next_case'] = event_log_df.groupby('case:concept:name')['case:concept:name'].shift(-1)

    # Filter out rows where next activity is in different case or doesn't exist
    valid_transitions = event_log_df[
        (event_log_df['next_case'] == event_log_df['case:concept:name']) &
        (event_log_df['next_activity'].notna())
    ]

    # Build DFG using vectorized groupby (MUCH faster than Python loops)
    dfg_series = valid_transitions.groupby(
        ['concept:name', 'next_activity']
    ).size()

    # Convert to dictionary
    dfg = {
        (row.Index[0], row.Index[1]): row.values[0]
        for _, row in dfg_series.reset_index().iterrows()
    }

    # Alternative simpler conversion:
    dfg = {}
    for (src, tgt), freq in dfg_series.items():
        dfg[(src, tgt)] = int(freq)

    # Count activity frequencies (vectorized)
    activity_freq = event_log_df['concept:name'].value_counts().to_dict()

    # Clean up temporary columns
    event_log_df = event_log_df.drop(columns=['next_activity', 'next_case'], errors='ignore')

    return dfg, activity_freq, event_log_df


def build_dfg_fast(log_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], pd.DataFrame]:
    """
    FASTEST: Use pm4py's optimized DFG discovery (Cython-backed).

    This is 10-50x faster than pure Python implementation.
    """
    # Load event log
    event_log_obj = read_xes(log_path)
    event_log_df = pm4py.convert_to_dataframe(event_log_obj)

    # Use pm4py's optimized DFG discovery
    dfg, start_activities, end_activities = pm4py.discover_directly_follows_graph(event_log_df)

    # Convert dfg to standard format
    dfg_dict = {}
    for edge, freq in dfg.items():
        if isinstance(edge, tuple) and len(edge) == 2:
            dfg_dict[edge] = int(freq)

    # Count activity frequencies
    activity_freq = event_log_df['concept:name'].value_counts().to_dict()

    return dfg_dict, activity_freq, event_log_df


def filter_dfg(dfg: Dict[Tuple[str, str], int],
               activity_freq: Dict[str, int],
               threshold_type: str = 'frequency',
               threshold_value: float = 0.02) -> Dict[Tuple[str, str], int]:
    """
    Filter DFG to remove noise and infrequent edges.

    Args:
        dfg: Raw directly-follows graph
        activity_freq: Activity frequencies
        threshold_type: 'frequency' (absolute) or 'relative' (proportion)
        threshold_value: Threshold value for filtering

    Returns:
        filtered_dfg: Filtered directly-follows graph
    """
    if not dfg:
        return {}

    max_freq = max(dfg.values())
    total_edges = sum(dfg.values())

    filtered_dfg = {}

    for edge, freq in dfg.items():
        if threshold_type == 'frequency':
            # Absolute frequency threshold
            min_freq = max(threshold_value * max_freq, 2)
            if freq >= min_freq:
                filtered_dfg[edge] = freq
        elif threshold_type == 'relative':
            # Relative proportion threshold
            if freq / total_edges >= threshold_value:
                filtered_dfg[edge] = freq
        else:
            # Keep all edges
            filtered_dfg[edge] = freq

    return filtered_dfg


def get_start_activities(dfg: Dict[Tuple[str, str], int],
                         activity_freq: Dict[str, int]) -> Set[str]:
    """
    Identify start activities (never appear as target).
    """
    targets = {tgt for (_, tgt) in dfg.keys()}
    starts = {act for act in activity_freq.keys() if act not in targets}
    return starts


def get_end_activities(dfg: Dict[Tuple[str, str], int],
                       activity_freq: Dict[str, int]) -> Set[str]:
    """
    Identify end activities (never appear as source).
    """
    sources = {src for (src, _) in dfg.keys()}
    ends = {act for act in activity_freq.keys() if act not in sources}
    return ends
