"""
metrics.py - Evaluate fitness, precision, and simplicity of discovered process model
UPDATED: Alignment-based fitness (primary) with token-based replay fallback [1].
Passes DataFrame directly throughout pipeline - no redundant file I/O [1].
Includes CFC and Structuredness metrics using gateway information [1].
FIXED:
- Bug 1: Use log_fitness/average_trace_fitness (0-1 scale) instead of perc_fit_traces (0-100)
- Bug 2: Add error logging for generalization failure and proper EventLog conversion
"""
import json
import os
from typing import Dict, Set, Tuple, Union, Optional
import pandas as pd
import pm4py
# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _ensure_dataframe(event_log_or_path: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Helper function to ensure we have a DataFrame.

    Args:
        event_log_or_path: Path to XES file OR pre-loaded DataFrame

    Returns:
        event_log_df: Event log as DataFrame
    """
    if isinstance(event_log_or_path, str):
        try:
            event_log_obj = pm4py.read_xes(event_log_or_path)
            return pm4py.convert_to_dataframe(event_log_obj)
        except Exception as e:
            print(f"⚠ Warning: Could not load event log: {e}")
            return pd.DataFrame()
    else:
        return event_log_or_path
def _run_alignments(event_log_df: pd.DataFrame,
                    net,
                    initial_marking,
                    final_marking,
                    timeout_seconds: int = 120) -> Optional[float]:
    """
    Calculate alignment-based fitness using pm4py's alignment algorithm.

    Wrapped in ThreadPoolExecutor with timeout to prevent pipeline freeze
    on large logs like BPI 2017 (~31k cases) [1].

    Args:
        event_log_df: Pre-loaded DataFrame (must NOT reload from disk)
        net: Petri net model
        initial_marking: Initial marking of the net
        final_marking: Final marking of the net
        timeout_seconds: Maximum time to wait for alignment (default: 120s)

    Returns:
        fitness: Alignment-based fitness score (0-1), or None if failed/timed out
    """
    from pm4py.algo.evaluation.replay_fitness import algorithm as rf_algo
    from pm4py.algo.evaluation.replay_fitness.variants import alignment_based as ab_variant
    from SplitMiner.dfg_builder import add_source_sink_to_log
    from concurrent.futures import ThreadPoolExecutor

    def _compute_alignment():
        """Inner function to run alignment computation."""
        # Add synthetic start/end events to log for proper alignment
        log_with_ss = add_source_sink_to_log(event_log_df)

        # Run alignment-based replay
        result = rf_algo.apply(
            log_with_ss,
            net,
            initial_marking,
            final_marking,
            variant=ab_variant
        )

        # Extract fitness from result (already in 0-1 scale)
        fitness = result.get('log_fitness', result.get('average_trace_fitness', None))

        return float(fitness) if fitness is not None else None

    try:
        # Run alignment with timeout to prevent pipeline freeze [1]
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_compute_alignment)
        try:
            fitness_score = future.result(timeout=timeout_seconds)
            executor.shutdown(wait=False)
            print(f"✓ Alignment-based fitness computed in timeout window ({timeout_seconds}s)")
            return fitness_score
        except TimeoutError:
            executor.shutdown(wait=False)
            print(f"⚠ Alignment computation timed out after {timeout_seconds}s - falling back to token-based replay")
            return None
        except Exception as e:
            executor.shutdown(wait=False)
            print(f"⚠ Alignment-based fitness failed: {e}")
            return None

    except Exception as e:
        print(f"⚠ Alignment executor setup failed: {e}")
        return None
# =============================================================================
# MAIN EVALUATION FUNCTION
# =============================================================================
def evaluate_model(event_log_df: pd.DataFrame,
                   dfg: Dict[Tuple[str, str], int],
                   start_activities: Set[str],
                   end_activities: Set[str],
                   pnml_file: str,
                   split_gateways: Dict[str, str],
                   join_gateways: Dict[str, str]) -> Dict[str, float]:
    """
    Comprehensive evaluation of the discovered process model.

    Uses alignment-based fitness (primary) with token-based replay fallback [1].
    Passes DataFrame directly - no file reload after Step 1 [1].
    Includes CFC and Structuredness metrics using gateway information [1].

    Args:
        event_log_df: Pre-loaded DataFrame (NOT file path - avoids reloading)
        dfg: Discovered directly-follows graph
        start_activities: Start activities set
        end_activities: End activities set
        pnml_file: Path to PNML file for Petri net loading [1]
        split_gateways: Split gateway mapping for CFC/Structuredness [1]
        join_gateways: Join gateway mapping for CFC/Structuredness [1]

    Returns:
        metrics: Dictionary with all evaluation metrics
    """
    from SplitMiner.dfg_builder import add_source_sink_to_log

    # Get unique activities from DFG
    activities = set()
    for (src, tgt) in dfg.keys():
        activities.add(src)
        activities.add(tgt)

    num_activities = len(activities)

    # Load Petri net from PNML file [1]
    try:
        net, initial_marking, final_marking = pm4py.read_pnml(pnml_file)
        net_loaded = True
    except Exception as e:
        print(f"⚠ Warning: Could not load Petri net from PNML: {e}")
        net_loaded = False
        net = None
        initial_marking = None
        final_marking = None

    # CRITICAL: Add synthetic >> and << events BEFORE any conformance checking
    # The PNML uses >> and << as start/end markers, so the log must have them too [1]
    log_with_ss = add_source_sink_to_log(event_log_df)

    # ================================================================
    # FITNESS: Alignment-based (primary) → Token-based (fallback)
    # ================================================================
    fitness_score = None

    if net_loaded and initial_marking is not None and final_marking is not None:
        # Try alignment-based fitness first (preferred method)
        fitness_score = _run_alignments(
            event_log_df=log_with_ss,  # Use log WITH synthetic events
            net=net,
            initial_marking=initial_marking,
            final_marking=final_marking
        )

    # Fallback to token-based replay if alignment failed
    if fitness_score is None and net_loaded:
        try:
            result = pm4py.fitness_token_based_replay(
                log_with_ss,  # Use log WITH synthetic events
                net,
                initial_marking,
                final_marking
            )
            # FIX Bug 1: Use log_fitness or average_trace_fitness (0-1 scale)
            # NOT perc_fit_traces which is 0-100 percentage [1]
            fitness_score = result.get('log_fitness', result.get('average_trace_fitness', 0.5))
        except Exception as e:
            print(f"⚠ Token-based replay also failed: {e}")
            fitness_score = 0.5

    if fitness_score is None:
        fitness_score = 0.5

    # Ensure fitness is in valid range [0, 1]
    fitness_score = max(0.0, min(1.0, float(fitness_score)))

    # ================================================================
    # PRECISION: ETC (escaping edges) → Token-based fallback
    # ================================================================
    precision_score = 0.75  # Default estimate

    if net_loaded:
        try:
            # Try ETC precision first (more accurate)
            from pm4py.algo.evaluation.precision import algorithm as prec_algo
            from pm4py.algo.evaluation.precision.variants import etconformance_token as etc_variant

            precision_result = prec_algo.apply(
                log_with_ss,  # Use log WITH synthetic events
                net,
                initial_marking,
                final_marking,
                variant=etc_variant
            )
            precision_score = float(precision_result)
        except Exception as e:
            print(f"⚠ ETC precision failed, falling back to token-based: {e}")
            try:
                # Fallback to token-based precision
                precision_result = pm4py.precision_token_based_replay(
                    log_with_ss,  # Use log WITH synthetic events
                    net,
                    initial_marking,
                    final_marking
                )
                precision_score = float(precision_result)
            except Exception as e2:
                print(f"⚠ Token-based precision also failed: {e2}")
                precision_score = 0.75

    # Ensure precision is in valid range [0, 1]
    precision_score = max(0.0, min(1.0, float(precision_score)))

    # ================================================================
    # GENERALIZATION: Token-based replay
    # ================================================================
    generalization_score = 0.5
    if net_loaded:
        try:
            # Convert DataFrame to EventLog for generalization
            event_log_obj = pm4py.convert_to_event_log(log_with_ss)

            # FIX: Use correct low-level import - pm4py.generalization_token_based_replay doesn't exist
            from pm4py.algo.evaluation.generalization import algorithm as gen_algo

            generalization_result = gen_algo.apply(
                event_log_obj,  # Requires EventLog object, not DataFrame
                net,
                initial_marking,
                final_marking
            )
            generalization_score = float(generalization_result)

        except Exception as e:
            # Print the actual error for debugging
            print(f"⚠ Generalization failed: {e}")
            print(f"  Falling back to estimate from fitness+precision")

            # Estimate from fitness/precision (both now in correct 0-1 range)
            generalization_score = 0.5 * (fitness_score + precision_score)
    # Ensure generalization is in valid range [0, 1]
    generalization_score = max(0.0, min(1.0, float(generalization_score)))

    # ================================================================
    # SIMPLICITY: Based on Petri net structure
    # ================================================================
    simplicity_score = 0.5

    if net_loaded:
        try:
            num_places = len(net.places)
            num_transitions = len(net.transitions)
            num_arcs = len(net.arcs)

            # Simplicity = 1 - (complexity / max_complexity)
            complexity = num_places + num_transitions + num_arcs
            max_complexity = 1000.0  # Normalize to reasonable scale
            simplicity_score = max(0.0, min(1.0, 1.0 - (complexity / max_complexity)))
        except Exception as e:
            print(f"⚠ Simplicity calculation failed: {e}")
            simplicity_score = 0.5

    # ================================================================
    # CFC (Control Flow Complexity)
    # Sum of (len(successors)-1) for each activity with multiple successors [1]
    # ================================================================
    from collections import defaultdict
    successors = defaultdict(set)

    # FIX: Use dfg.keys() not dfg.items() - items yields ((src,tgt), freq) pairs
    for (src, tgt) in dfg.keys():
        successors[src].add(tgt)

    cfc = 0.0
    for activity, succ_set in successors.items():
        if len(succ_set) > 1:
            cfc += len(succ_set) - 1

    # ================================================================
    # STRUCTUREDNESS: Fraction of gateways that are XOR (not AND) [1]
    # ================================================================
    total_gateways = len(split_gateways) + len(join_gateways)
    xor_gateways = 0

    if total_gateways > 0:
        for gw_type in split_gateways.values():
            if str(gw_type) in ('XOR', 'GatewayType.XOR'):
                xor_gateways += 1

        for gw_type in join_gateways.values():
            if str(gw_type) in ('XOR', 'GatewayType.XOR'):
                xor_gateways += 1

        structuredness = xor_gateways / total_gateways
    else:
        structuredness = 1.0  # No gateways = fully structured

    # ================================================================
    # COMPOSITE SCORES
    # ================================================================

    # F-score: harmonic mean of fitness and precision
    if fitness_score > 0 and precision_score > 0:
        f_score = 2 * fitness_score * precision_score / (fitness_score + precision_score)
    else:
        f_score = 0.0

    # Overall quality score (weighted average) [1]
    weights = {
        'fitness': 0.4,
        'precision': 0.3,
        'generalization': 0.2,
        'simplicity': 0.1
    }

    overall_score = (
        weights['fitness'] * fitness_score +
        weights['precision'] * precision_score +
        weights['generalization'] * generalization_score +
        weights['simplicity'] * simplicity_score
    )

    # ================================================================
    # RETURN METRICS DICTIONARY
    # ================================================================
    return {
        'fitness_score': round(float(fitness_score), 6),
        'precision_score': round(float(precision_score), 6),
        'generalization_score': round(float(generalization_score), 6),
        'simplicity_score': round(float(simplicity_score), 6),
        'f_score': round(float(f_score), 6),
        'overall_score': round(float(overall_score), 6),
        'cfc': round(float(cfc), 6),
        'structuredness': round(float(structuredness), 6),
        'num_activities': num_activities,
        'num_edges': len(dfg)
    }
# =============================================================================
# SAVE METRICS TO FILE
# =============================================================================
def save_metrics(metrics: dict, output_path: str):
    """
    Save metrics to JSON file.

    Args:
        metrics: Dictionary containing evaluation metrics
        output_path: Path to save JSON file [1]
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

        print(f"  ✓ Metrics saved to: {output_path}")
    except Exception as e:
        print(f"  ⚠ Warning: Could not save metrics: {e}")
