"""
Interface Module for Genetic Process Discovery.

This module provides high-level interface functions for running the genetic 
process discovery algorithm on XES event logs, converting results to Petri 
nets, and saving outputs to disk. It bridges the evolutionary algorithm 
implementation with standard process mining formats and tools.

Available Functions:
    - run_genetic_miner_from_file: Load XES file and run genetic miner
    - convert_to_petri_net: Convert CausalNet to Petri net representation
    - save_results: Save Petri net and scores to disk

Author: Senior Process Mining Engineer
Date: 2024
"""

from __future__ import annotations

import json
import os
import pandas as pd
import pm4py
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils
from genetic_miner import run_genetic_miner
from causal_net import CausalNet


def run_genetic_miner_from_file(
    xes_file_path: str,
    **kwargs
) -> tuple[CausalNet, float, float, float]:
    """
    Run the genetic process discovery algorithm on an XES event log file.
    
    Loads an event log from XES format, converts it to a pandas DataFrame,
    and executes the genetic algorithm for process discovery. All parameters
    for the genetic algorithm are passed as keyword arguments.
    
    This function provides a convenient entry point for users who have event
    logs in standard XES format and want to discover process models using
    the evolutionary algorithm.
    
    Args:
        xes_file_path: Path to the XES event log file to load and process.
            File must be valid XES format readable by pm4py.
        **kwargs: Keyword arguments passed directly to run_genetic_miner:
            - population_size (int): Number of individuals in population
            - num_generations (int): Number of generations to evolve
            - mutation_rate (float): Probability of mutation per activity
            - tournament_size (int): Size of tournament for selection
            - w_fitness (float): Weight for fitness score [0.0, 1.0]
            - w_simplicity (float): Weight for simplicity score [0.0, 1.0]
            - max_bindings_per_activity (int): Max binding sets per activity
            - random_seed (int): Random seed for reproducibility
    
    Returns:
        Tuple[CausalNet, float, float, float]: Four-element tuple containing:
            - best_causal_net: Best discovered CausalNet process model
            - overall_score: Weighted fitness + simplicity score
            - fitness_score: Raw replay fitness score
            - simplicity_score: Raw simplicity score
    
    Raises:
        FileNotFoundError: If xes_file_path does not exist.
        ValueError: If XES file is invalid or required genetic algorithm
            parameters are missing from kwargs.
    
    Example:
        >>> result = run_genetic_miner_from_file(
        ...     "data/bpi2017.xes",
        ...     population_size=50,
        ...     num_generations=100,
        ...     mutation_rate=0.2,
        ...     tournament_size=3,
        ...     w_fitness=0.7,
        ...     w_simplicity=0.3,
        ...     max_bindings_per_activity=3,
        ...     random_seed=42
        ... )
        >>> best_net, overall, fitness, simplicity = result
    """
    # Load XES file using pm4py
    event_log = pm4py.read_xes(xes_file_path)
    
    # Convert to pandas DataFrame
    df = pm4py.convert_to_dataframe(event_log)
    
    # Run genetic miner with provided parameters
    result = run_genetic_miner(df, **kwargs)
    
    return result


def convert_to_petri_net(causal_net: CausalNet) -> tuple[PetriNet, Marking, Marking]:
    """
    Convert a CausalNet process model to a Petri net representation.
    
    Transforms the causal net structure into a standard Petri net that can
    be used with pm4py's analysis and visualization tools. The conversion
    creates places based on direct follow relationships implied by the
    output bindings.
    
    Conversion Process:
    1. Create one transition per activity, labeled with activity name
    2. For each activity A and each activity B in A's output bindings,
       create a place p_A_B with arcs A→place→B
    3. Create source place connected to all start activities (empty input_bindings)
    4. Create sink place connected from all end activities (empty output_bindings)
    5. Initialize markings with one token in source (initial) and sink (final)
    
    Args:
        causal_net: CausalNet instance to convert. Contains input_bindings
            and output_bindings for each activity.
    
    Returns:
        Tuple[PetriNet, Marking, Marking]: Three-element tuple containing:
            - net: PetriNet object with transitions, places, and arcs
            - initial_marking: Marking with one token in source place
            - final_marking: Marking with one token in sink place
    
    Note:
        - Place names follow convention p_A_B for place between transitions
          A and B.
        - Source and sink places handle cases with multiple start/end activities.
        - Activities with empty input_bindings are treated as start activities.
        - Activities with empty output_bindings are treated as end activities.
        - The resulting Petri net may not be sound or free-choice; it reflects
          the structure discovered by the genetic algorithm.
    
    Example:
        >>> from causal_net import CausalNet
        >>> net = CausalNet(['A', 'B', 'C'])
        >>> net.output_bindings['A'].append(frozenset(['B']))
        >>> petri_net, init_mark, final_mark = convert_to_petri_net(net)
        >>> len(petri_net.transitions)
        3
        >>> len(petri_net.places) >= 1  # At least source and sink
        True
    """
    # Create new Petri net instance
    net = PetriNet(name="GeneticMinerResult")
    
    # Create one transition per activity, labeled with activity name
    # Store mapping from activity name to transition for arc creation
    activity_to_transition: dict[str, PetriNet.Transition] = {}
    
    for activity in causal_net.activities:
        transition = PetriNet.Transition(activity, label=activity)
        activity_to_transition[activity] = transition
        net.transitions.add(transition)
    
    # Track places created to avoid duplicates
    # Key: (source_activity, target_activity), Value: Place object
    created_places: dict[tuple[str, str], PetriNet.Place] = {}
    
    # For each activity A, for each activity B in output_bindings[A],
    # create place p_A_B with arcs A → place → B
    for activity_a in causal_net.activities:
        output_binding_sets = causal_net.output_bindings.get(activity_a, [])
        
        # Collect all successor activities from all output binding sets
        successor_activities: set[str] = set()
        for binding_set in output_binding_sets:
            successor_activities.update(binding_set)
        
        # Create place and arcs for each unique successor
        for activity_b in successor_activities:
            place_name = f"p_{activity_a}_{activity_b}"
            place_key = (activity_a, activity_b)
            
            # Only create place if not already created
            if place_key not in created_places:
                place = PetriNet.Place(place_name)
                created_places[place_key] = place
                net.places.add(place)
                
                # Add arc from transition A to place
                petri_utils.add_arc_from_to(
                    activity_to_transition[activity_a],
                    place,
                    net
                )
            
            # Get the place (either newly created or existing)
            place = created_places[place_key]
            
            # Add arc from place to transition B
            petri_utils.add_arc_from_to(
                place,
                activity_to_transition[activity_b],
                net
            )
    
    # Identify start activities (empty input_bindings list)
    start_activities: list[str] = []
    for activity in causal_net.activities:
        input_binding_sets = causal_net.input_bindings.get(activity, [])
        if len(input_binding_sets) == 0:
            start_activities.append(activity)
    
    # Create single source place and connect to all start activities
    source_place = PetriNet.Place("source")
    net.places.add(source_place)
    
    for activity in start_activities:
        petri_utils.add_arc_from_to(
            source_place,
            activity_to_transition[activity],
            net
        )
    
    # Identify end activities (empty output_bindings list)
    end_activities: list[str] = []
    for activity in causal_net.activities:
        output_binding_sets = causal_net.output_bindings.get(activity, [])
        if len(output_binding_sets) == 0:
            end_activities.append(activity)
    
    # Create single sink place and connect from all end activities
    sink_place = PetriNet.Place("sink")
    net.places.add(sink_place)
    
    for activity in end_activities:
        petri_utils.add_arc_from_to(
            activity_to_transition[activity],
            sink_place,
            net
        )
    
    # Create initial marking with one token in source place
    initial_marking = Marking()
    initial_marking[source_place] = 1
    
    # Create final marking with one token in sink place
    final_marking = Marking()
    final_marking[sink_place] = 1
    
    return net, initial_marking, final_marking


