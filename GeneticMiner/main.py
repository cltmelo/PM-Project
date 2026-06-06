"""
Main Entry Point for Genetic Process Discovery.

This script serves as the primary entry point for running the genetic 
algorithm process discovery on the BPI Challenge 2017 dataset. It loads 
the event log, executes the evolutionary algorithm with predefined 
hyperparameters, and saves the results to disk.

Usage:
    python main.py
    
The script expects the BPI Challenge 2017 XES file to be located in the 
parent directory relative to this script's location.

Author: Senior Process Mining Engineer
Date: 2024
"""

from __future__ import annotations

import os
import sys
import pandas as pd
import pm4py
from interface import save_results
from genetic_miner import run_genetic_miner


if __name__ == "__main__":
    # (1) Define the XES file path
    xes_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        'BPI Challenge 2017_1_all',
        'BPI Challenge 2017.xes.gz'
    )
    
    # Check if file exists
    if not os.path.exists(xes_path):
        print(f"Error: XES file not found at '{xes_path}'")
        print("Please ensure the BPI Challenge 2017.xes.gz file is located in the parent directory.")
        sys.exit(1)
    
    # (2) OPTIMIZED algorithm hyperparameters as named constants
    POPULATION_SIZE = 50
    NUM_GENERATIONS = 50
    MUTATION_RATE = 0.2
    TOURNAMENT_SIZE = 3
    W_FITNESS = 0.7
    W_SIMPLICITY = 0.3
    MAX_BINDINGS = 3
    RANDOM_SEED = 42
    
    # Early stopping parameters - DISABLED
    # PATIENCE = 12
    # MIN_IMPROVEMENT = 0.0001
    
    try:
        # (3) Load the XES file and convert to DataFrame
        print(f"Loading event log from: {xes_path}")
        event_log = pm4py.read_xes(xes_path)
        df = pm4py.convert_to_dataframe(event_log)
        
        # Sort DataFrame by case and timestamp to ensure chronological order
        df = df.sort_values(["case:concept:name", "time:timestamp"])
        
        # Print loading statistics
        num_cases = df["case:concept:name"].nunique()
        num_events = len(df)
        print(f"Loaded {num_cases} cases with {num_events} events")
        
        # (4) Run the genetic algorithm - early stopping DISABLED
        print("\nStarting OPTIMIZED genetic process discovery...")
        print(f"Population size: {POPULATION_SIZE}")
        print(f"Generations: {NUM_GENERATIONS}")
        print(f"Mutation rate: {MUTATION_RATE}")
        print(f"Tournament size: {TOURNAMENT_SIZE}")
        print(f"Weights: fitness={W_FITNESS}, simplicity={W_SIMPLICITY}")
        print(f"Max bindings per activity: {MAX_BINDINGS}")
        print(f"Random seed: {RANDOM_SEED}")
        print(f"Early stopping: DISABLED (will run all {NUM_GENERATIONS} generations)")
        print("-" * 60)
        
        best_net, overall, fitness, simplicity, actual_generations = run_genetic_miner(
            df=df,
            population_size=POPULATION_SIZE,
            num_generations=NUM_GENERATIONS,
            mutation_rate=MUTATION_RATE,
            tournament_size=TOURNAMENT_SIZE,
            w_fitness=W_FITNESS,
            w_simplicity=W_SIMPLICITY,
            max_bindings_per_activity=MAX_BINDINGS,
            random_seed=RANDOM_SEED,
            elite_count=2
            # patience=PATIENCE,                # DISABLED
            # min_improvement=MIN_IMPROVEMENT   # DISABLED
        )
        
        # Print final scores
        print("-" * 60)
        print(f"\nEvolution completed after {actual_generations} generations")
        print("\nFinal Results:")
        print(f"  Overall score:    {overall:.6f}")
        print(f"  Fitness score:    {fitness:.6f}")
        print(f"  Simplicity score: {simplicity:.6f}")
        
        # Diagnostics for convergence analysis
        if fitness > 0.7 and simplicity < 0.1:
            print("\n⚠ WARNING: High fitness but very low simplicity detected.")
            print("  Consider further reducing W_FITNESS or MAX_BINDINGS.")
        elif simplicity > 0.3:
            print("\n✓ Good simplicity score achieved - cleaner Petri net expected.")
        
        # (5) Save results to output directory (INSIDE GeneticMiner folder)
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'output'
        )
        
        save_results(best_net, (overall, fitness, simplicity), output_dir)
        
        # Print full paths of saved files
        pnml_path = os.path.join(output_dir, "result_petri_net.pnml")
        json_path = os.path.join(output_dir, "result_scores.json")
        
        print(f"\nResults saved to:")
        print(f"  Petri net (PNML): {pnml_path}")
        print(f"  Scores (JSON):    {json_path}")
        print("\nGenetic process discovery completed successfully!")
        
    except Exception as e:
        # (6) Handle exceptions
        print(f"\nError during process discovery: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)