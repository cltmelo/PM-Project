"""
Genetic Operators for Evolutionary Process Discovery.

This module provides genetic operators (mutation, crossover, etc.) for 
evolving CausalNet instances in the evolutionary process discovery 
algorithm for BPI Challenge 2017 dataset analysis.

Available Operators:
    - mutate: Performs random mutations on a CausalNet's binding structures
      to introduce variation in the evolutionary population.
    
    - crossover: Combines binding structures from two parent CausalNet instances
      to create a child. For each activity, input and output bindings are 
      independently inherited from either parent with equal probability.
    
    - tournament_selection: Selects an individual from a population using 
      tournament selection. Randomly samples a subset of individuals and 
      returns the one with the highest fitness score.

Author: Senior Process Mining Engineer
Date: 2024
"""

from __future__ import annotations

import random
from typing import Set, Tuple, List, FrozenSet
from causal_net import CausalNet


def mutate(
    causal_net: CausalNet,
    directly_follows_pairs: Set[Tuple[str, str]],
    mutation_rate: float
) -> CausalNet:
    """
    Mutate a CausalNet individual by randomly modifying its binding structures.
    
    Creates a copy of the input causal net and applies random mutations to
    the input and/or output binding sets of activities based on the mutation
    rate. This operator introduces variation into the evolutionary population,
    allowing the algorithm to explore new regions of the search space.
    
    For each activity in the causal net, with probability equal to mutation_rate,
    one of three mutation operations is randomly selected and applied to either
    the input or output binding sets:
    
    (a) Add: Insert a new random binding set (non-empty frozenset of valid
        predecessor/successor activities)
    (b) Remove: Delete a randomly chosen existing binding set (only if more
        than one binding set exists)
    (c) Replace: Substitute a randomly chosen binding set with a different
        random frozenset
    
    Args:
        causal_net: CausalNet instance to mutate. This instance is not modified;
            a deep copy is created and returned with mutations applied.
        directly_follows_pairs: Set of (predecessor, successor) tuples derived
            from the event log. Each tuple represents a direct follow relationship
            observed in at least one case trace. Used to determine valid activities
            for creating new binding sets.
        mutation_rate: Probability between 0.0 and 1.0 that an activity will
            undergo mutation. Higher values increase exploration but may disrupt
            good solutions; lower values preserve existing structure.
    
    Returns:
        CausalNet: A new CausalNet instance with mutations applied. The original
            causal_net remains unmodified. Returned instance is a deep copy with
            independent binding structures.
    
    Raises:
        ValueError: If mutation_rate is outside the valid range [0.0, 1.0].
    
    Note:
        - Valid predecessor activities for an activity X are those Y where
          (Y, X) exists in directly_follows_pairs.
        - Valid successor activities for an activity X are those Y where
          (X, Y) exists in directly_follows_pairs.
        - Binding sets are always non-empty frozensets.
        - If an activity has no valid predecessors/successors, mutation
          operations that would add bindings are skipped for that direction.
        - The remove operation requires at least 2 binding sets to proceed
          (to avoid leaving an activity with no bindings after removal).
    
    Example:
        >>> from causal_net import CausalNet
        >>> follows = {('A', 'B'), ('B', 'C'), ('A', 'C')}
        >>> net = CausalNet(['A', 'B', 'C'])
        >>> net.input_bindings['B'].append(frozenset(['A']))
        >>> mutated = mutate(net, follows, mutation_rate=0.5)
        >>> mutated is not net  # Different instance
        True
    """
    # Validate mutation rate is in valid range
    if not (0.0 <= mutation_rate <= 1.0):
        raise ValueError(
            f"mutation_rate must be in range [0.0, 1.0], got {mutation_rate}"
        )
    
    # Create a deep copy of the causal net to avoid modifying the original
    mutated_net = causal_net.copy()
    
    # Pre-compute valid predecessors and successors for each activity
    # from the directly-follows pairs
    valid_predecessors, valid_successors = _extract_valid_activities(
        directly_follows_pairs,
        mutated_net.activities
    )
    
    # Iterate through each activity and potentially apply mutation
    for activity in mutated_net.activities:
        # Decide whether to mutate this activity based on mutation rate
        if random.random() >= mutation_rate:
            continue  # Skip this activity
        
        # Randomly choose which binding type to mutate (input or output)
        # 0 = input bindings, 1 = output bindings
        binding_type = random.choice([0, 1])
        
        if binding_type == 0:
            # Mutate input bindings (predecessors)
            _mutate_bindings(
                mutated_net,
                activity,
                valid_predecessors.get(activity, set()),
                is_input=True
            )
        else:
            # Mutate output bindings (successors)
            _mutate_bindings(
                mutated_net,
                activity,
                valid_successors.get(activity, set()),
                is_input=False
            )
    
    return mutated_net


