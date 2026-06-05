"""
Fitness evaluation using token-based replay.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

import pm4py
from pm4py.objects.petri.net import PetriNet
from pm4py.objects.petri.semantics import Marking

from ..utils.logging_utils import print_header, print_info, print_success, print_warning


@dataclass
class FitnessResult:
    """Container for fitness evaluation results."""
    fitness: float
    percent_fit_traces: float
    average_trace_fitness: float
    total_produced_tokens: int
    total_consumed_tokens: int
    total_missing_tokens: int
    total_remaining_tokens: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "token_replay_fitness": round(self.fitness, 4),
            "percent_fit_traces": round(self.percent_fit_traces, 4),
            "average_trace_fitness": round(self.average_trace_fitness, 4),
            "produced_tokens": self.total_produced_tokens,
            "consumed_tokens": self.total_consumed_tokens,
            "missing_tokens": self.total_missing_tokens,
            "remaining_tokens": self.total_remaining_tokens,
        }


class FitnessEvaluator:
    """
    Evaluates fitness using token-based replay.
    
    Token-based replay measures how well a Petri net can replay
    all traces in an event log by tracking token production and
    consumption.
    
    Example:
        evaluator = FitnessEvaluator()
        result = evaluator.evaluate(df, net, initial_marking, final_marking)
        print(f"Fitness: {result.fitness}")
    """
    
    def __init__(self):
        """Initialize the fitness evaluator."""
        self._result: Optional[FitnessResult] = None
    
    @property
    def result(self) -> Optional[FitnessResult]:
        """Get the evaluation result."""
        return self._result
    
    def evaluate(
        self,
        df: pd.DataFrame,
        net: PetriNet,
        initial_marking: Marking,
        final_marking: Marking,
    ) -> FitnessResult:
        """
        Evaluate fitness using token-based replay.
        
        Args:
            df: Event log DataFrame
            net: Petri net
            initial_marking: Initial marking
            final_marking: Final marking
            
        Returns:
            FitnessResult with detailed metrics
        """
        print_header("FITNESS EVALUATION")
        print("\n⏳ Running token-based replay...")
        
        try:
            # Run token-based replay
            result = pm4py.fitness_token_based_replay(
                df, net, initial_marking, final_marking
            )
            
            # Parse results
            self._result = FitnessResult(
                fitness=result["log_fitness"],
                percent_fit_traces=result.get("percentage_of_fit_traces", 0),
                average_trace_fitness=result.get("average_trace_fitness", 0),
                total_produced_tokens=result.get("produced_tokens", 0),
                total_consumed_tokens=result.get("consumed_tokens", 0),
                total_missing_tokens=result.get("missing_tokens", 0),
                total_remaining_tokens=result.get("remaining_tokens", 0),
            )
            
            print_success("Fitness evaluation completed!")
            self._print_summary()
            
            return self._result
            
        except Exception as e:
            print_warning(f"Fitness evaluation failed: {e}")
            # Return a default result indicating failure
            self._result = FitnessResult(
                fitness=0.0,
                percent_fit_traces=0.0,
                average_trace_fitness=0.0,
                total_produced_tokens=0,
                total_consumed_tokens=0,
                total_missing_tokens=0,
                total_remaining_tokens=0,
            )
            return self._result
    
    def _print_summary(self) -> None:
        """Print a summary of the fitness results."""
        r = self._result
        print_info("Log fitness", f"{r.fitness:.4f}")
        print_info("Fit traces", f"{r.percent_fit_traces:.2%}")
        print_info("Produced tokens", r.total_produced_tokens)
        print_info("Missing tokens", r.total_missing_tokens)