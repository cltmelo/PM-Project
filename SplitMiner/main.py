"""
main.py - Entry point for SplitMiner algorithm
Orchestrates the complete process discovery pipeline
OPTIMIZED: Reuses DataFrame across steps, exports multiple formats, generates visualization
"""
import os
import sys
import time
from typing import Dict, Set, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from SplitMiner.dfg_builder import (
    build_dfg_fast,  # Use optimized version
    filter_dfg,
    get_start_activities,
    get_end_activities
)
from SplitMiner.concurrency import detect_concurrency_fast
from SplitMiner.gateway_discovery import discover_all_gateways
from SplitMiner.loop_discovery import detect_back_edges, get_loop_structures
from SplitMiner.bpmn_exporter import export_model
from SplitMiner.metrics import evaluate_model, save_metrics

# =============================================================================
# CONFIGURATION
# =============================================================================

# Input/Output paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENT_LOG_PATH = os.path.join(
    PROJECT_ROOT,
    "BPI Challenge 2017_1_all",
    "BPI Challenge 2017.xes.gz"
)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "SplitMiner", "output")

# Algorithm parameters
FILTER_THRESHOLD_TYPE = 'frequency'
FILTER_THRESHOLD_VALUE = 0.02
MIN_CONCURRENCY_SUPPORT = 0.01