def crossover(
    parent_a: CausalNet,
    parent_b: CausalNet,
    activities: List[str]
) -> CausalNet:
    """
    Perform crossover between two parent CausalNet instances to create a child.
    
    Combines binding structures from two parents by independently selecting
    input and output bindings for each activity from either parent with equal
    probability (50/50). This operator enables recombination of successful
    structural patterns from different individuals in the population.
    
    For each activity in the activities list:
    1. A random draw determines whether input bindings come from parent_a or
       parent_b (equal probability)
    2. An independent random draw determines whether output bindings come from
       parent_a or parent_b (equal probability)
    3. Selected binding lists are shallow copied to ensure child mutations
       do not affect parent structures
    
    Args:
        parent_a: First parent CausalNet instance. Not modified by this function.
        parent_b: Second parent CausalNet instance. Not modified by this function.
        activities: List of activity names to include in the child CausalNet.
            Typically matches the activities from both parents.
    
    Returns:
        CausalNet: A new child CausalNet instance with binding structures
            inherited from both parents. Parent instances remain unmodified.
    
    Raises:
        ValueError: If activities list is empty.
    
    Note:
        - Input and output binding inheritance decisions are made independently
          for each activity, allowing fine-grained recombination.
        - Shallow copies of binding lists are created (new list objects containing
          the same frozenset references), ensuring child mutations don't affect
          parents while avoiding unnecessary deep copying of immutable frozensets.
        - Both parents should have the same activities for meaningful crossover,
          though this function accepts any activities list.
    
    Example:
        >>> from causal_net import CausalNet
        >>> parent_a = CausalNet(['A', 'B', 'C'])
        >>> parent_b = CausalNet(['A', 'B', 'C'])
        >>> parent_a.input_bindings['B'].append(frozenset(['A']))
        >>> parent_b.output_bindings['A'].append(frozenset(['B']))
        >>> child = crossover(parent_a, parent_b, ['A', 'B', 'C'])
        >>> child is not parent_a and child is not parent_b
        True
        >>> len(child.activities)
        3
    """
    # Validate activities list is not empty
    if not activities:
        raise ValueError("Activities list cannot be empty")
    
    # Create new CausalNet instance for the child
    child = CausalNet(activities.copy())
    
    # For each activity, independently inherit input and output bindings
    for activity in activities:
        # Independent random draw for input bindings (50/50 chance)
        if random.random() < 0.5:
            # Inherit input bindings from parent_a (shallow copy)
            child.input_bindings[activity] = parent_a.input_bindings.get(activity, []).copy()
        else:
            # Inherit input bindings from parent_b (shallow copy)
            child.input_bindings[activity] = parent_b.input_bindings.get(activity, []).copy()
        
        # Independent random draw for output bindings (50/50 chance)
        if random.random() < 0.5:
            # Inherit output bindings from parent_a (shallow copy)
            child.output_bindings[activity] = parent_a.output_bindings.get(activity, []).copy()
        else:
            # Inherit output bindings from parent_b (shallow copy)
            child.output_bindings[activity] = parent_b.output_bindings.get(activity, []).copy()
    
    return child


