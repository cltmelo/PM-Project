"""
Causal Net Implementation for Process Discovery Algorithm.

This module provides a CausalNet class for representing process models
in the context of evolutionary process discovery algorithms, specifically
designed for BPI Challenge 2017 dataset analysis.

A causal net stores, for each activity in an event log, two sets of bindings:
1. Input binding sets: frozensets of activity names that must precede the activity
2. Output binding sets: frozensets of activity names that must follow the activity

Author: Senior Process Mining Engineer
Date: 2024
"""

from __future__ import annotations

from typing import List, FrozenSet, Dict


class CausalNet:
    """
    A causal net data structure for representing process models.
    
    A causal net stores, for each activity in an event log, two sets of bindings:
    1. Input binding sets: frozensets of activity names that must precede the activity
    2. Output binding sets: frozensets of activity names that must follow the activity
    
    This representation is used in evolutionary process discovery algorithms
    where candidate process models are evolved through a population-based approach.
    Each candidate solution in the population is represented as a CausalNet instance.
    
    Attributes:
        activities (List[str]): List of all activity names in the process model
        input_bindings (Dict[str, List[FrozenSet[str]]]): Mapping from activity name 
            to list of input binding sets (predecessors). Each binding set is a 
            frozenset of activity names that must precede the key activity.
        output_bindings (Dict[str, List[FrozenSet[str]]]): Mapping from activity name 
            to list of output binding sets (successors). Each binding set is a 
            frozenset of activity names that must follow the key activity.
    
    Example:
        >>> activities = ['A', 'B', 'C']
        >>> net = CausalNet(activities)
        >>> net.input_bindings['B'].append(frozenset(['A']))
        >>> net.output_bindings['A'].append(frozenset(['B']))
    """
    
    def __init__(self, activities: List[str]) -> None:
        """
        Initialize a CausalNet with a list of activity names.
        
        Creates empty input and output binding lists for each activity.
        This constructor establishes the foundation for the causal net structure
        by initializing all activities with empty binding sets ready to be 
        populated during the evolutionary process discovery algorithm.
        
        Args:
            activities: List of unique activity names in the process model.
                These correspond to the distinct activities found in the 
                BPI Challenge 2017 event log.
            
        Raises:
            ValueError: If activities list is empty or contains duplicates.
                Empty activity lists cannot form valid process models.
                Duplicate activities would create ambiguous binding structures.
            
        Example:
            >>> net = CausalNet(['Start', 'Process', 'End'])
            >>> len(net.activities)
            3
            >>> len(net.input_bindings['Process'])
            0
        """
        if not activities:
            raise ValueError("Activities list cannot be empty")
        
        if len(activities) != len(set(activities)):
            raise ValueError("Activities list contains duplicates")
        
        # Store a copy of the activities list to prevent external modification
        self.activities: List[str] = activities.copy()
        
        # Initialize empty binding lists for each activity
        # Input bindings: what must precede this activity
        self.input_bindings: Dict[str, List[FrozenSet[str]]] = {
            activity: [] for activity in self.activities
        }
        
        # Output bindings: what must follow this activity
        self.output_bindings: Dict[str, List[FrozenSet[str]]] = {
            activity: [] for activity in self.activities
        }
    
    def copy(self) -> CausalNet:
        """
        Create a deep copy of this CausalNet instance.
        
        Returns a new CausalNet object with identical structure and bindings,
        but with all nested objects independently copied (no shared references).
        This is essential for evolutionary algorithms where multiple candidate
        solutions must be modified independently without affecting the parent.
        
        The deep copy ensures that:
        - The activities list is independent
        - Input binding lists are independent
        - Output binding lists are independent
        - Individual frozenset bindings are independent
        
        Returns:
            CausalNet: A deep copy of this causal net suitable for use as
                a new candidate solution in the evolutionary population.
            
        Example:
            >>> net = CausalNet(['A', 'B'])
            >>> net.input_bindings['B'].append(frozenset(['A']))
            >>> net_copy = net.copy()
            >>> net_copy.input_bindings['B'].append(frozenset([]))
            >>> len(net.input_bindings['B'])
            1
            >>> len(net_copy.input_bindings['B'])
            2
        """
        # Create new instance with same activities (copied to prevent sharing)
        new_net = CausalNet(self.activities.copy())
        
        # Deep copy the input bindings for each activity
        # Each binding set (frozenset) is immutable, but the list container must be copied
        for activity in self.activities:
            new_net.input_bindings[activity] = [
                binding_set for binding_set in self.input_bindings[activity]
            ]
        
        # Deep copy the output bindings for each activity
        for activity in self.activities:
            new_net.output_bindings[activity] = [
                binding_set for binding_set in self.output_bindings[activity]
            ]
        
        return new_net
    
    def __repr__(self) -> str:
        """
        Return a string representation of the CausalNet.
        
        Provides a concise summary of the causal net structure including
        the number of activities and total binding counts. Useful for
        debugging and monitoring the evolutionary process discovery algorithm.
        
        Returns:
            str: String showing number of activities and total bindings
                in the format: CausalNet(activities=N, input_bindings=M, output_bindings=K)
        
        Example:
            >>> net = CausalNet(['A', 'B', 'C'])
            >>> repr(net)
            'CausalNet(activities=3, input_bindings=0, output_bindings=0)'
        """
        total_input = sum(len(bindings) for bindings in self.input_bindings.values())
        total_output = sum(len(bindings) for bindings in self.output_bindings.values())
        
        return (
            f"CausalNet(activities={len(self.activities)}, "
            f"input_bindings={total_input}, output_bindings={total_output})"
        )
    
    def __eq__(self, other: object) -> bool:
        """
        Check equality between two CausalNet instances.
        
        Two causal nets are considered equal if they have the same activities
        and identical input/output binding structures. This is useful for
        detecting duplicate solutions in the evolutionary population.
        
        Args:
            other: Another object to compare against this CausalNet
            
        Returns:
            bool: True if both causal nets are structurally identical
            
        Example:
            >>> net1 = CausalNet(['A', 'B'])
            >>> net2 = CausalNet(['A', 'B'])
            >>> net1 == net2
            True
        """
        if not isinstance(other, CausalNet):
            return False
        
        if self.activities != other.activities:
            return False
        
        # Compare input bindings
        for activity in self.activities:
            if set(self.input_bindings[activity]) != set(other.input_bindings[activity]):
                return False
        
        # Compare output bindings
        for activity in self.activities:
            if set(self.output_bindings[activity]) != set(other.output_bindings[activity]):
                return False
        
        return True