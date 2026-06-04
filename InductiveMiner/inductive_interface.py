import pm4py
from discovery import discover_process_tree
from petri_converter import dict_to_pm4py_tree


def run_inductive_miner_from_df(df):
    """
    Run the Inductive Miner algorithm on a pandas DataFrame event log.
    
    This is the main API function for external experiment frameworks.
    It executes the complete discovery pipeline and returns a Petri net.
    
    Parameters:
        df: pandas DataFrame with columns 'case:concept:name' and 'concept:name'
            representing the event log
    
    Returns:
        net: pm4py Petri net object
        initial_marking: pm4py marking object for the initial state
        final_marking: pm4py marking object for the final state
    
    Note:
        This function does not perform any file I/O or printing.
        All outputs are returned as objects for further processing.
    """
    
    # Step 1: Discover the process tree using our custom algorithm
    custom_tree = discover_process_tree(df)
    
    # Step 2: Convert custom tree dictionary to pm4py ProcessTree
    pm4py_tree = dict_to_pm4py_tree(custom_tree)
    
    # Step 3: Convert ProcessTree to Petri Net
    net, initial_marking, final_marking = pm4py.convert_to_petri_net(pm4py_tree)
    
    # Step 4: Assign internal name to the Petri net
    net.name = 'InductiveMinerResult'
    
    # Step 5: Return the Petri net components
    return net, initial_marking, final_marking

# ============================================================================
# INDEPENDENT TEST BLOCK
# ============================================================================

if __name__ == '__main__':
    from event_log import load_real_log
    
    print("=" * 80)
    print("TESTING INDUCTIVE MINER INTERFACE")
    print("=" * 80)
    
    # Load the BPI Challenge 2017 log (relative path from repository root)
    LOG_FILE_PATH = "../BPI Challenge 2017_1_all/BPI Challenge 2017.xes.gz"
    
    print(f"\nLoading log from: {LOG_FILE_PATH}")
    df = load_real_log(LOG_FILE_PATH)
    
    print(f"Log loaded: {len(df):,} events, {df['case:concept:name'].nunique():,} cases")
    
    # Run the Inductive Miner
    print("\nRunning Inductive Miner algorithm...")
    net, initial_marking, final_marking = run_inductive_miner_from_df(df)
    
    # Print success message with net statistics
    print("\n" + "=" * 80)
    print("✓ SUCCESS - Petri Net Generated")
    print("=" * 80)
    print(f"\nPetri Net Statistics:")
    print(f"  Name: {net.name}")
    print(f"  Places: {len(net.places)}")
    print(f"  Transitions: {len(net.transitions)}")
    print(f"  Arcs: {len(net.arcs)}")
    print(f"\nInitial Marking: {initial_marking}")
    print(f"Final Marking: {final_marking}")
    print("\n" + "=" * 80)
    print("Interface test completed successfully!")
    print("=" * 80)