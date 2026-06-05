"""
Combined process metrics evaluation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd

import pm4py
from pm4py import PetriNet, Marking

from ..utils.logging_utils import print_header, print_stage, print_info, print_success
from ..utils.metrics_utils import calculate_f_score

from .fitness import FitnessEvaluator, FitnessResult
from .precision import PrecisionEvaluator, PrecisionResult


@dataclass
class ProcessMetrics:
    """
    Container for all process model metrics.
    
    Aggregates fitness, precision, and structure metrics
    into a single unified result.
    """
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Event log stats
    num_cases: int = 0
    num_events: int = 0
    num_activities: int = 0
    
    # Model structure
    num_places: int = 0
    num_transitions: int = 0
    num_arcs: int = 0
    
    # Quality metrics
    fitness: Optional[float] = None
    precision: Optional[float] = None
    f_score: Optional[float] = None
    
    # Detailed results (for debugging)
    fitness_details: Optional[Dict[str, Any]] = None
    precision_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "algorithm": "Alpha Miner",
            "timestamp": self.timestamp.isoformat(),
            "event_log": {
                "num_cases": self.num_cases,
                "num_events": self.num_events,
                "num_activities": self.num_activities,
            },
            "model_structure": {
                "num_places": self.num_places,
                "num_transitions": self.num_transitions,
                "num_arcs": self.num_arcs,
                "total_elements": self.num_places + self.num_transitions + self.num_arcs,
            },
            "quality_metrics": {
                "fitness": {
                    "token_replay": self.fitness,
                    "description": "Token-based replay fitness (1.0 = perfect)",
                },
                "precision": {
                    "value": self.precision,
                    "description": "ETD-based precision (1.0 = no extra behavior)",
                },
                "f_score": {
                    "value": self.f_score,
                    "description": "Harmonic mean of fitness and precision",
                },
            },
            "fitness_details": self.fitness_details,
            "precision_details": self.precision_details,
        }


class MetricsCollector:
    """
    Collects and computes all process metrics.
    
    Orchestrates fitness and precision evaluation to
    produce a complete set of quality metrics.
    
    Example:
        collector = MetricsCollector()
        metrics = collector.collect(df, net, initial_marking, final_marking)
        print(f"F-Score: {metrics.f_score}")
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._fitness_evaluator = FitnessEvaluator()
        self._precision_evaluator = PrecisionEvaluator()
        self._metrics: Optional[ProcessMetrics] = None
    
    @property
    def metrics(self) -> ProcessMetrics:
        """Get the collected metrics."""
        if self._metrics is None:
            raise ValueError("No metrics collected. Call collect() first.")
        return self._metrics
    
    def collect(
        self,
        df: pd.DataFrame,
        net: PetriNet,
        initial_marking: Marking,
        final_marking: Marking,
        compute_fitness: bool = True,
        compute_precision: bool = True,
    ) -> ProcessMetrics:
        """
        Collect all process metrics.
        
        Args:
            df: Event log DataFrame
            net: Petri net
            initial_marking: Initial marking
            final_marking: Final marking
            compute_fitness: Whether to compute fitness
            compute_precision: Whether to compute precision
            
        Returns:
            ProcessMetrics with all computed metrics
        """
        print_stage(4, "COMPUTING PROCESS METRICS")
        
        # Create base metrics object
        self._metrics = ProcessMetrics(
            num_cases=df['case:concept:name'].nunique(),
            num_events=len(df),
            num_activities=df['concept:name'].nunique(),
            num_places=len(net.places),
            num_transitions=len(net.transitions),
            num_arcs=len(net.arcs),
        )
        
        # Compute fitness
        if compute_fitness:
            fitness_result = self._fitness_evaluator.evaluate(
                df, net, initial_marking, final_marking
            )
            self._metrics.fitness = fitness_result.fitness
            self._metrics.fitness_details = fitness_result.to_dict()
        
        # Compute precision
        if compute_precision:
            precision_result = self._precision_evaluator.evaluate(
                df, net, initial_marking, final_marking
            )
            self._metrics.precision = precision_result.precision
            self._metrics.precision_details = precision_result.to_dict()
        
        # Calculate F-score
        if self._metrics.fitness and self._metrics.precision:
            self._metrics.f_score = calculate_f_score(
                self._metrics.fitness,
                self._metrics.precision
            )
        
        self._print_summary()
        
        return self._metrics
    
    def _print_summary(self) -> None:
        """Print a summary of all metrics."""
        m = self._metrics
        print_success("Metrics computation completed!")
        
        print("\n--- Structure ---")
        print_info("Places", m.num_places)
        print_info("Transitions", m.num_transitions)
        print_info("Arcs", m.num_arcs)
        
        print("\n--- Quality ---")
        if m.fitness is not None:
            print_info("Fitness", f"{m.fitness:.4f}")
        if m.precision is not None:
            print_info("Precision", f"{m.precision:.4f}")
        if m.f_score is not None:
            print_info("F-Score", f"{m.f_score:.4f}")