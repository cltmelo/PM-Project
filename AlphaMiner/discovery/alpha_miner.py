"""
Alpha Miner algorithm implementation.

Discovers Petri nets from event logs using the Alpha Miner algorithm.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd

import pm4py
from pm4py.objects.petri.net import PetriNet
from pm4py.objects.petri.semantics import Marking

from ..utils.logging_utils import print_header, print_info, print_success


@dataclass
class AlphaMinerResult:
    """Result container for Alpha Miner discovery."""
    net: PetriNet
    initial_marking: Marking
    final_marking: Marking
    
    @property
    def num_places(self) -> int:
        """Get the number of places."""
        return len(self.net.places)
    
    @property
    def num_transitions(self) -> int:
        """Get the number of transitions."""
        return len(self.net.transitions)
    
    @property
    def num_arcs(self) -> int:
        """Get the number of arcs."""
        return len(self.net.arcs)
    
    @property
    def structure_summary(self) -> dict:
        """Get a summary of the model structure."""
        return {
            "num_places": self.num_places,
            "num_transitions": self.num_transitions,
            "num_arcs": self.num_arcs,
            "total_elements": self.num_places + self.num_transitions + self.num_arcs,
        }


class AlphaMinerDiscoverer:
    """
    Discovers Petri nets using the Alpha Miner algorithm.
    
    The Alpha Miner is a classic process discovery algorithm that:
    1. Analyzes direct succession relationships
    2. Builds place/transition net based on causal dependencies
    3. Produces a sound Workflow net
    
    Example:
        discoverer = AlphaMinerDiscoverer()
        result = discoverer.discover(df)
        net = result.net
    """
    
    def __init__(self):
        """Initialize the Alpha Miner discoverer."""
        self._result: Optional[AlphaMinerResult] = None
    
    @property
    def result(self) -> AlphaMinerResult:
        """Get the discovery result."""
        if self._result is None:
            raise ValueError("No discovery run. Call discover() first.")
        return self._result
    
    @property
    def net(self) -> PetriNet:
        """Get the discovered Petri net."""
        return self.result.net
    
    @property
    def initial_marking(self) -> Marking:
        """Get the initial marking."""
        return self.result.initial_marking
    
    @property
    def final_marking(self) -> Marking:
        """Get the final marking."""
        return self.result.final_marking
    
    def discover(self, df: pd.DataFrame) -> AlphaMinerResult:
        """
        Discover a Petri net from an event log.
        
        Args:
            df: Event log DataFrame with columns:
                - case:concept:name: Case identifier
                - concept:name: Activity name
                - time:timestamp: Event timestamp
                
        Returns:
            AlphaMinerResult containing the Petri net and markings
            
        Raises:
            ValueError: If the DataFrame is empty or missing required columns
        """
        print_header("ALPHA MINER DISCOVERY")
        
        # Validate input
        self._validate_input(df)
        
        print("\n⏳ Running Alpha Miner algorithm...")
        print("   This may take a while for large event logs.")
        
        # Discover Petri net using pm4py's Alpha Miner
        try:
            net, initial_marking, final_marking = pm4py.discover_petri_net_alpha(df)
            
            # Create result object
            self._result = AlphaMinerResult(
                net=net,
                initial_marking=initial_marking,
                final_marking=final_marking
            )
            
            # Print summary
            print_success("Petri net discovered successfully!")
            self._print_structure_summary()
            
            return self._result
            
        except Exception as e:
            raise RuntimeError(f"Alpha Miner discovery failed: {e}") from e
    
    def discover_alpha_plus(self, df: pd.DataFrame) -> AlphaMinerResult:
        """
        Discover a Petri net using Alpha+ variant.
        
        Alpha+ handles indirect succession relations and produces
        more precise models for some process types.
        
        Args:
            df: Event log DataFrame
            
        Returns:
            AlphaMinerResult containing the Petri net and markings
        """
        print_header("ALPHA+ DISCOVERY")
        
        self._validate_input(df)
        
        print("\n⏳ Running Alpha+ algorithm...")
        
        try:
            net, initial_marking, final_marking = pm4py.discover_petri_net_alpha_plus(df)
            
            self._result = AlphaMinerResult(
                net=net,
                initial_marking=initial_marking,
                final_marking=final_marking
            )
            
            print_success("Petri net discovered successfully!")
            self._print_structure_summary()
            
            return self._result
            
        except Exception as e:
            raise RuntimeError(f"Alpha+ discovery failed: {e}") from e
    
    def _validate_input(self, df: pd.DataFrame) -> None:
        """Validate the input DataFrame."""
        if df is None or len(df) == 0:
            raise ValueError("Event log DataFrame is empty")
        
        required_columns = ['case:concept:name', 'concept:name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        print_info("Input cases", df['case:concept:name'].nunique())
        print_info("Input events", len(df))
    
    def _print_structure_summary(self) -> None:
        """Print the structure summary."""
        summary = self.result.structure_summary
        print_info("Places", summary["num_places"])
        print_info("Transitions", summary["num_transitions"])
        print_info("Arcs", summary["num_arcs"])