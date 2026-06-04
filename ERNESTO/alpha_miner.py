# USE THE CONDA ENVIRONMENT WITH PM4PY INSTALLED TO RUN THIS SCRIPT
# conda activate process-mining
import pm4py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

"""
Event Log Analysis Script
Load and explore the BPI Challenge 2017 event data
"""

# Path to event data
DATA_DIR = Path(__file__).parent.parent / "BPI Challenge 2017_1_all"
XES_FILE = DATA_DIR / "BPI Challenge 2017.xes"

def load_event_log():
    """Load the XES event log"""
    print(f"Loading event log from: {XES_FILE}")
    # Load event log using pm4py [1]
    df = pm4py.read_xes(XES_FILE)
    return df

def apply_alpha_miner(df):
    """Apply Alpha Miner algorithm for process discovery"""

    # Convert DataFrame to event log format if needed
    if isinstance(df, pd.DataFrame):
        event_log = pm4py.convert_to_event_log(df)
    else:
        event_log = df

    # Discover process model using Alpha Miner [1]
    process_model = pm4py.discover_petri_net_alpha(event_log)

    return process_model

def visualize_petri_net(petri_net):
    """Visualize the discovered Petri net"""
    net, im, fm = petri_net

    # Save visualization
    output_path = Path(__file__).parent / "alpha_miner_output.png"
    pm4py.save_vis_petri_net(net, im, fm, output_path)
    print(f"Petri net visualization saved to: {output_path}")

    return output_path


def get_process_metrics(df, petri_net):
    """Calculate fitness and precision metrics"""
    net, im, fm = petri_net
    event_log = pm4py.convert_to_event_log(df)

    # Calculate conformance checking
    fitness = pm4py.fitness_token_based_replay(event_log, net, im, fm)
    precision = pm4py.precision_token_based_replay(event_log, net, im, fm)

    print(f"Fitness: {fitness['average_trace_fitness']}")
    print(f"Precision: {precision}")

    return fitness, precision

def main():
    """Main execution function"""
    # Step 1: Load event log
    df = load_event_log()
    print(f"Loaded {len(df)} events")

    # Step 2: Apply Alpha Miner
    petri_net = apply_alpha_miner(df)

    # Step 3: Visualize results
    visualize_petri_net(petri_net)

    # Step 4: Get process tree (alternative representation)
    process_tree = pm4py.discover_process_tree(pm4py.convert_to_event_log(df))
    print(f"Discovered process tree: {process_tree}")

    # Step 5: Calculate process metrics
    fitness, precision = get_process_metrics(df, petri_net)

    return petri_net, fitness, precision

if __name__ == "__main__":
    main()