"""
dfg_builder.py - Build and filter the Process Data Flow Graph (PDFG)
Based on Split Miner algorithm (Augusto et al., 2017)
OPTIMIZED: Uses vectorized pandas operations instead of Python loops [1]
"""
import pandas as pd
import numpy as np
import pm4py
from pm4py import read_xes
from typing import Dict, Tuple, Set, List, Optional, Union
from collections import defaultdict, Counter
from datetime import timedelta
# =============================================================================
# SOURCE/SINK MARKER FUNCTIONS
# =============================================================================
def add_source_sink_to_filtered_dfg(dfg: Dict[Tuple[str, str], int],
                                     activity_freq: Dict[str, int],
                                     event_log_df: pd.DataFrame,
                                     start_marker: str = '>>',
                                     end_marker: str = '<<') -> Tuple[Dict[Tuple[str, str], int], Dict[str, int]]:
    """
    Add synthetic source (>>) and sink (<<) edges to the filtered DFG.

    MUST be called AFTER filter_dfg — source/sink edges must not be
    subject to removal by the frequency filter.

    Args:
        dfg: Filtered directly-follows graph
        activity_freq: Activity frequencies
        event_log_df: Event log DataFrame for extracting case boundaries
        start_marker: Symbol for artificial start activity (default: '>>')
        end_marker: Symbol for artificial end activity (default: '<<')

    Returns:
        updated_dfg: DFG with source/sink edges added
        updated_activity_freq: Activity frequencies including markers
    """
    # Sort by case ID and timestamp
    sorted_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp'],
        kind='mergesort'
    )

    # Get first activity of each case
    first_acts = sorted_df.groupby('case:concept:name')['concept:name'].first()

    # Get last activity of each case
    last_acts = sorted_df.groupby('case:concept:name')['concept:name'].last()

    # Count how many cases start with each activity
    start_counts = Counter(first_acts.values)

    # Count how many cases end with each activity
    end_counts = Counter(last_acts.values)

    # Total number of cases
    num_cases = len(first_acts)

    # Add source edges: (>>, first_activity) with case counts
    for activity, count in start_counts.items():
        dfg[(start_marker, activity)] = count

    # Add sink edges: (last_activity, <<) with case counts
    for activity, count in end_counts.items():
        dfg[(activity, end_marker)] = count

    # Add markers to activity frequencies
    activity_freq[start_marker] = num_cases
    activity_freq[end_marker] = num_cases

    return dfg, activity_freq
def add_source_sink_to_log(event_log_df: pd.DataFrame,
                            start_marker: str = '>>',
                            end_marker: str = '<<') -> pd.DataFrame:
    """
    Insert synthetic start/end events into every trace for replay purposes.

    Args:
        event_log_df: Event log DataFrame
        start_marker: Symbol for artificial start activity (default: '>>')
        end_marker: Symbol for artificial end activity (default: '<<')

    Returns:
        updated_df: DataFrame with synthetic events inserted
    """
    # Sort by case ID and timestamp
    sorted_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp'],
        kind='mergesort'
    ).copy()

    # Vectorized: Get min/max timestamp per case using groupby agg
    case_times = sorted_df.groupby('case:concept:name')['time:timestamp'].agg(['min', 'max'])

    start_events = []
    end_events = []

    # Process each case (vectorized timestamp calculation)
    for case_id, row in case_times.iterrows():
        case_min_ts = row['min']
        case_max_ts = row['max']

        # Get template row from original data for this case
        case_template = sorted_df[sorted_df['case:concept:name'] == case_id].iloc[[0]].copy()

        # Create start event row (24h before first event)
        start_row = case_template.copy()
        start_row['concept:name'] = start_marker
        start_row['time:timestamp'] = case_min_ts - timedelta(hours=24)
        start_events.append(start_row)

        # Create end event row (24h after last event)
        end_row = case_template.copy()
        end_row['concept:name'] = end_marker
        end_row['time:timestamp'] = case_max_ts + timedelta(hours=24)
        end_events.append(end_row)

    # Concatenate all parts
    if start_events:
        start_df = pd.concat(start_events, ignore_index=True)
        end_df = pd.concat(end_events, ignore_index=True)

        # Combine with original data
        updated_df = pd.concat([sorted_df, start_df, end_df], ignore_index=True)

        # Final stable sort by case ID and timestamp
        updated_df = updated_df.sort_values(
            ['case:concept:name', 'time:timestamp'],
            kind='mergesort'
        ).reset_index(drop=True)
    else:
        updated_df = sorted_df

    return updated_df