def tournament_selection(
    population_with_scores: List[Tuple[CausalNet, float]],
    tournament_size: int
) -> CausalNet:
    """
    Select an individual from a population using tournament selection.
    
    Randomly samples a subset of individuals from the population and returns
    the one with the highest fitness score. This selection method provides
    selective pressure while maintaining diversity in the evolutionary population.
    
    Tournament selection works by:
    1. Randomly sampling tournament_size individuals from the population
    2. Comparing their scores
    3. Returning the individual with the highest score
    
    This method balances exploration and exploitation: larger tournaments
    increase selection pressure (favoring high-scoring individuals), while
    smaller tournaments maintain more diversity.
    
    Args:
        population_with_scores: List of (CausalNet, score) tuples representing
            the current population. Each tuple contains a CausalNet instance
            and its corresponding fitness score (float).
        tournament_size: Number of individuals to sample for the tournament.
            Must be at least 1. If greater than population length, silently
            clamped to len(population_with_scores).
    
    Returns:
        CausalNet: The CausalNet instance with the highest score among the
            sampled tournament participants.
    
    Raises:
        ValueError: If population_with_scores is empty or if tournament_size
            is less than 1.
    
    Note:
        - Sampling is done without replacement, so all tournament participants
          are distinct individuals.
        - If multiple individuals have the same highest score, one is chosen
          arbitrarily (typically the first encountered during max evaluation).
        - Tournament size controls selection pressure:
          - Small tournaments (e.g., 2-3): More diversity, weaker pressure
          - Large tournaments: Stronger pressure toward high-scoring individuals
    
    Example:
        >>> from causal_net import CausalNet
        >>> pop = [
        ...     (CausalNet(['A', 'B']), 0.6),
        ...     (CausalNet(['A', 'B']), 0.8),
        ...     (CausalNet(['A', 'B']), 0.5)
        ... ]
        >>> winner = tournament_selection(pop, tournament_size=2)
        >>> winner is not None
        True
    """
    # Validate population is not empty
    if not population_with_scores:
        raise ValueError("Population cannot be empty")
    
    # Validate tournament_size is at least 1
    if tournament_size < 1:
        raise ValueError(
            f"tournament_size must be at least 1, got {tournament_size}"
        )
    
    # Clamp tournament_size to population length if necessary
    # This prevents ValueError from random.sample when k > n
    effective_tournament_size = min(tournament_size, len(population_with_scores))
    
    # Randomly sample tournament_size individuals without replacement
    tournament_participants = random.sample(
        population_with_scores,
        effective_tournament_size
    )
    
    # Find and return the individual with the highest score
    # Each tuple is (CausalNet, score), so we use key=lambda x: x[1]
    winner, __ = max(tournament_participants, key=lambda x: x[1])
    
    return winner


def _extract_valid_activities(
    directly_follows_pairs: Set[Tuple[str, str]],
    activities: List[str]
) -> Tuple[dict, dict]:
    """
    Extract valid predecessor and successor activities for each activity.
    
    Processes the directly-follows pairs to build mappings from each activity
    to its valid predecessors and successors. These mappings constrain mutation
    operations to only use activities that have observed direct relationships
    in the event log.
    
    Args:
        directly_follows_pairs: Set of (predecessor, successor) tuples from
            the event log analysis.
        activities: List of all activity names in the causal net.
    
    Returns:
        Tuple containing two dictionaries:
            - predecessors: Mapping from activity to set of valid predecessor
              activities (those Y where (Y, activity) exists in pairs)
            - successors: Mapping from activity to set of valid successor
              activities (those Y where (activity, Y) exists in pairs)
    
    Example:
        >>> pairs = {('A', 'B'), ('B', 'C'), ('A', 'C')}
        >>> preds, succs = _extract_valid_activities(pairs, ['A', 'B', 'C'])
        >>> preds['B']
        {'A'}
        >>> succs['A']
        {'B', 'C'}
    """
    # Convert activities list to set for O(1) membership checks
    activities_set = set(activities)
    
    predecessors: dict = {activity: set() for activity in activities}
    successors: dict = {activity: set() for activity in activities}
    
    for pred, succ in directly_follows_pairs:
        # Only consider activities that are in our activity list
        if pred in activities_set and succ in activities_set:
            successors[pred].add(succ)
            predecessors[succ].add(pred)
    
    return predecessors, successors


