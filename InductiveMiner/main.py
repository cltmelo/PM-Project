from event_log import load_real_log, build_directly_follows_graph
from cut_detection import (
    detect_rule_a,
    detect_rule_b,
    detect_rule_c,
    detect_rule_d
)
from discovery import discover_process_tree, print_process_tree, MAX_RECURSION_DEPTH
from petri_converter import export_tree_to_pnml

import pm4py


# ============================================================================
# LOAD REAL LOG DATA (BPI Challenge 2017)
# ============================================================================

LOG_FILE_PATH = "../BPI Challenge 2017_1_all/BPI Challenge 2017.xes.gz"

print("=" * 80)
print("LOADING REAL EVENT LOG...")
print("=" * 80)

df_sample = load_real_log(LOG_FILE_PATH)

print(f"\nLog Statistics:")
print(f"  Total events: {len(df_sample):,}")
print(f"  Unique cases: {df_sample['case:concept:name'].nunique():,}")
print(f"  Unique activities: {df_sample['concept:name'].nunique()}")
print(f"\nColumns: {list(df_sample.columns)}")
print(f"\nFirst 10 rows:")
print(df_sample[['case:concept:name', 'concept:name']].head(10).to_string())

# Build DFG for validation
arcs, start_activities, end_activities = build_directly_follows_graph(df_sample, noise_threshold=0.015)

print(f"\nDirectly-Follows Graph (after noise filtering):")
print(f"  Total unique arcs: {len(arcs)}")
print(f"  Start activities ({len(start_activities)}): {sorted(start_activities)}")
print(f"  End activities ({len(end_activities)}): {sorted(end_activities)}")


# ============================================================================
# RUN PROCESS DISCOVERY
# ============================================================================

print("\n" + "=" * 80)
print("RUNNING PROCESS DISCOVERY ALGORITHM...")
print("=" * 80)
print()

process_tree = discover_process_tree(df_sample)

print("\nDISCOVERED PROCESS TREE:")
print("-" * 80)
print_process_tree(process_tree)
print("-" * 80)


# ============================================================================
# CONVERT TO PETRI NET
# ============================================================================

print("\n" + "=" * 80)
print("CONVERTING PROCESS TREE TO PETRI NET...")
print("=" * 80)

import pm4py
from petri_converter import dict_to_pm4py_tree

# Convert custom tree to pm4py ProcessTree
pm4py_tree = dict_to_pm4py_tree(process_tree)

# Convert ProcessTree to Petri Net
net, initial_marking, final_marking = pm4py.convert_to_petri_net(pm4py_tree)

# Assign internal name to the Petri net
net.name = 'InductiveMinerResult'

print(f"\n✓ Petri Net Created:")
print(f"  Places: {len(net.places)}")
print(f"  Transitions: {len(net.transitions)}")
print(f"  Arcs: {len(net.arcs)}")


# ============================================================================
# EXPORT TO MULTIPLE FORMATS
# ============================================================================

print("\n" + "=" * 80)
print("EXPORTING PROCESS MODEL...")
print("=" * 80)

# Ensure output directory exists
import os
output_dir = "output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# -----------------------------------------------------------
# Export 1: PNML File (Petri Net Markup Language)
# -----------------------------------------------------------
pnml_path = "output/petrinet_inductiveminer.pnml"
pm4py.write_pnml(net, initial_marking, final_marking, pnml_path)
print(f"\n✓ PNML exported: {pnml_path}")

# -----------------------------------------------------------
# Export 2: PNG Visualization
# -----------------------------------------------------------
png_path = "output/petrinet_inductiveminer.png"
pm4py.save_vis_petri_net(net, initial_marking, final_marking, png_path)
print(f"✓ PNG visualization exported: {png_path}")

# -----------------------------------------------------------
# Summary
# -----------------------------------------------------------
print(f"\n" + "=" * 80)
print("EXPORT SUMMARY")
print("=" * 80)
print(f"\nAll exports completed successfully!")
print(f"\nGenerated Files:")
print(f"  1. {pnml_path}")
print(f"     - Format: PNML (Petri Net Markup Language)")
print(f"     - Use: Import into ProM, Celonis, PM4Py")
print(f"\n  2. {png_path}")
print(f"     - Format: PNG Image")
print(f"     - Use: Visual inspection, reports, presentations")

print("\n" + "=" * 80)
print("PROCESS DISCOVERY COMPLETE")
print("=" * 80)