# =============================================================================
# VARIANT FILTERING
# =============================================================================
def filter_rare_variants(event_log_df: pd.DataFrame,
                          min_variant_freq: int = 3,
                          verbose: bool = True) -> pd.DataFrame:
    """
    Remove cases whose activity sequence (variant) appears fewer than
    min_variant_freq times across all cases.

    This is a pre-processing step to remove noise traces before DFG filtering.

    Args:
        event_log_df: Event log DataFrame
        min_variant_freq: Minimum number of times a variant must appear (default: 3)
        verbose: Whether to print summary statistics

    Returns:
        filtered_df: DataFrame with rare variants removed
    """
    # Sort by case ID and timestamp (stable sort)
    sorted_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp'],
        kind='mergesort'
    ).copy()

    # Build variant tuple per case: ordered sequence of activities
    case_variants = sorted_df.groupby(
        'case:concept:name'
    )['concept:name'].apply(tuple)

    # Count how many times each variant appears
    variant_counts = case_variants.value_counts()

    # Find variants that meet the minimum frequency threshold
    common_variants = variant_counts[variant_counts >= min_variant_freq].index

    # Get case IDs that have common variants
    kept_cases = case_variants[case_variants.isin(common_variants)].index

    # Filter the DataFrame to keep only those cases
    filtered_df = sorted_df[
        sorted_df['case:concept:name'].isin(kept_cases)
    ].copy()

    # Calculate statistics for summary
    original_cases = len(case_variants)
    kept_case_count = len(kept_cases)
    removed_cases = original_cases - kept_case_count

    original_variants = len(variant_counts)
    kept_variant_count = len(common_variants)
    removed_variants = original_variants - kept_variant_count

    if verbose:
        print(f"\n{'='*70}")
        print("RARE VARIANT FILTERING")
        print(f"{'='*70}")
        print(f"Original: {original_cases} cases, {original_variants} unique variants")
        print(f"Kept:     {kept_case_count} cases ({kept_case_count/original_cases*100:.1f}%), "
              f"{kept_variant_count} variants")
        print(f"Removed:  {removed_cases} cases ({removed_cases/original_cases*100:.1f}%), "
              f"{removed_variants} rare variants")
        print(f"Threshold: ≥{min_variant_freq} occurrences per variant")
        print(f"{'='*70}")

    return filtered_df
# =============================================================================
# DFG BUILDING FUNCTIONS
# =============================================================================
def build_dfg(log_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], pd.DataFrame]:
    """
    Build Directly-Follows Graph from event log using VECTORIZED operations.

    Pure-pandas version for reference (slower than build_dfg_fast).

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

    # Sort by case and timestamp (vectorized, stable sort)
    event_log_df = event_log_df.sort_values(
        ['case:concept:name', 'time:timestamp'],
        kind='mergesort'
    )

    # Create next_activity column using vectorized groupby + shift(-1)
    event_log_df['next_activity'] = event_log_df.groupby(
        'case:concept:name'
    )['concept:name'].shift(-1)

    # Filter rows where next activity belongs to same case and is not null
    valid_transitions = event_log_df[event_log_df['next_activity'].notna()].copy()

    # Count (concept:name, next_activity) pairs with groupby().size()
    dfg_series = valid_transitions.groupby(
        ['concept:name', 'next_activity']
    ).size()

    # Build DFG dict
    dfg_dict = {
        (row[0], row[1]): int(count)
        for (row, count) in dfg_series.items()
    }

    # Build activity frequency dict
    activity_freq_dict = dict(
        event_log_df['concept:name'].value_counts()
    )

    # Clean up temporary column
    event_log_df = event_log_df.drop(columns=['next_activity'], errors='ignore')

    return dfg_dict, activity_freq_dict, event_log_df
def build_dfg_fast(log_path: str) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int], pd.DataFrame]:
    """
    FASTEST: Use pm4py's optimized DFG discovery (Cython-backed).

    This is 10-50x faster than pure Python implementation.

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

    # Use pm4py's Cython-backed DFG discovery (10-50x faster)
    dfg, start_activities, end_activities = pm4py.discover_directly_follows_graph(
        event_log_df
    )

    # Convert to plain dict of {(src, tgt): int}
    dfg_dict = {key: int(value) for key, value in dfg.items()}

    # Build activity frequency dict
    activity_freq_dict = dict(
        event_log_df['concept:name'].value_counts()
    )

    return dfg_dict, activity_freq_dict, event_log_df
