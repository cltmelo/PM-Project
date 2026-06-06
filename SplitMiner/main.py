"""
main.py - Entry point for SplitMiner algorithm
Orchestrates the complete process discovery pipeline
OPTIMIZED: Reuses DataFrame across all steps, no redundant file I/O [1]
"""
import os
import sys
import time
from typing import Dict, Set, Tuple
import pandas as pd
import pm4py
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# =============================================================================
# IMPORTS - All pipeline components
# =============================================================================
from SplitMiner.dfg_builder import (
    build_dfg_fast,                    # Step 1: Fast DFG construction
    filter_rare_variants,              # Step 1.5: Remove rare trace variants
    filter_dfg,                        # Step 2: Filter DFG edges
    add_source_sink_to_filtered_dfg,   # Step 2: Add markers after filtering
)
from SplitMiner.concurrency import (
    detect_concurrency_fast            # Step 3: Vectorized concurrency detection
)
from SplitMiner.gateway_discovery import (
    discover_all_gateways              # Step 4: XOR/AND gateway discovery
)
from SplitMiner.loop_discovery import (
    get_loop_structures                # Step 5: Loop/back-edge detection
)
from SplitMiner.bpmn_exporter import (
    export_model                       # Step 6: BPMN/PNML export
)
from SplitMiner.metrics import (
    evaluate_model,                    # Step 8: Alignment-based fitness evaluation
    save_metrics
)
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
# DFG Filtering
FILTER_THRESHOLD_TYPE = 'frequency'      # 'frequency' or 'relative'
FILTER_THRESHOLD_VALUE = 0.15            # 15% of cases must contain the edge
# Rare Variant Pre-filtering
FILTER_RARE_VARIANTS = True              # Enable/disable rare variant removal
MIN_VARIANT_FREQ = 3                     # Minimum occurrences per variant
# Concurrency Detection
MIN_CONCURRENCY_SUPPORT = 0.01           # 1% of cases for concurrency detection
# Model Markers (explicit - do NOT use get_start_activities/get_end_activities)
START_MARKER = '>>'
END_MARKER = '<<'
# Export Settings
GENERATE_VISUALIZATION = True            # Generate PNG from PNML
# =============================================================================
# MAIN PIPELINE
# =============================================================================
def main():
    """
    Main execution function for SplitMiner algorithm.

    Pipeline Steps:
    1. Build DFG (fast, vectorized)
    1.5. Filter rare variants (optional pre-processing)
    2. Filter DFG edges + Add source/sink markers
    3. Detect concurrency relations
    4. Discover gateways (XOR/AND split-join)
    5. Detect loops/back-edges
    6. Export BPMN and PNML models
    7. Generate PNG visualization
    8. Evaluate model quality (alignment-based fitness)

    All steps after Step 1 receive event_log_df as parameter - no file reloads [1].
    """
    pipeline_start = time.time()

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
    # STEP 1: Build Directly-Follows Graph (DFG) - VECTORIZED
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 1: Building Directly-Follows Graph (DFG) - VECTORIZED")
    print("-" * 70)

    start_time = time.time()

    # CRITICAL: Returns THREE values including event_log_df for reuse [1]
    dfg_raw, activity_freq, event_log_df = build_dfg_fast(EVENT_LOG_PATH)

    build_time = time.time() - start_time
    num_cases = event_log_df['case:concept:name'].nunique()

    print(f"✓ Built raw DFG with {len(dfg_raw)} edges")
    print(f"✓ Found {len(activity_freq)} unique activities")
    print(f"✓ Loaded {len(event_log_df)} events in {num_cases} cases")
    print(f"  Time: {build_time:.2f}s")

    # ==========================================================================
    # STEP 1.5: Filter Rare Variants (Optional Pre-processing)
    # ==========================================================================
    if FILTER_RARE_VARIANTS:
        print("\n" + "-" * 70)
        print("STEP 1.5: Filtering Rare Variants (Noise Removal)")
        print("-" * 70)

        start_time = time.time()

        # Filter cases with infrequent activity sequences
        event_log_df = filter_rare_variants(
            event_log_df=event_log_df,      # Pass DataFrame (no reload)
            min_variant_freq=MIN_VARIANT_FREQ,
            verbose=True
        )

        # Rebuild DFG from filtered DataFrame
        # FIX: pm4py.discover_directly_follows_graph returns 3 values, not 2 [1]
        dfg_raw, _, _ = pm4py.discover_directly_follows_graph(event_log_df)
        dfg_raw = {key: int(value) for key, value in dfg_raw.items()}
        activity_freq = dict(event_log_df['concept:name'].value_counts())

        variant_filter_time = time.time() - start_time
        print(f"✓ Rebuilt DFG with {len(dfg_raw)} edges from filtered log")
        print(f"  Time: {variant_filter_time:.2f}s")

    # ==========================================================================
    # STEP 2: Filter DFG Edges + Add Source/Sink Markers
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 2: Filtering DFG (Case-Based Thresholding)")
    print("-" * 70)

    start_time = time.time()

    # Filter DFG using case-based frequency (not raw occurrence count)
    dfg_filtered = filter_dfg(
        dfg=dfg_raw,
        activity_freq=activity_freq,
        threshold_type=FILTER_THRESHOLD_TYPE,
        threshold_value=FILTER_THRESHOLD_VALUE,
        event_log_df=event_log_df  # Pass DataFrame for case counting
    )

    filter_time = time.time() - start_time
    edges_removed = len(dfg_raw) - len(dfg_filtered)

    print(f"✓ Filtered DFG: {len(dfg_filtered)} edges ({edges_removed} removed)")
    print(f"  Filter type: {FILTER_THRESHOLD_TYPE}, threshold: {FILTER_THRESHOLD_VALUE}")
    print(f"  Time: {filter_time:.2f}s")

    # Immediately add source/sink markers AFTER filtering (must not be filtered out)
    print("\n" + "-" * 70)
    print("STEP 2b: Adding Source/Sink Markers to Filtered DFG")
    print("-" * 70)

    dfg_filtered, activity_freq = add_source_sink_to_filtered_dfg(
        dfg=dfg_filtered,
        activity_freq=activity_freq,
        event_log_df=event_log_df,
        start_marker=START_MARKER,
        end_marker=END_MARKER
    )

    print(f"✓ Added {START_MARKER} and {END_MARKER} markers to DFG")
    print(f"  Final DFG edges: {len(dfg_filtered)}")

    # ==========================================================================
    # STEP 3: Detect Concurrency Relations - VECTORIZED
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 3: Discovering Concurrency Relations - VECTORIZED")
    print("-" * 70)

    start_time = time.time()

    # Pass DataFrame directly (no file reload)
    concurrent_pairs = detect_concurrency_fast(
        event_log_df=event_log_df,
        dfg=dfg_filtered,            # Use filtered DFG
        min_support=MIN_CONCURRENCY_SUPPORT
    )

    concurrency_time = time.time() - start_time

    print(f"✓ Found {len(concurrent_pairs)} concurrent activity pairs")
    if concurrent_pairs:
        examples = list(concurrent_pairs)[:5]
        print(f"  Examples: {examples}")
    print(f"  Time: {concurrency_time:.2f}s")

    # ==========================================================================
    # STEP 4: Discover Gateways (XOR/AND Split-Join)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 4: Discovering Gateways")
    print("-" * 70)

    split_gateways, join_gateways = discover_all_gateways(
        dfg=dfg_filtered,                  # Use DFG WITH markers
        concurrent_pairs=concurrent_pairs,
        activity_freq=activity_freq
    )

    print(f"✓ Split gateways: {len(split_gateways)}")
    print(f"✓ Join gateways: {len(join_gateways)}")

    # Count gateway types
    from SplitMiner.gateway_discovery import GatewayType
    and_splits = sum(1 for g in split_gateways.values() if str(g) == 'AND')
    xor_splits = sum(1 for g in split_gateways.values() if str(g) == 'XOR')
    and_joins = sum(1 for g in join_gateways.values() if str(g) == 'AND')
    xor_joins = sum(1 for g in join_gateways.values() if str(g) == 'XOR')

    print(f"  AND splits: {and_splits}, XOR splits: {xor_splits}")
    print(f"  AND joins: {and_joins}, XOR joins: {xor_joins}")

    # ==========================================================================
    # STEP 5: Detect Loops and Back-Edges
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 5: Detecting Loops")
    print("-" * 70)

    loop_structures = get_loop_structures(dfg_filtered)

    print(f"✓ Identified {len(loop_structures)} loop structures")

    # ==========================================================================
    # STEP 6: Export Models (BPMN and PNML)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 6: Exporting Models")
    print("-" * 70)

    # Use EXPLICIT markers - DO NOT call get_start_activities/get_end_activities
    start_activities = {START_MARKER}   # {'>>'}
    end_activities = {END_MARKER}       # {'<<'}

    # Export BPMN (for visualization in BPMN tools)
    bpmn_path = export_model(
        dfg=dfg_filtered,
        split_gateways=split_gateways,
        join_gateways=join_gateways,
        concurrent_pairs=concurrent_pairs,
        loop_info=loop_structures,
        output_dir=OUTPUT_DIR,
        format='bpmn',
        start_activities=start_activities,
        end_activities=end_activities
    )
    print(f"✓ Exported BPMN: {bpmn_path}")

    # Export PNML first (needed for Petri net analysis and visualization)
    pnml_path = export_model(
        dfg=dfg_filtered,
        split_gateways=split_gateways,
        join_gateways=join_gateways,
        concurrent_pairs=concurrent_pairs,
        loop_info=loop_structures,
        output_dir=OUTPUT_DIR,
        format='pnml',
        start_activities=start_activities,
        end_activities=end_activities
    )
    print(f"✓ Exported PNML: {pnml_path}")

    # ==========================================================================
    # STEP 7: Generate PNG Visualization from PNML
    # ==========================================================================
    if GENERATE_VISUALIZATION:
        print("\n" + "-" * 70)
        print("STEP 7: Generating PNG Visualization")
        print("-" * 70)

        try:
            png_path = os.path.join(OUTPUT_DIR, "model.png")

            # Load Petri net from PNML
            net, initial_marking, final_marking = pm4py.read_pnml(pnml_path)

            # Generate visualization
            from pm4py.visualization.petri_net import visualizer as pn_visualizer
            # Generate visualization object
            gviz = pn_visualizer.apply(net, initial_marking, final_marking)
            # Save to file
            pn_visualizer.save(gviz, png_path)
            print(f"✓ Generated visualization: {png_path}")
        except Exception as e:
            print(f"⚠ Visualization generation failed: {e}")
            print("  (Install graphviz and pygraphviz for PNG support)")

    # ==========================================================================
    # STEP 8: Evaluate Model Quality (Alignment-Based Fitness)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("STEP 8: Evaluating Model Quality")
    print("-" * 70)

    # Pass DataFrame directly - NO file reload
    metrics = evaluate_model(
        event_log_df=event_log_df,         # DataFrame from Step 1
        dfg=dfg_filtered,
        start_activities=start_activities,
        end_activities=end_activities,
        pnml_file=pnml_path,
        split_gateways=split_gateways,
        join_gateways=join_gateways
    )

    print(f"✓ Fitness:        {metrics['fitness_score']:.4f}")
    print(f"✓ Precision:      {metrics['precision_score']:.4f}")
    print(f"✓ Generalization: {metrics['generalization_score']:.4f}")
    print(f"✓ Simplicity:     {metrics['simplicity_score']:.4f}")
    print(f"✓ F-Score:        {metrics['f_score']:.4f}")
    print(f"✓ Overall Score:  {metrics['overall_score']:.4f}")
    print(f"✓ CFC:            {metrics['cfc']:.4f}")
    print(f"✓ Structuredness: {metrics['structuredness']:.4f}")

    # Save metrics to JSON
    metrics_path = os.path.join(OUTPUT_DIR, "result_scores.json")
    save_metrics(metrics, metrics_path)

    # ==========================================================================
    # PIPELINE COMPLETE
    # ==========================================================================
    total_time = time.time() - pipeline_start

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Total time: {total_time:.2f}s")
    print(f"Output files:")
    print(f"  • {bpmn_path}")
    print(f"  • {pnml_path}")
    if GENERATE_VISUALIZATION:
        print(f"  • {os.path.join(OUTPUT_DIR, 'model.png')}")
    print(f"  • {metrics_path}")
    print("=" * 70)

    return metrics
# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    main()
