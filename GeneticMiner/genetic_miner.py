"""
Genetic Algorithm for Process Discovery.

This module implements the main genetic algorithm driver for evolutionary 
process discovery applied to the BPI Challenge 2017 dataset. It orchestrates 
the population-based search process that evolves CausalNet process models 
through selection, crossover, and mutation operators.

The algorithm balances fitness (trace replay capability) and simplicity 
(structural complexity) through multi-objective optimization guided by 
user-specified weights.

Author: Senior Process Mining Engineer
Date: 2024
"""

from __future__ import annotations

import random
import pandas as pd
from causal_net import CausalNet
from initialization import initialize_individual
from metrics import evaluate_individual
from operators import mutate, crossover, tournament_selection


def run_genetic_miner(
    df: pd.DataFrame,
    population_size: int,
    num_generations: int,
    mutation_rate: float,
    tournament_size: int,
    w_fitness: float,
    w_simplicity: float,
    max_bindings_per_activity: int,
    random_seed: int
) -> tuple[CausalNet, float, float, float]:
    """
    Run the genetic algorithm for process discovery on an event log.
    
    Executes an evolutionary process discovery algorithm that maintains a 
    population of CausalNet process models and evolves them over multiple 
    generations using genetic operators (selection, crossover, mutation). 
    The algorithm balances fitness and simplicity through weighted multi-objective 
    optimization.
    
    Algorithm Overview:
    1. Initialize random seed for reproducibility
    2. Extract activities and directly-follows relationships from event log
    3. Create initial population of random CausalNet individuals
    4. For each generation:
       - Evaluate all individuals using weighted fitness + simplicity
       - Preserve best individual unchanged (elitism)
       - Generate new individuals through tournament selection, crossover, mutation
       - Track and print generation statistics
    5. Return best individual from final population
    
    Args:
        df: Pandas DataFrame representing the event log with required columns:
            - "case:concept:name": Case identifier for grouping events
            - "concept:name": Activity name for each event
            Events should be in chronological order within each case.
        population_size: Number of individuals to maintain in the population.
            Must be at least 2 to allow meaningful selection and crossover.
        num_generations: Number of generations to evolve the population.
            More generations allow more exploration but increase computation time.
        mutation_rate: Probability between 0.0 and 1.0 that an activity undergoes
            mutation during the mutate operator. Typical values: 0.1-0.3.
        tournament_size: Number of individuals sampled for tournament selection.
            Controls selection pressure. Typical values: 2-5.
        w_fitness: Weight for replay fitness in [0.0, 1.0]. Higher values prioritize
            accurate trace replay. Must satisfy w_fitness + w_simplicity = 1.0.
        w_simplicity: Weight for simplicity in [0.0, 1.0]. Higher values prioritize
            simpler process models. Must satisfy w_fitness + w_simplicity = 1.0.
        max_bindings_per_activity: Maximum number of binding sets per activity
            when initializing individuals. Controls initial model complexity.
            Typical values: 2-5.
        random_seed: Integer seed for random number generator to ensure
            reproducible results across runs.
    
    Returns:
        Tuple[CausalNet, float, float, float]: Four-element tuple containing:
            - best_causal_net: Best CausalNet instance from final population
            - overall_score: Weighted fitness + simplicity score of best individual
            - fitness_score: Raw replay fitness score of best individual
            - simplicity_score: Raw simplicity score of best individual
    
    Raises:
        ValueError: If population_size < 2, if weights don't sum to 1.0,
            if required DataFrame columns are missing, or if event log is empty.
    
    Note:
        - Elitism preserves the best individual unchanged across generations,
          ensuring monotonic improvement of best solution quality.
        - Directly-follows pairs are computed once at the start and reused
          throughout all generations for mutation operations.
        - Selection uses (CausalNet, overall_score) tuples; other scores are
          tracked but not used for selection decisions.
        - Progress is printed each generation for monitoring convergence.
    
    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'case:concept:name': [1, 1, 1, 2, 2, 2],
        ...     'concept:name': ['A', 'B', 'C', 'A', 'B', 'D']
        ... })
        >>> result = run_genetic_miner(
        ...     df,
        ...     population_size=10,
        ...     num_generations=50,
        ...     mutation_rate=0.2,
        ...     tournament_size=3,
        ...     w_fitness=0.7,
        ...     w_simplicity=0.3,
        ...     max_bindings_per_activity=3,
        ...     random_seed=42
        ... )
        >>> best_net, overall, fitness, simplicity = result
        >>> isinstance(best_net, CausalNet)
        True
    """
    # Step 1: Set random seed for reproducibility
    random.seed(random_seed)
    
    # Step 2: Extract unique activities and compute directly-follows pairs
    
    # Get sorted list of unique activity names from concept:name column
    activities = sorted(df["concept:name"].unique().tolist())
    
    if not activities:
        raise ValueError("Event log contains no activities")
    
    if population_size < 2:
        raise ValueError(f"population_size must be at least 2, got {population_size}")
    
    # Compute directly-follows pairs by grouping by case and iterating consecutive pairs
    directly_follows_pairs: set[tuple[str, str]] = set()
    
    grouped = df.groupby("case:concept:name", sort=False)
    
    for case_id, case_df in grouped:
        # Get activity sequence for this case in original row order
        case_activities = case_df["concept:name"].tolist()
        
        # Extract consecutive pairs within this case
        for i in range(len(case_activities) - 1):
            predecessor = case_activities[i]
            successor = case_activities[i + 1]
            directly_follows_pairs.add((predecessor, successor))
    
    # Step 3: Initialize population of CausalNet individuals
    
    population: list[CausalNet] = []
    
    for _ in range(population_size):
        individual = initialize_individual(
            df,
            activities,
            max_bindings_per_activity
        )
        population.append(individual)
    
    # Step 4: Evolution loop for each generation
    
    for generation in range(1, num_generations + 1):
        # (i) Evaluate every individual in the population
        
        evaluated_population: list[tuple[CausalNet, float, float, float]] = []
        
        for individual in population:
            overall_score, fitness_score, simplicity_score = evaluate_individual(
                individual,
                df,
                w_fitness,
                w_simplicity
            )
            evaluated_population.append((
                individual,
                overall_score,
                fitness_score,
                simplicity_score
            ))
        
        # (ii) Identify best individual and carry it over (elitism of size 1)
        
        best_evaluated = max(evaluated_population, key=lambda x: x[1])
        best_individual = best_evaluated[0]
        best_overall_score = best_evaluated[1]
        
        # Start next generation with elite individual
        next_generation: list[CausalNet] = [best_individual.copy()]
        
        # (iii) Fill remaining slots through selection, crossover, and mutation
        
        # Create list of (CausalNet, overall_score) tuples for tournament selection
        selection_pool: list[tuple[CausalNet, float]] = [
            (individual, overall_score)
            for individual, overall_score, _, _ in evaluated_population
        ]
        
        # Generate population_size - 1 new individuals
        slots_to_fill = population_size - 1
        
        for _ in range(slots_to_fill):
            # Select two parents via tournament selection
            parent_a = tournament_selection(selection_pool, tournament_size)
            parent_b = tournament_selection(selection_pool, tournament_size)
            
            # Apply crossover to produce offspring
            offspring = crossover(parent_a, parent_b, activities)
            
            # Apply mutation to offspring
            mutated_offspring = mutate(
                offspring,
                directly_follows_pairs,
                mutation_rate
            )
            
            # Add to next generation
            next_generation.append(mutated_offspring)
        
        # Update population for next generation
        population = next_generation
        
        # (iv) Print generation number and best overall_score
        print(f"Generation {generation}: Best overall_score = {best_overall_score:.6f}")
    
    # Step 5: Evaluate final population and return best individual
    
    final_evaluated: list[tuple[CausalNet, float, float, float]] = []
    
    for individual in population:
        overall_score, fitness_score, simplicity_score = evaluate_individual(
            individual,
            df,
            w_fitness,
            w_simplicity
        )
        final_evaluated.append((
            individual,
            overall_score,
            fitness_score,
            simplicity_score
        ))
    
    # Identify best individual from final population
    best_final = max(final_evaluated, key=lambda x: x[1])
    best_causal_net = best_final[0]
    best_overall = best_final[1]
    best_fitness = best_final[2]
    best_simplicity = best_final[3]
    
    return best_causal_net, best_overall, best_fitness, best_simplicity