def main():
    """
    Main execution function for SplitMiner algorithm.
    """
    print("=" * 70)
    print("SPLIT MINER - Process Discovery Algorithm (OPTIMIZED)")
    print("Based on: Augusto et al. (2017)")
    print("=" * 70)

    # Verify input file exists
    if not os.path.exists(EVENT_LOG_PATH):
        print(f"\n❌ ERROR: Event log not found at: {EVENT_LOG_PATH}")
        print("\nPlease ensure the BPI Challenge 2017 dataset is in:")
        print(f"  {os.path.dirname(EVENT_LOG_PATH)}")
        sys.exit(1)

    print(f"\n📂 Event Log: {EVENT_LOG_PATH}")
    print(f"📁 Output Directory: {OUTPUT_DIR}")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ==========================================================================
    # STEP 1: Build Directly-Follows Graph (OPTIMIZED)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 1: Building Directly-Follows Graph (DFG) - VECTORIZED")
    print("-" * 70)

    start_time = time.time()
    dfg_raw, activity_freq, event_log_df = build_dfg_fast(EVENT_LOG_PATH)
    build_time = time.time() - start_time

    print(f"✓ Built raw DFG with {len(dfg_raw)} edges")
    print(f"✓ Found {len(activity_freq)} unique activities")
    print(f"✓ Loaded {len(event_log_df)} events in {len(event_log_df['case:concept:name'].unique())} cases")
    print(f"  Time: {build_time:.2f}s")

    # ==========================================================================
    # STEP 2: Filter DFG (Remove Noise)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 2: Filtering DFG (Noise Removal)")
    print("-" * 70)

    start_time = time.time()
    dfg_filtered = filter_dfg(
        dfg_raw,
        activity_freq,
        threshold_type=FILTER_THRESHOLD_TYPE,
        threshold_value=FILTER_THRESHOLD_VALUE
    )
    filter_time = time.time() - start_time

    edges_removed = len(dfg_raw) - len(dfg_filtered)
    print(f"✓ Filtered DFG: {len(dfg_filtered)} edges ({edges_removed} removed)")
    print(f"  Filter type: {FILTER_THRESHOLD_TYPE}, threshold: {FILTER_THRESHOLD_VALUE}")
    print(f"  Time: {filter_time:.2f}s")

    # ==========================================================================
    # STEP 3: Discover Concurrency Relations (OPTIMIZED)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 3: Discovering Concurrency Relations - VECTORIZED")
    print("-" * 70)

    start_time = time.time()
    # PASS DataFrame directly (no reload!)
    concurrent_pairs = detect_concurrency_fast(
        event_log_df=event_log_df,  # Reuse loaded DataFrame
        dfg=dfg_filtered,
        min_support=MIN_CONCURRENCY_SUPPORT
    )
    concurrency_time = time.time() - start_time

    print(f"✓ Found {len(concurrent_pairs)} concurrent activity pairs")
    if concurrent_pairs:
        print(f"  Examples: {list(concurrent_pairs)[:5]}")
    print(f"  Time: {concurrency_time:.2f}s")

    # ==========================================================================
    # STEP 4: Discover Gateways (Splits and Joins)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 4: Discovering Split/Join Gateways")
    print("-" * 70)

    start_time = time.time()
    split_gateways, join_gateways = discover_all_gateways(
        dfg_filtered,
        concurrent_pairs,
        activity_freq
    )
    gateway_time = time.time() - start_time

    print(f"✓ Split gateways: {len(split_gateways)}")
    print(f"✓ Join gateways: {len(join_gateways)}")

    if split_gateways:
        print(f"  Splits: {split_gateways}")
    if join_gateways:
        print(f"  Joins: {join_gateways}")
    print(f"  Time: {gateway_time:.2f}s")

    # ==========================================================================
    # STEP 5: Discover Loops
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 5: Discovering Loops")
    print("-" * 70)

    start_time = time.time()
    loop_info = get_loop_structures(dfg_filtered)
    loop_time = time.time() - start_time

    print(f"✓ Back-edges detected: {len(loop_info['back_edges'])}")
    print(f"✓ Loops found: {loop_info['loop_count']}")
    if loop_info['loops']:
        print(f"  Example loops: {loop_info['loops'][:3]}")
    print(f"  Time: {loop_time:.2f}s")

    # ==========================================================================
    # STEP 6: Export Process Model (BOTH BPMN and PNML)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 6: Exporting Process Model (BPMN + PNML)")
    print("-" * 70)

    start_time = time.time()

    # Get start/end activities
    start_activities = get_start_activities(dfg_filtered, activity_freq)
    end_activities = get_end_activities(dfg_filtered, activity_freq)

    print(f"  Start activities: {sorted(list(start_activities))}")
    print(f"  End activities: {sorted(list(end_activities))}")

    # Export BPMN
    bpmn_file = export_model(
        dfg=dfg_filtered,
        split_gateways=split_gateways,
        join_gateways=join_gateways,
        concurrent_pairs=concurrent_pairs,
        loop_info=loop_info,
        output_dir=OUTPUT_DIR,
        format='bpmn',
        start_activities=start_activities,
        end_activities=end_activities
    )
    print(f"✓ BPMN exported to: {bpmn_file}")

    # Export PNML (with start/end activities for proper Petri net)
    pnml_file = export_model(
        dfg=dfg_filtered,
        split_gateways=split_gateways,
        join_gateways=join_gateways,
        concurrent_pairs=concurrent_pairs,
        loop_info=loop_info,
        output_dir=OUTPUT_DIR,
        format='pnml',
        start_activities=start_activities,
        end_activities=end_activities
    )
    print(f"✓ PNML exported to: {pnml_file}")

    export_time = time.time() - start_time
    print(f"  Time: {export_time:.2f}s")

    # ==========================================================================
    # STEP 7: Generate Visualization (PNG)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 7: Generating Process Model Visualization")
    print("-" * 70)

    start_time = time.time()

    try:
        import pm4py
        from pm4py.visualization.petri_net import visualizer

        # Read the PNML file
        net, initial_marking, final_marking = pm4py.read_pnml(pnml_file)

        # Generate visualization
        fig = visualizer.apply(net, initial_marking, final_marking)

        # Save as PNG
        view_file = os.path.join(OUTPUT_DIR, 'result_split_miner_view.png')
        visualizer.save(fig, view_file)

        print(f"✓ Visualization saved to: {view_file}")
    except Exception as e:
        print(f"⚠ Visualization failed: {str(e)}")
        print("  (You can still view the BPMN/PNML files in external tools)")
        view_file = None

    viz_time = time.time() - start_time
    print(f"  Time: {viz_time:.2f}s")

    # ==========================================================================
    # STEP 8: Evaluate Model Quality
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 8: Evaluating Model Quality")
    print("-" * 70)

    start_time = time.time()
    # PASS DataFrame directly (no reload!)
    metrics = evaluate_model(
        event_log_df,          # Reuse loaded DataFrame
        dfg_filtered,          # Filtered DFG
        start_activities,      # Start activities
        end_activities,        # End activities
        pnml_file              # FIX: Pass PNML path for conformance checking
    )
    eval_time = time.time() - start_time

    # Save metrics
    metrics_file = os.path.join(OUTPUT_DIR, 'result_scores.json')
    save_metrics(metrics, metrics_file)

    print(f"\n📊 EVALUATION METRICS:")
    print(f"  Overall Score:     {metrics['overall_score']:.4f}")
    print(f"  Fitness:           {metrics['fitness_score']:.4f}")
    print(f"  Precision:         {metrics['precision_score']:.4f}")
    print(f"  Simplicity:        {metrics['simplicity_score']:.4f}")
    print(f"  Generalization:    {metrics['generalization_score']:.4f}")
    print(f"  F-Score:           {metrics['f_score']:.4f}")
    print(f"\n  Activities:        {metrics['num_activities']}")
    print(f"  Edges:             {metrics['num_edges']}")
    print(f"\n✓ Metrics saved to: {metrics_file}")
    print(f"  Time: {eval_time:.2f}s")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    total_time = build_time + filter_time + concurrency_time + gateway_time + loop_time + export_time + viz_time + eval_time

    print("\n" + "=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)
    print(f"⏱ Total Time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    print(f"📁 Output Files:")
    print(f"   - BPMN Model: {bpmn_file}")
    print(f"   - PNML Model: {pnml_file}")
    if view_file:
        print(f"   - Visualization: {view_file}")
    print(f"   - Metrics: {metrics_file}")
    print("=" * 70)

    return metrics


if __name__ == "__main__":
    try:
        results = main()
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
