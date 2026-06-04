"""
dfg_builder.py - Build and filter the Process Data Flow Graph (PDFG)
Based on Split Miner algorithm (Augusto et al., 2017)
"""
import pandas as pd
import pm4py
from pm4py import read_xes
from typing import Dict, Tuple, Set
from collections import defaultdict


def build_dfg(log_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int]]:
    """
    Build Directly-Follows Graph from event log.

    Args:
        log_path: Path to XES file

    Returns:
        dfg: Dictionary mapping (activity_from, activity_to) -> frequency
        activity_freq: Dictionary mapping activity -> frequency
    """
    event_log_obj = read_xes(log_path)
    event_log = pm4py.convert_to_dataframe(event_log_obj)

    dfg = defaultdict(int)
    activity_freq = defaultdict(int)

    for case in event_log['case:concept:name'].unique():
        case_events = event_log[event_log['case:concept:name'] == case]
        case_events = case_events.sort_values('time:timestamp')
        activities = case_events['concept:name'].tolist()

        for act in activities:
            activity_freq[act] += 1

        for i in range(len(activities) - 1):
            edge = (activities[i], activities[i + 1])
            dfg[edge] += 1

    return dict(dfg), dict(activity_freq)


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
            min_freq = max(threshold_value * max_freq, 2)
            if freq >= min_freq:
                filtered_dfg[edge] = freq
        elif threshold_type == 'relative':
            if freq / total_edges >= threshold_value:
                filtered_dfg[edge] = freq
        else:
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
