"""
Metrics Computation for Evolutionary Process Discovery.

This module provides evaluation metrics for candidate process models 
(CausalNet instances) in the context of evolutionary process discovery 
algorithms, specifically designed for BPI Challenge 2017 dataset analysis.

Available Metrics:
    - compute_replay_fitness: Evaluates how well a causal net can replay 
      the traces in an event log using token-based semantics. Returns a 
      score between 0.0 (poor fit) and 1.0 (perfect fit).
    
    - compute_simplicity: Evaluates the structural complexity of a causal 
      net by counting activity references across all binding sets. Returns 
      a score between 0.0 (complex) and 1.0 (simple).

These metrics are used together in multi-objective optimization to guide 
the evolutionary algorithm toward process models that balance fitness 
(accuracy) and simplicity (parsimony).

Author: Senior Process Mining Engineer
Date: 2024
"""

from collections import Counter
from typing import FrozenSet
import random
import pandas as pd
from causal_net import CausalNet


def compute_replay_fitness(causal_net: CausalNet, df: pd.DataFrame) -> float:
    """
    Compute replay fitness score for a CausalNet against an event log.
    
    Evaluates how well the causal net can replay the traces in the event log
    by simulating token-based execution. The fitness score ranges from 0.0
    (poor fit) to 1.0 (perfect fit), measuring the alignment between the
    process model and observed behavior.
    
    The replay semantics:
    1. Each case starts with an empty token multiset
    2. Activities consume tokens from input bindings and produce tokens
       to output bindings
    3. Missing tokens (disabled activities) and remaining tokens (after
       case completion) both penalize the fitness score
    
    Args:
        causal_net: CausalNet instance representing the process model to evaluate.
            Contains input_bindings and output_bindings for each activity.
        df: Pandas DataFrame representing the event log with required columns:
            - "case:concept:name": Case identifier for grouping events
            - "concept:name": Activity name for each event
            Events should be in chronological order within each case (original
            row order is preserved during groupby iteration).
    
    Returns:
        float: Fitness score between 0.0 and 1.0, where:
            - 1.0 indicates perfect replay (no missing or remaining tokens)
            - 0.0 indicates very poor replay capability
            - Scores are clamped to ensure they stay within [0.0, 1.0]
    
    Raises:
        ValueError: If required columns are missing from the DataFrame or
            if total_activities is zero (empty event log).
    
    Note:
        The fitness formula is:
        fitness = 1 - ((total_missing_events + total_remaining_tokens) / 
                       (2 * total_activities))
        
        This formula equally weights missing tokens (cannot fire activities)
        and remaining tokens (incomplete case execution).
    
    Example:
        >>> import pandas as pd
        >>> from causal_net import CausalNet
        >>> df = pd.DataFrame({
        ...     'case:concept:name': [1, 1, 2, 2],
        ...     'concept:name': ['A', 'B', 'A', 'B']
        ... })
        >>> net = CausalNet(['A', 'B'])
        >>> net.output_bindings['A'].append(frozenset(['A']))  # A produces token for itself
        >>> fitness = compute_replay_fitness(net, df)
        >>> 0.0 <= fitness <= 1.0
        True
    """
    # Validate input DataFrame has required columns
    required_columns = ["case:concept:name", "concept:name"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Initialize counters for fitness computation
    total_missing_events = 0
    total_remaining_tokens = 0
    total_activities = 0
    
    # Group events by case ID, preserving original row order within each case
    grouped = df.groupby("case:concept:name", sort=False)
    
    for case_id, case_df in grouped:
        # Get activity sequence for this case in original order
        trace = case_df["concept:name"].tolist()
        total_activities += len(trace)
        
        # Initialize token multiset for this case (starts empty)
        token_multiset: Counter = Counter()
        
        # Replay each activity in the trace sequentially
        for activity in trace:
            # Check if activity is enabled given current token multiset
            is_enabled, satisfied_binding = _is_activity_enabled(
                activity, 
                causal_net.input_bindings, 
                token_multiset
            )
            
            if is_enabled:
                # Fire the activity: consume tokens from satisfied input binding
                _consume_tokens(token_multiset, satisfied_binding)
                
                # Produce tokens to output bindings (if any exist)
                _produce_tokens(
                    activity, 
                    causal_net.output_bindings, 
                    token_multiset
                )
            else:
                # Activity cannot fire - count as missing token event
                total_missing_events += 1
                # Do not modify token multiset
        
        # After replaying all activities, count remaining tokens
        case_remaining_tokens = sum(token_multiset.values())
        total_remaining_tokens += case_remaining_tokens
    
    # Prevent division by zero for empty event logs
    if total_activities == 0:
        raise ValueError("Event log contains no activities")
    
    # Compute fitness score using the standard replay fitness formula
    # Equal weight given to missing events and remaining tokens
    penalty = (total_missing_events + total_remaining_tokens) / (2 * total_activities)
    fitness = 1.0 - penalty
    
    # Clamp fitness to valid range [0.0, 1.0]
    fitness = max(0.0, min(1.0, fitness))
    
    return fitness


def _is_activity_enabled(
    activity: str,
    input_bindings: dict,
    token_multiset: Counter
) -> tuple[bool, FrozenSet[str] | None]:
    """
    Check if an activity is enabled given the current token multiset.
    
    An activity is enabled if:
    1. Its input_bindings list is empty (always enabled, requires no tokens), OR
    2. At least one frozenset in its input_bindings is entirely contained
       within the current token multiset (every activity in the frozenset
       has at least one token available)
    
    Args:
        activity: Name of the activity to check for enabled status.
        input_bindings: Dictionary mapping activity names to their input
            binding lists (list of frozensets).
        token_multiset: Counter representing current token distribution,
            where keys are activity names and values are token counts.
    
    Returns:
        tuple: Two-element tuple containing:
            - bool: True if activity is enabled, False otherwise
            - FrozenSet[str] | None: The first satisfied binding frozenset
              if enabled, None if not enabled or if input_bindings is empty
    
    Example:
        >>> tokens = Counter({'A': 2, 'B': 1})
        >>> bindings = {'C': [frozenset(['A', 'B']), frozenset(['A'])]}
        >>> enabled, binding = _is_activity_enabled('C', bindings, tokens)
        >>> enabled
        True
        >>> binding
        frozenset({'A', 'B'})
    """
    # Get input binding sets for this activity
    activity_input_bindings = input_bindings.get(activity, [])
    
    # Empty input bindings means activity is always enabled (start activity)
    if not activity_input_bindings:
        return True, None
    
    # Check each binding set to see if it's satisfied by current tokens
    for binding_set in activity_input_bindings:
        if _is_binding_satisfied(binding_set, token_multiset):
            return True, binding_set
    
    # No binding set is satisfied - activity is not enabled
    return False, None


def _is_binding_satisfied(
    binding_set: FrozenSet[str],
    token_multiset: Counter
) -> bool:
    """
    Check if a binding set is satisfied by the current token multiset.
    
    A binding set is satisfied if every activity name in the frozenset
    has at least one token available in the token multiset.
    
    Args:
        binding_set: Frozenset of activity names that must all have tokens
            available for this binding to be satisfied.
        token_multiset: Counter representing current token distribution.
    
    Returns:
        bool: True if all activities in binding_set have at least one token,
            False otherwise.
    
    Example:
        >>> tokens = Counter({'A': 2, 'B': 1, 'C': 0})
        >>> _is_binding_satisfied(frozenset(['A', 'B']), tokens)
        True
        >>> _is_binding_satisfied(frozenset(['A', 'C']), tokens)
        False
    """
    for required_activity in binding_set:
        if token_multiset.get(required_activity, 0) < 1:
            return False
    return True


def _consume_tokens(
    token_multiset: Counter,
    binding_set: FrozenSet[str] | None
) -> None:
    """
    Consume tokens from the token multiset according to a binding set.
    
    Removes one token for each activity name in the binding set from
    the token multiset. Token counts can go to zero but not negative.
    
    Args:
        token_multiset: Counter representing current token distribution.
            Modified in-place.
        binding_set: Frozenset of activity names to consume tokens from.
            If None, no tokens are consumed (for activities with empty
            input bindings).
    
    Note:
        This function modifies the token_multiset in-place. No return value.
    
    Example:
        >>> tokens = Counter({'A': 3, 'B': 2})
        >>> _consume_tokens(tokens, frozenset(['A', 'B']))
        >>> tokens['A']
        2
        >>> tokens['B']
        1
    """
    if binding_set is None:
        return
    
    for activity in binding_set:
        token_multiset[activity] -= 1
        # Ensure token count doesn't go negative (shouldn't happen if
        # binding was properly satisfied, but defensive programming)
        if token_multiset[activity] < 0:
            token_multiset[activity] = 0


def _produce_tokens(
    activity: str,
    output_bindings: dict,
    token_multiset: Counter
) -> None:
    """
    Produce tokens to the token multiset according to output bindings.
    
    Randomly selects one frozenset from the activity's output_bindings list
    and adds one token for each activity name in that frozenset to the
    token multiset.
    
    Args:
        activity: Name of the activity that just fired and is producing tokens.
        output_bindings: Dictionary mapping activity names to their output
            binding lists (list of frozensets).
        token_multiset: Counter representing current token distribution.
            Modified in-place.
    
    Note:
        This function modifies the token_multiset in-place. No return value.
        If output_bindings for the activity is empty, no tokens are produced.
    
    Example:
        >>> tokens = Counter({'A': 1})
        >>> outputs = {'A': [frozenset(['B', 'C']), frozenset(['B'])]}
        >>> _produce_tokens('A', outputs, tokens)  # Randomly selects one binding
        >>> 'B' in tokens
        True
    """
    # Get output binding sets for this activity
    activity_output_bindings = output_bindings.get(activity, [])
    
    # No output bindings means no tokens are produced (end activity)
    if not activity_output_bindings:
        return
    
    # Randomly select one output binding set to produce tokens
    selected_binding = random.choice(activity_output_bindings)
    
    # Add one token for each activity in the selected binding set
    for target_activity in selected_binding:
        token_multiset[target_activity] += 1


def compute_simplicity(causal_net: CausalNet) -> float:
    """
    Compute simplicity score for a CausalNet based on structural complexity.
    
    Evaluates the structural simplicity of a causal net by counting the
    total number of individual activity references across all binding sets.
    Simpler models with fewer and smaller bindings receive higher scores.
    
    The simplicity metric penalizes complexity in the process model structure,
    encouraging the evolutionary algorithm to find parsimonious solutions
    that explain the observed behavior without unnecessary complexity.
    
    Args:
        causal_net: CausalNet instance representing the process model to evaluate.
            Contains input_bindings and output_bindings for each activity.
            Each binding is a frozenset of activity names.
    
    Returns:
        float: Simplicity score between 0.0 and 1.0, where:
            - 1.0 indicates maximum simplicity (no bindings/arcs)
            - Scores approach 0.0 as complexity increases
            - Formula: 1 / (1 + total_arc_count)
    
    Note:
        The total_arc_count is computed by summing the size of every
        frozenset in both input_bindings and output_bindings across
        all activities. Each activity reference in a binding set counts
        as one arc.
        
        Example arc count calculation:
        - Activity 'A' has input_bindings: [frozenset(['B', 'C'])]
          → contributes 2 arcs (B and C)
        - Activity 'A' has output_bindings: [frozenset(['D']), frozenset(['E', 'F'])]
          → contributes 3 arcs (D, E, and F)
        - Total for activity 'A': 5 arcs
    
    Example:
        >>> from causal_net import CausalNet
        >>> net = CausalNet(['A', 'B', 'C'])
        >>> net.input_bindings['B'].append(frozenset(['A']))
        >>> net.output_bindings['A'].append(frozenset(['B']))
        >>> simplicity = compute_simplicity(net)
        >>> simplicity  # 1 / (1 + 2) = 0.333...
        0.3333333333333333
        >>> 
        >>> # Empty causal net has maximum simplicity
        >>> empty_net = CausalNet(['A', 'B'])
        >>> compute_simplicity(empty_net)
        1.0
    """
    # Initialize counter for total arc count
    total_arc_count = 0
    
    # Count arcs in input bindings across all activities
    # Each activity reference in a binding frozenset counts as one arc
    for activity in causal_net.activities:
        input_binding_sets = causal_net.input_bindings.get(activity, [])
        for binding_set in input_binding_sets:
            total_arc_count += len(binding_set)
    
    # Count arcs in output bindings across all activities
    # Each activity reference in a binding frozenset counts as one arc
    for activity in causal_net.activities:
        output_binding_sets = causal_net.output_bindings.get(activity, [])
        for binding_set in output_binding_sets:
            total_arc_count += len(binding_set)
    
    # Compute simplicity score using inverse relationship with arc count
    # Formula: 1 / (1 + total_arc_count) ensures:
    # - Score of 1.0 when total_arc_count = 0 (empty causal net)
    # - Score approaches 0.0 as complexity increases
    # - Always in valid range [0.0, 1.0]
    simplicity_score = 1.0 / (1.0 + total_arc_count)
    
    return simplicity_score