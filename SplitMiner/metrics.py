"""
metrics.py - Evaluate fitness, precision, and simplicity of discovered process model
Mirrors logic from GeneticMiner/metrics.py for consistent comparison
"""
import json
import pm4py
from pm4py import read_xes
from typing import Dict, Set, Tuple, List, Union
from collections import defaultdict
import pandas as pd


def _ensure_dataframe(event_log_or_path: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Helper function to ensure we have a DataFrame.

    Args:
        event_log_or_path: Either a file path (str) or already-loaded DataFrame

    Returns:
        DataFrame representation of the event log
    """
    if isinstance(event_log_or_path, str):
        event_log_obj = read_xes(event_log_or_path)
        return pm4py.convert_to_dataframe(event_log_obj)
    else:
        # Already a DataFrame
        return event_log_or_path


def calculate_replay_fitness(event_log_or_path: Union[str, pd.DataFrame],
                              dfg: Dict[Tuple[str, str], int],
                              start_activities: Set[str],
                              end_activities: Set[str]) -> float:
    """
    Calculate replay fitness: how well the model can reproduce traces in the log.

    Fitness = (correctly parsed tokens) / (total tokens)

    Args:
        event_log_or_path: Path to XES file OR pre-loaded DataFrame
        dfg: Directly-follows graph (the model)
        start_activities: Set of start activities
        end_activities: Set of end activities

    Returns:
        fitness: Score between 0 and 1
    """
    # Load or use provided DataFrame
    event_log = _ensure_dataframe(event_log_or_path)

    total_produced = 0
    total_consumed = 0
    total_missing = 0
    total_remaining = 0

    for case_id in event_log['case:concept:name'].unique():
        case_events = event_log[event_log['case:concept:name'] == case_id]
        case_events = case_events.sort_values('time:timestamp')
        activities = case_events['concept:name'].tolist()

        if not activities:
            continue

        # Simulate token flow through the model
        produced = 0
        consumed = 0
        missing = 0

        # Check first activity
        if activities[0] in start_activities:
            produced += 1
        else:
            missing += 1

        # Process each transition
        current_tokens = {activities[0]} if activities[0] in start_activities else set()

        for i in range(len(activities) - 1):
            src_act = activities[i]
            tgt_act = activities[i + 1]

            # Check if transition exists in model
            if (src_act, tgt_act) in dfg:
                consumed += 1
                produced += 1
            else:
                missing += 1

        # Check last activity
        if activities[-1] in end_activities:
            consumed += 1
        else:
            # Tokens remaining (should have been consumed at end)
            pass

        total_produced += produced
        total_consumed += consumed
        total_missing += missing

    # Avoid division by zero
    if total_produced + total_missing == 0:
        return 1.0

    fitness = 1 - (total_missing / (total_produced + total_missing))
    return max(0.0, min(1.0, fitness))


def calculate_precision(event_log_or_path: Union[str, pd.DataFrame],
                        dfg: Dict[Tuple[str, str], int]) -> float:
    """
    Calculate behavioral precision: how much extra behavior does the model allow?

    Precision = (observed edges) / (all possible edges in model)

    Higher precision = fewer extra behaviors allowed by the model.

    Args:
        event_log_or_path: Path to XES file OR pre-loaded DataFrame
        dfg: Directly-follows graph (the model)

    Returns:
        precision: Score between 0 and 1
    """
    # Load or use provided DataFrame
    event_log = _ensure_dataframe(event_log_or_path)

    # Count observed directly-follows relations
    observed_edges = set()
    total_occurrences = 0

    for case_id in event_log['case:concept:name'].unique():
        case_events = event_log[event_log['case:concept:name'] == case_id]
        case_events = case_events.sort_values('time:timestamp')
        activities = case_events['concept:name'].tolist()

        for i in range(len(activities) - 1):
            edge = (activities[i], activities[i + 1])
            observed_edges.add(edge)
            total_occurrences += 1

    if not dfg:
        return 1.0

    model_edges = set(dfg.keys())

    # Precision: how many model edges are actually observed?
    # Penalize edges in model that never appear in log
    unobserved_model_edges = model_edges - observed_edges

    if len(model_edges) == 0:
        return 1.0

    precision = 1 - (len(unobserved_model_edges) / len(model_edges))
    return max(0.0, min(1.0, precision))


def calculate_simplicity(dfg: Dict[Tuple[str, str], int],
                         num_activities: int) -> float:
    """
    Calculate structural simplicity: penalize complex models.

    Simplicity = 1 - (edges / (activities * max_possible_connections))

    Simpler models (fewer edges relative to activities) score higher.

    Args:
        dfg: Directly-follows graph
        num_activities: Number of unique activities

    Returns:
        simplicity: Score between 0 and 1
    """
    if num_activities <= 1:
        return 1.0

    num_edges = len(dfg)

    # Maximum possible edges in a directed graph: n * (n-1)
    max_edges = num_activities * (num_activities - 1)

    if max_edges == 0:
        return 1.0

    # Normalized complexity (0 = simple, 1 = complex)
    complexity = num_edges / max_edges

    simplicity = 1 - complexity
    return max(0.0, min(1.0, simplicity))


def calculate_generalization(event_log_or_path: Union[str, pd.DataFrame],
                             dfg: Dict[Tuple[str, str], int]) -> float:
    """
    Calculate generalization: ability to handle unseen behavior.

    Simplified estimation based on:
    - Number of unique cases vs total events
    - Edge frequency distribution

    Higher generalization = model can handle variations not in training log.

    Args:
        event_log_or_path: Path to XES file OR pre-loaded DataFrame
        dfg: Directly-follows graph

    Returns:
        generalization: Score between 0 and 1
    """
    # Load or use provided DataFrame
    event_log = _ensure_dataframe(event_log_or_path)

    num_cases = len(event_log['case:concept:name'].unique())
    num_events = len(event_log)

    if not dfg or num_cases == 0:
        return 0.5

    # Estimate based on log size and model coverage
    avg_trace_length = num_events / num_cases

    # More diverse logs should lead to better generalization estimates
    # This is a simplified heuristic
    freq_values = list(dfg.values())
    if freq_values:
        avg_freq = sum(freq_values) / len(freq_values)
        min_freq = min(freq_values)

        # Models with more uniform edge frequencies generalize better
        freq_variance = sum((f - avg_freq) ** 2 for f in freq_values) / len(freq_values)

        # Normalize variance penalty
        variance_penalty = min(1.0, freq_variance / (avg_freq ** 2)) if avg_freq > 0 else 0

        generalization = 1 - variance_penalty
    else:
        generalization = 0.5

    return max(0.0, min(1.0, generalization))


def evaluate_model(event_log_path: str,
                   dfg: Dict[Tuple[str, str], int],
                   start_activities: Set[str],
                   end_activities: Set[str]) -> dict:
    """
    Comprehensive evaluation of the discovered process model.

    Loads the event log ONCE and reuses it across all metric calculations
    for improved performance on large datasets.

    Args:
        event_log_path: Path to XES file
        dfg: Discovered directly-follows graph
        start_activities: Start activities
        end_activities: End activities

    Returns:
        metrics: Dictionary with all evaluation metrics
    """
    # Load event log ONCE for all metrics
    event_log_df = pm4py.convert_to_dataframe(read_xes(event_log_path))

    # Get unique activities
    activities = set()
    for (src, tgt) in dfg.keys():
        activities.add(src)
        activities.add(tgt)

    num_activities = len(activities)

    # Calculate individual metrics (pass DataFrame, not path)
    fitness = calculate_replay_fitness(
        event_log_df, dfg, start_activities, end_activities
    )

    precision = calculate_precision(event_log_df, dfg)

    simplicity = calculate_simplicity(dfg, num_activities)

    generalization = calculate_generalization(event_log_df, dfg)

    # Calculate composite scores
    f_score = (fitness + precision) / 2  # F-measure approximation

    # Overall quality score (weighted average)
    weights = {
        'fitness': 0.4,
        'precision': 0.3,
        'simplicity': 0.15,
        'generalization': 0.15
    }

    overall_score = (
        weights['fitness'] * fitness +
        weights['precision'] * precision +
        weights['simplicity'] * simplicity +
        weights['generalization'] * generalization
    )

    return {
        'overall_score': round(overall_score, 6),
        'fitness_score': round(fitness, 6),
        'precision_score': round(precision, 6),
        'simplicity_score': round(simplicity, 6),
        'generalization_score': round(generalization, 6),
        'f_score': round(f_score, 6),
        'num_activities': num_activities,
        'num_edges': len(dfg),
        'model_stats': {
            'start_activities': sorted(list(start_activities)),
            'end_activities': sorted(list(end_activities)),
            'activities': sorted(list(activities))
        }
    }


def save_metrics(metrics: dict, output_path: str):
    """Save metrics to JSON file."""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
