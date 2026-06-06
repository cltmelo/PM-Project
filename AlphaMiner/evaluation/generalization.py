"""
Generalization evaluation.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

import pm4py
from pm4py import PetriNet, Marking

from ..utils.logging_utils import print_header, print_info, print_success, print_warning


@dataclass
class GeneralizationResult:
    """Container for generalization results."""
    generalization: float

    def to_dict(self) -> dict:
        return {
            "generalization": round(self.generalization, 4),
        }


class GeneralizationEvaluator:
    """
    Evaluates generalization using directly-follows relations.
    
    Generalization = (relations in BOTH model AND log) / (relations in model)
    """
    
    def __init__(self):
        self._result: Optional[GeneralizationResult] = None
    
    @property
    def result(self) -> Optional[GeneralizationResult]:
        return self._result
    
    def evaluate(
        self,
        df: pd.DataFrame,
        net: PetriNet,
        initial_marking: Marking,
        final_marking: Marking,
    ) -> GeneralizationResult:
        """
        Evaluate generalization.
        
        Args:
            df: Event log DataFrame
            net: Petri net
            initial_marking: Initial marking
            final_marking: Final marking
            
        Returns:
            GeneralizationResult
        """
        print_header("GENERALIZATION EVALUATION")
        print("\n⏳ Computing generalization...")
        
        try:
            # Get log relations
            log_relations = set()
            df_sorted = df.sort_values(['case:concept:name', 'time:timestamp'])
            for case_id, group in df_sorted.groupby('case:concept:name'):
                activities = group['concept:name'].tolist()
                for i in range(len(activities) - 1):
                    log_relations.add((activities[i], activities[i + 1]))
            
            # Get model relations from PNML
            model_relations = set()
            for arc in net.arcs:
                source = arc.source.name if hasattr(arc.source, 'name') else str(arc.source)
                target = arc.target.name if hasattr(arc.target, 'name') else str(arc.target)
                # Skip if involves places
                if not source.startswith('p_') and not target.startswith('p_'):
                    model_relations.add((source, target))
            
            if not model_relations:
                print_warning("No model relations found")
                self._result = GeneralizationResult(generalization=0.0)
                return self._result
            
            # Calculate generalization
            observed = len(log_relations & model_relations)
            generalization = observed / len(model_relations)
            
            self._result = GeneralizationResult(generalization=generalization)
            print_success("Generalization evaluation completed!")
            print_info("Generalization", f"{generalization:.4f}")
            
            return self._result
            
        except Exception as e:
            print_warning(f"Generalization evaluation failed: {e}")
            self._result = GeneralizationResult(generalization=0.0)
            return self._result