def save_results(
    causal_net: CausalNet,
    scores: tuple[float, float, float],
    output_dir: str
) -> None:
    """
    Save genetic miner results to disk in standard formats.
    
    Saves the discovered process model as a Petri net in PNML format and
    the evaluation scores plus causal net structure as JSON. Creates the
    output directory if it doesn't exist.
    
    Output Files:
    1. result_petri_net.pnml: Petri net in PNML format for visualization
       and analysis in process mining tools.
    2. result_scores.json: JSON file containing:
       - overall_score: Weighted fitness + simplicity
       - fitness_score: Raw replay fitness
       - simplicity_score: Raw simplicity
       - activities: List of activity names
       - input_bindings: Serialized input binding structure
       - output_bindings: Serialized output binding structure
    
    Args:
        causal_net: CausalNet instance representing the discovered process
            model to save.
        scores: Three-element tuple containing (overall_score, fitness_score,
            simplicity_score) from the final evaluation.
        output_dir: Directory path where results will be saved. Created if
            it doesn't exist.
    
    Raises:
        OSError: If output_dir cannot be created or files cannot be written.
        ValueError: If scores tuple doesn't contain exactly 3 float values.
    
    Note:
        - PNML format is widely supported by process mining tools including
          ProM, pm4py, and various Petri net analyzers.
        - JSON format allows easy inspection and programmatic access to
          results without requiring specialized process mining software.
        - Binding sets (frozensets) are serialized as lists in JSON since
          frozenset is not JSON-serializable.
    
    Example:
        >>> from causal_net import CausalNet
        >>> net = CausalNet(['A', 'B', 'C'])
        >>> scores = (0.75, 0.80, 0.65)
        >>> save_results(net, scores, "output/results/")
        >>> # Creates output/results/result_petri_net.pnml
        >>> # Creates output/results/result_scores.json
    """
    # Validate scores tuple
    if len(scores) != 3:
        raise ValueError(
            f"scores must be a 3-tuple (overall, fitness, simplicity), "
            f"got {len(scores)} elements"
        )
    
    overall_score, fitness_score, simplicity_score = scores
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Step (i): Convert to Petri net and save as PNML
    petri_net, initial_marking, final_marking = convert_to_petri_net(causal_net)
    
    pnml_path = os.path.join(output_dir, "result_petri_net.pnml")
    pm4py.write_pnml(petri_net, initial_marking, final_marking, pnml_path)
    
    # Step (ii): Serialize scores and causal net structure to JSON
    
    # Helper function to convert frozensets to lists for JSON serialization
    def serialize_bindings(bindings_dict: dict) -> dict:
        """Convert binding dictionaries with frozensets to JSON-serializable format."""
        serialized = {}
        for activity, binding_list in bindings_dict.items():
            # Each binding_list is List[FrozenSet[str]]
            # Convert each frozenset to sorted list for consistent serialization
            serialized[activity] = [
                sorted(list(binding_set)) for binding_set in binding_list
            ]
        return serialized
    
    # Build result dictionary
    result_data = {
        "overall_score": overall_score,
        "fitness_score": fitness_score,
        "simplicity_score": simplicity_score,
        "activities": causal_net.activities,
        "input_bindings": serialize_bindings(causal_net.input_bindings),
        "output_bindings": serialize_bindings(causal_net.output_bindings)
    }
    
    # Write JSON file
    json_path = os.path.join(output_dir, "result_scores.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(result_data, json_file, indent=2)