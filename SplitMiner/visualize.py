import pm4py
from pm4py.visualization.petri_net import visualizer
import os

# Load the BPMN/PNML file
net, initial_marking, final_marking = pm4py.read_pnml(
    "SplitMiner/output/result_split_miner.pnml"
)

# Visualize
fig = visualizer.apply(net, initial_marking, final_marking)

# Save visualization
visualizer.save(fig, "SplitMiner/output/split_miner_visualization.png")
print("✓ Visualization saved to: SplitMiner/output/split_miner_visualization.png")