def _mutate_bindings(
    causal_net: CausalNet,
    activity: str,
    valid_activities: Set[str],
    is_input: bool
) -> None:
    """
    Apply a mutation operation to the binding sets of an activity.
    
    Randomly selects and executes one of three mutation operations:
    (a) Add a new binding set, (b) Remove an existing binding set, or
    (c) Replace an existing binding set with a new one.
    
    Args:
        causal_net: CausalNet instance to mutate (modified in-place).
        activity: Name of the activity whose bindings will be mutated.
        valid_activities: Set of valid activities to use when creating
            new binding sets (predecessors for input, successors for output).
        is_input: If True, mutate input bindings; if False, mutate output
            bindings.
    
    Note:
        This function modifies the causal_net in-place. No return value.
        If valid_activities is empty, add and replace operations are skipped.
        Remove operation requires at least 2 existing binding sets.
    """
    # Get the binding list to mutate
    if is_input:
        bindings_list = causal_net.input_bindings[activity]
    else:
        bindings_list = causal_net.output_bindings[activity]
    
    # Determine available mutation operations based on current state
    available_ops = []
    
    # Operation (a): Add - always available if there are valid activities
    if valid_activities:
        available_ops.append('add')
    
    # Operation (b): Remove - only if more than one binding exists
    if len(bindings_list) > 1:
        available_ops.append('remove')
    
    # Operation (c): Replace - only if at least one binding exists and valid activities available
    if len(bindings_list) > 0 and valid_activities:
        available_ops.append('replace')
    
    # If no operations are available, skip mutation for this activity
    if not available_ops:
        return
    
    # Randomly select which mutation operation to perform
    operation = random.choice(available_ops)
    
    # Execute the selected mutation operation
    if operation == 'add':
        _add_binding(bindings_list, valid_activities)
    elif operation == 'remove':
        _remove_binding(bindings_list)
    elif operation == 'replace':
        _replace_binding(bindings_list, valid_activities)


def _add_binding(
    bindings_list: List[FrozenSet[str]],
    valid_activities: Set[str]
) -> None:
    """
    Add a new random binding set to the bindings list.
    
    Creates a new non-empty frozenset by randomly sampling from the valid
    activities and appends it to the bindings list.
    
    Args:
        bindings_list: List of frozenset bindings to modify (modified in-place).
        valid_activities: Set of activity names to sample from for the new
            binding set.
    
    Note:
        This function modifies bindings_list in-place. No return value.
        The new binding set size is randomly chosen between 1 and the
        number of available valid activities.
    """
    # Randomly select size for the new binding set (at least 1)
    binding_size = random.randint(1, len(valid_activities))
    
    # Randomly sample activities for the new binding set
    sampled_activities = random.sample(list(valid_activities), binding_size)
    
    # Create and append the new binding set
    new_binding = frozenset(sampled_activities)
    bindings_list.append(new_binding)


def _remove_binding(bindings_list: List[FrozenSet[str]]) -> None:
    """
    Remove a randomly chosen binding set from the bindings list.
    
    Selects a random index from the bindings list and removes the binding
    set at that position.
    
    Args:
        bindings_list: List of frozenset bindings to modify (modified in-place).
    
    Note:
        This function modifies bindings_list in-place. No return value.
        Should only be called when len(bindings_list) > 1 to ensure
        at least one binding remains after removal.
    """
    # Randomly select which binding to remove
    remove_index = random.randint(0, len(bindings_list) - 1)
    
    # Remove the selected binding
    bindings_list.pop(remove_index)


def _replace_binding(
    bindings_list: List[FrozenSet[str]],
    valid_activities: Set[str]
) -> None:
    """
    Replace a randomly chosen binding set with a new random binding set.
    
    Selects a random existing binding set and substitutes it with a newly
    generated random frozenset sampled from the valid activities.
    
    Args:
        bindings_list: List of frozenset bindings to modify (modified in-place).
        valid_activities: Set of activity names to sample from for the new
            binding set.
    
    Note:
        This function modifies bindings_list in-place. No return value.
        The new binding set may coincidentally be identical to the old one,
        though this is unlikely with reasonable numbers of valid activities.
    """
    # Randomly select which binding to replace
    replace_index = random.randint(0, len(bindings_list) - 1)
    
    # Randomly select size for the new binding set (at least 1)
    binding_size = random.randint(1, len(valid_activities))
    
    # Randomly sample activities for the new binding set
    sampled_activities = random.sample(list(valid_activities), binding_size)
    
    # Create the new binding set and replace the old one
    new_binding = frozenset(sampled_activities)
    bindings_list[replace_index] = new_binding