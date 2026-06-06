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
    random_seed: int,
    elite_count: int = 1,
    patience: int = None,
    min_improvement: float = 0.001
) -> tuple[CausalNet, float, float, float, int]:
    """
    Run the genetic algorithm for process discovery on an event log.
    
    Executes an evolutionary process discovery algorithm that maintains a 
    population of CausalNet process models and evolves them over multiple 
    generations using genetic operators (selection, crossover, mutation). 
    The algorithm balances fitness and simplicity through weighted multi-objective 
    optimization.
    
    Args:
        df: Pandas DataFrame representing the event log with required columns:
            - "case:concept:name": Case identifier for grouping events
            - "concept:name": Activity name for each event
        population_size: Number of individuals to maintain in the population.
        num_generations: Number of generations to evolve the population.
        mutation_rate: Probability between 0.0 and 1.0 that an activity undergoes
            mutation during the mutate operator.
        tournament_size: Number of individuals sampled for tournament selection.
        w_fitness: Weight for replay fitness in [0.0, 1.0].
        w_simplicity: Weight for simplicity in [0.0, 1.0].
        max_bindings_per_activity: Maximum number of binding sets per activity
            when initializing individuals.
        random_seed: Integer seed for random number generator.
        elite_count: Number of best individuals to preserve unchanged (default 1).
        patience: Number of generations without improvement before early stop.
        min_improvement: Minimum score improvement to reset patience counter.
    
    Returns:
        Tuple[CausalNet, float, float, float, int]: Five-element tuple containing:
            - best_causal_net: Best CausalNet instance from final population
            - overall_score: Weighted fitness + simplicity score
            - fitness_score: Raw replay fitness score
            - simplicity_score: Raw simplicity score
            - actual_generations: Number of generations actually executed
    """
    # Step 1: Set random seed for reproducibility
    random.seed(random_seed)
    
    # Step 2: Extract unique activities and compute directly-follows pairs
    activities = sorted(df["concept:name"].unique().tolist())
    
    if not activities:
        raise ValueError("Event log contains no activities")
    
    if population_size < 2:
        raise ValueError(f"population_size must be at least 2, got {population_size}")
    
    if elite_count < 1 or elite_count >= population_size:
        raise ValueError(f"elite_count must be between 1 and {population_size - 1}")
    
    # Compute directly-follows pairs
    directly_follows_pairs: set[tuple[str, str]] = set()
    grouped = df.groupby("case:concept:name", sort=False)
    
    for case_id, case_df in grouped:
        case_activities = case_df["concept:name"].tolist()
        for i in range(len(case_activities) - 1):
            predecessor = case_activities[i]
            successor = case_activities[i + 1]
            directly_follows_pairs.add((predecessor, successor))
    
    # Step 3: Initialize population
    population: list[CausalNet] = []
    for _ in range(population_size):
        individual = initialize_individual(df, activities, max_bindings_per_activity)
        population.append(individual)
    
    # Early stopping tracking
    best_score_history: list[float] = []
    no_improvement_count = 0
    actual_generations = 0
    
    # Step 4: Evolution loop
    for generation in range(1, num_generations + 1):
        actual_generations = generation
        
        # (i) Evaluate all individuals
        evaluated_population: list[tuple[CausalNet, float, float, float]] = []
        for individual in population:
            overall_score, fitness_score, simplicity_score = evaluate_individual(
                individual, df, w_fitness, w_simplicity
            )
            evaluated_population.append((individual, overall_score, fitness_score, simplicity_score))
        
        # Sort by overall_score descending
        evaluated_population.sort(key=lambda x: x[1], reverse=True)
        
        best_overall_score = evaluated_population[0][1]
        
        # Early stopping check
        if patience is not None and len(best_score_history) > 0:
            previous_best = best_score_history[-1]
            improvement = best_overall_score - previous_best
            
            if improvement >= min_improvement:
                no_improvement_count = 0
                print(f"Generation {generation}: Best overall_score = {best_overall_score:.6f} (+{improvement:.6f})")
            else:
                no_improvement_count += 1
                print(f"Generation {generation}: Best overall_score = {best_overall_score:.6f} (no improvement: {no_improvement_count}/{patience})")
                
                if no_improvement_count >= patience:
                    print(f"\nEarly stopping triggered at generation {generation} (no improvement for {patience} generations)")
                    break
        else:
            print(f"Generation {generation}: Best overall_score = {best_overall_score:.6f}")
        
        best_score_history.append(best_overall_score)
        
        # (ii) Elitism: preserve top elite_count individuals
        next_generation: list[CausalNet] = [
            individual.copy() for individual, _, _, _ in evaluated_population[:elite_count]
        ]
        
        # Selection pool for tournament
        selection_pool: list[tuple[CausalNet, float]] = [
            (individual, overall_score)
            for individual, overall_score, _, _ in evaluated_population
        ]
        
        # (iii) Fill remaining slots through selection, crossover, and mutation
        slots_to_fill = population_size - elite_count
        for _ in range(slots_to_fill):
            parent_a = tournament_selection(selection_pool, tournament_size)
            parent_b = tournament_selection(selection_pool, tournament_size)
            offspring = crossover(parent_a, parent_b, activities)
            mutated_offspring = mutate(offspring, directly_follows_pairs, mutation_rate)
            next_generation.append(mutated_offspring)
        
        population = next_generation
    
    # Step 5: Evaluate final population and return best individual
    final_evaluated: list[tuple[CausalNet, float, float, float]] = []
    for individual in population:
        overall_score, fitness_score, simplicity_score = evaluate_individual(
            individual, df, w_fitness, w_simplicity
        )
        final_evaluated.append((individual, overall_score, fitness_score, simplicity_score))
    
    best_final = max(final_evaluated, key=lambda x: x[1])
    
    return (
        best_final[0],
        best_final[1],
        best_final[2],
        best_final[3],
        actual_generations
    )