# =============================================================================
# DFG FILTERING
# =============================================================================
def filter_dfg(dfg: Dict[Tuple[str, str], int],
               activity_freq: Dict[str, int],
               threshold_type: str = 'frequency',
               threshold_value: float = 0.02,
               event_log_df: Optional[pd.DataFrame] = None) -> Dict[Tuple[str, str], int]:
    """
    Filter DFG to remove noise and infrequent edges.

    When event_log_df is provided and threshold_type='frequency',
    filters by number of UNIQUE CASES containing each edge (not raw occurrences).
    This prevents self-loops from inflating max_freq and breaking the filter.

    Args:
        dfg: Raw directly-follows graph
        activity_freq: Activity frequencies
        threshold_type: 'frequency' (absolute/case-based) or 'relative' (proportion)
        threshold_value: Threshold value for filtering
        event_log_df: Optional DataFrame for case-based filtering

    Returns:
        filtered_dfg: Filtered directly-follows graph
    """
    if not dfg:
        return {}

    filtered_dfg = {}

    # CASE-BASED FILTERING (preferred when event_log_df is provided)
    if threshold_type == 'frequency' and event_log_df is not None:
        # Sort by case ID and timestamp
        sorted_df = event_log_df.sort_values(
            ['case:concept:name', 'time:timestamp'],
            kind='mergesort'
        )

        # Get next activity within each case using vectorized shift
        sorted_df = sorted_df.copy()
        sorted_df['_next'] = sorted_df.groupby(
            'case:concept:name'
        )['concept:name'].shift(-1)

        # Filter out rows where next activity is null
        valid_transitions = sorted_df[sorted_df['_next'].notna()].copy()

        # Count DISTINCT CASES for each (src, tgt) pair
        edge_case_counts = valid_transitions.groupby(
            ['concept:name', '_next']
        )['case:concept:name'].nunique()

        # Build dict of {(src, tgt): num_cases}
        edge_case_dict = {
            (row[0], row[1]): int(count)
            for (row, count) in edge_case_counts.items()
        }

        # Compute threshold based on total number of cases
        num_cases = event_log_df['case:concept:name'].nunique()
        min_cases = max(threshold_value * num_cases, 2)

        # Keep edges that appear in enough unique cases
        for edge, freq in dfg.items():
            case_count = edge_case_dict.get(edge, 0)
            if case_count >= min_cases:
                filtered_dfg[edge] = freq

        # Clean up temporary column
        if '_next' in event_log_df.columns:
            event_log_df = event_log_df.drop(columns=['_next'], errors='ignore')

        return filtered_dfg

    # FALLBACK: Old occurrence-based logic (when event_log_df is None)
    elif threshold_type == 'frequency':
        # This is the broken logic - kept for backward compatibility only
        max_freq = max(dfg.values())
        min_freq = max(threshold_value * max_freq, 2)

        for edge, freq in dfg.items():
            if freq >= min_freq:
                filtered_dfg[edge] = freq

    # RELATIVE THRESHOLD (proportion of total edges)
    elif threshold_type == 'relative':
        total_edges = sum(dfg.values())

        for edge, freq in dfg.items():
            if freq / total_edges >= threshold_value:
                filtered_dfg[edge] = freq

    else:
        # Keep all edges
        filtered_dfg = dfg.copy()

    return filtered_dfg
# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_start_activities(dfg: Dict[Tuple[str, str], int],
                         activity_freq: Dict[str, int]) -> Set[str]:
    """
    Get activities that never appear as target (only as source).

    Args:
        dfg: Directly-follows graph
        activity_freq: Activity frequencies

    Returns:
        start_activities: Set of activities that only appear as sources
    """
    all_sources = {edge[0] for edge in dfg.keys()}
    all_targets = {edge[1] for edge in dfg.keys()}

    # Start activities appear as source but never as target
    start_activities = all_sources - all_targets

    return start_activities
def get_end_activities(dfg: Dict[Tuple[str, str], int],
                       activity_freq: Dict[str, int]) -> Set[str]:
    """
    Get activities that never appear as source (only as target).

    Args:
        dfg: Directly-follows graph
        activity_freq: Activity frequencies

    Returns:
        end_activities: Set of activities that only appear as targets
    """
    all_sources = {edge[0] for edge in dfg.keys()}
    all_targets = {edge[1] for edge in dfg.keys()}

    # End activities appear as target but never as source
    end_activities = all_targets - all_sources

    return end_activities
