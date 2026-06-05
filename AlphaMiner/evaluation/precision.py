"""
Precision evaluation using token-based replay.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

import pm4py
from pm4py.objects.petri.net import PetriNet
from pm4py.objects.petri.semantics import Marking

from ..utils.logging_utils import print_header, print_info, print_success, print_warning


@dataclass
class PrecisionResult:
    """Container for precision evaluation results."""
    precision: float
    escaped_tokens: int
    not_escaped_tokens: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "precision": round(self.precision, 4),
            "escaped_tokens": self.escaped_tokens,
            "not_escaped_tokens": self.not_escaped_tokens,
        }


class PrecisionEvaluator:
    """
    Evaluates precision using token-based replay.
    
    Precision measures how much extra behavior a model allows
    that was not observed in the event log. Higher precision
    means less extra behavior.
    
    Example:
        evaluator = PrecisionEvaluator()
        result = evaluator.evaluate(df, net, initial_marking, final_marking)
        print(f"Precision: {result.precision}")
    """
    
    def __init__(self):
        """Initialize the precision evaluator."""
        self._result: Optional[PrecisionResult] = None
    
    @property
    def result(self) -> Optional[PrecisionResult]:
        """Get the evaluation result."""
        return self._result
    
    def evaluate(
        self,
        df: pd.DataFrame,
        net: PetriNet,
        initial_marking: Marking,
        final_marking: Marking,
    ) -> PrecisionResult:
        """
        Evaluate precision using token-based replay.
        
        Args:
            df: Event log DataFrame
            net: Petri net
            initial_marking: Initial marking
            final_marking: Final marking
            
        Returns:
            PrecisionResult with detailed metrics
        """
        print_header("PRECISION EVALUATION")
        print("\n⏳ Computing precision...")
        
        try:
            # Compute precision
            result = pm4py.precision_token_based_replay(
                df, net, initial_marking, final_marking
            )
            
            # Parse results (format varies by pm4py version)
            if isinstance(result, tuple):
                escaped, not_escaped = result[1], result[2] if len(result) > 2 else (0, 0)
            else:
                escaped, not_escaped = 0, 0
            
            self._result = PrecisionResult(
                precision=result[0] if isinstance(result, tuple) else result,
                escaped_tokens=escaped,
                not_escaped_tokens=not_escaped,
            )
            
            print_success("Precision evaluation completed!")
            self._print_summary()
            
            return self._result
            
        except Exception as e:
            print_warning(f"Precision evaluation failed: {e}")
            # Return a default result indicating failure
            self._result = PrecisionResult(
                precision=0.0,
                escaped_tokens=0,
                not_escaped_tokens=0,
            )
            return self._result
    
    def _print_summary(self) -> None:
        """Print a summary of the precision results."""
        r = self._result
        print_info("Precision", f"{r.precision:.4f}")
        print_info("Escaped tokens", r.escaped_tokens)