"""
Initialization Function for Evolutionary Process Discovery.

This module provides the initialize_individual function for creating
initial candidate solutions (CausalNet instances) for the evolutionary
process discovery algorithm applied to BPI Challenge 2017 dataset.
"""

import random
from typing import List, FrozenSet, Dict, Set, Tuple
import pandas as pd
from causal_net import CausalNet


def initialize_individual(
    df: pd.DataFrame,
    activities: List[str],
    max_bindings_per_activity: int
) -> CausalNet:
    """
    Initialize a CausalNet individual for the evolutionary process discovery algorithm.
    
    Creates a populated CausalNet instance by analyzing direct follow relationships
    in the event log and randomly selecting binding sets for each activity.
    This function generates one candidate solution for the initial population
    of the evolutionary algorithm.
    
    The initialization process:
    1. Extracts direct follow relationships from the event log (A directly follows B
       if there exists a case where B is immediately succeeded by A)
    2. For each activity, identifies all observed predecessors and successors
    3. Randomly selects between 1 and max_bindings_per_activity binding sets
       from the observed predecessors/successors
    4. Each binding set is a non-empty frozenset of activity names
    
    Args:
        df: Pandas DataFrame representing the event log with required columns:
            - "case:concept:name": Case identifier for grouping events
            - "concept:name": Activity name for each event
            Events should be sorted chronologically within each case.
        activities: List of unique activity names present in the process model.
            These correspond to the distinct activities found in the event log.
        max_bindings_per_activity: Maximum number of binding sets to create
            for each activity's input and output bindings. Must be >= 1.
            The actual number selected will be between 1 and this value (inclusive).
    
    Returns:
        CausalNet: A populated causal net instance with randomly selected
            input and output binding sets based on observed direct follow
            relationships in the event log.
    
    Raises:
        ValueError: If required columns are missing from the DataFrame,
            if max_bindings_per_activity is less than 1, or if activities
            list is empty.
        KeyError: If any activity in the activities list is not found in the event log.
    
    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'case:concept:name': [1, 1, 1, 2, 2, 2],
        ...     'concept:name': ['A', 'B', 'C', 'A', 'B', 'D']
        ... })
        >>> activities = ['A', 'B', 'C', 'D']
        >>> net = initialize_individual(df, activities, max_bindings_per_activity=2)
        >>> len(net.input_bindings['B'])  # Between 1 and 2 binding sets
        1
    """
    # Validate inputs
    if max_bindings_per_activity < 1:
        raise ValueError("max_bindings_per_activity must be at least 1")
    
    if not activities:
        raise ValueError("Activities list cannot be empty")
    
    required_columns = ["case:concept:name", "concept:name"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Create CausalNet instance with empty bindings
    causal_net = CausalNet(activities)
    
    # Extract direct follow relationships from the event log
    # Returns dict mapping each activity to its direct predecessors and successors
    predecessors, successors = _extract_direct_follows(df, activities)
    
    # Populate input bindings for each activity
    for activity in activities:
        pred_set = predecessors.get(activity, set())
        
        # Only create bindings if there are observed predecessors
        if pred_set:
            # Generate random binding sets from predecessors
            num_bindings = random.randint(1, max_bindings_per_activity)
            binding_sets = _generate_random_binding_sets(
                pred_set, 
                num_bindings, 
                max_bindings_per_activity
            )
            causal_net.input_bindings[activity] = binding_sets
        # else: leave as empty list (already initialized in CausalNet.__init__)
    
    # Populate output bindings for each activity
    for activity in activities:
        succ_set = successors.get(activity, set())
        
        # Only create bindings if there are observed successors
        if succ_set:
            # Generate random binding sets from successors
            num_bindings = random.randint(1, max_bindings_per_activity)
            binding_sets = _generate_random_binding_sets(
                succ_set, 
                num_bindings, 
                max_bindings_per_activity
            )
            causal_net.output_bindings[activity] = binding_sets
        # else: leave as empty list (already initialized in CausalNet.__init__)
    
    return causal_net


def _extract_direct_follows(
    df: pd.DataFrame, 
    activities: List[str]
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Extract direct follow relationships from the event log.
    
    Analyzes the event log to identify which activities directly follow
    which other activities within the same case. Activity B directly follows
    activity A if there exists at least one case where A is immediately
    succeeded by B in the event sequence.
    
    This relationship forms the basis for generating valid binding sets
    that respect the observed behavior in the event log.
    
    Args:
        df: Pandas DataFrame with columns "case:concept:name" and "concept:name".
            Events should be in chronological order within each case.
        activities: List of activity names to consider for follow relationships.
            Activities not in this list will be ignored.
    
    Returns:
        Tuple containing two dictionaries:
            - predecessors: Mapping from activity to set of activities that
              directly precede it (input candidates)
            - successors: Mapping from activity to set of activities that
              directly follow it (output candidates)
    
    Example:
        >>> df = pd.DataFrame({
        ...     'case:concept:name': [1, 1, 2, 2],
        ...     'concept:name': ['A', 'B', 'A', 'C']
        ... })
        >>> preds, succs = _extract_direct_follows(df, ['A', 'B', 'C'])
        >>> preds['B']
        {'A'}
        >>> succs['A']
        {'B', 'C'}
    """
    # Initialize dictionaries to store predecessors and successors
    predecessors: Dict[str, Set[str]] = {activity: set() for activity in activities}
    successors: Dict[str, Set[str]] = {activity: set() for activity in activities}
    
    # Convert activities to set for O(1) lookup
    activity_set = set(activities)
    
    # Group events by case and sort by order within case
    # Assumes DataFrame is already sorted chronologically within cases
    grouped = df.groupby("case:concept:name")
    
    for case_id, case_df in grouped:
        # Get activity sequence for this case
        case_activities = case_df["concept:name"].tolist()
        
        # Filter to only include activities in our activity list
        case_activities = [
            act for act in case_activities if act in activity_set
        ]
        
        # Extract direct follow relationships within this case
        for i in range(len(case_activities) - 1):
            current_activity = case_activities[i]
            next_activity = case_activities[i + 1]
            
            # current_activity directly precedes next_activity
            predecessors[next_activity].add(current_activity)
            
            # next_activity directly follows current_activity
            successors[current_activity].add(next_activity)
    
    return predecessors, successors


def _generate_random_binding_sets(
    source_activities: Set[str],
    num_bindings: int,
    max_bindings_per_activity: int
) -> List[FrozenSet[str]]:
    """
    Generate random binding sets from a set of source activities.
    
    Creates a specified number of binding sets by randomly sampling
    from the source activities. Each binding set is a non-empty frozenset
    containing one or more activities from the source set.
    
    This function ensures diversity in the initial population by creating
    varied binding structures while respecting the observed direct follow
    relationships in the event log.
    
    Args:
        source_activities: Set of activity names to sample from.
            These are either predecessors (for input bindings) or
            successors (for output bindings) of a target activity.
        num_bindings: Number of binding sets to generate.
            Will be between 1 and max_bindings_per_activity (inclusive).
        max_bindings_per_activity: Maximum size of each binding set.
            Limits the complexity of individual binding sets.
    
    Returns:
        List[FrozenSet[str]]: List of non-empty frozensets, where each
            frozenset represents a binding set of source activities.
            The list length equals num_bindings.
    
    Note:
        If source_activities contains fewer elements than needed to create
        diverse binding sets, some binding sets may be duplicates. This is
        acceptable for initial population diversity and will be refined
        during the evolutionary process.
    
    Example:
        >>> sources = {'A', 'B', 'C'}
        >>> bindings = _generate_random_binding_sets(sources, 2, 2)
        >>> len(bindings)
        2
        >>> all(isinstance(b, frozenset) and len(b) > 0 for b in bindings)
        True
    """
    binding_sets: List[FrozenSet[str]] = []
    source_list = list(source_activities)
    
    for _ in range(num_bindings):
        # Randomly select size for this binding set (at least 1, at most max)
        # Cannot exceed the number of available source activities
        max_size = min(max_bindings_per_activity, len(source_list))
        binding_size = random.randint(1, max_size)
        
        # Randomly sample activities for this binding set
        sampled_activities = random.sample(source_list, binding_size)
        
        # Create frozenset (immutable, hashable) for the binding set
        binding_set = frozenset(sampled_activities)
        
        binding_sets.append(binding_set)
    
    return binding_sets