"""
JSON metrics parser.

Parses metrics JSON files from different algorithm formats to extract
standardized quality metrics (fitness, precision, simplicity, overall score).
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AlgorithmMetrics:
    """Container for algorithm performance metrics."""
    algorithm_name: str = ""
    timestamp: str = ""
    
    # Event log stats
    num_cases: int = 0
    num_events: int = 0
    num_activities: int = 0
    
    # PRIMARY METRICS (what we care about)
    fitness: float = 0.0
    precision: float = 0.0
    simplicity: float = 0.0
    #generalization: float = 0.0  # ADD THIS LINE
    overall_score: float = 0.0
    f_score: float = 0.0
    
    # Model structure (optional, not primary)
    num_places: int = 0
    num_transitions: int = 0
    num_arcs: int = 0
    
    # Raw data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "algorithm_name": self.algorithm_name,
            "timestamp": self.timestamp,
            "event_log": {
                "num_cases": self.num_cases,
                "num_events": self.num_events,
                "num_activities": self.num_activities,
            },
            "quality_metrics": {
                "fitness": {
                    "value": round(self.fitness, 4),
                    "description": "Fitness score (1.0 = perfect)"
                },
                "precision": {
                    "value": round(self.precision, 4),
                    "description": "Precision score (1.0 = no extra behavior)"
                },
                "simplicity": {
                    "value": round(self.simplicity, 4),
                    "description": "Simplicity score (1.0 = simplest)"
                },
                "overall_score": {
                    "value": round(self.overall_score, 4),
                    "description": "Overall score (weighted combination)"
                },
                "f_score": {
                    "value": round(self.f_score, 4),
                    "description": "Harmonic mean of fitness and precision"
                },
            },
            "model_structure": {
                "num_places": self.num_places,
                "num_transitions": self.num_transitions,
                "num_arcs": self.num_arcs,
            },
        }


class JSONMetricsParser:
    """
    Parses metrics JSON files from different algorithm formats.
    
    Handles these formats:
    - GeneticMiner: Flat format with fitness_score, precision_score, etc.
    - InductiveMiner: Mixed format with nested quality_metrics
    - AlphaMiner: pm4py style with quality_metrics.fitness.token_replay
    - SplitMiner: Similar to GeneticMiner
    
    Example:
        parser = JSONMetricsParser()
        metrics = parser.parse("path/to/metrics.json")
    """
    
    def __init__(self):
        """Initialize the JSON metrics parser."""
        self._metrics: Optional[AlgorithmMetrics] = None
    
    @property
    def metrics(self) -> Optional[AlgorithmMetrics]:
        """Get the parsed metrics."""
        return self._metrics
    
    def parse(
        self,
        json_path: str,
        algorithm_name: str = ""
    ) -> AlgorithmMetrics:
        """
        Parse a metrics JSON file.
        
        Args:
            json_path: Path to the JSON file
            algorithm_name: Name to assign to this algorithm
            
        Returns:
            AlgorithmMetrics with extracted values
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        if not json_path or not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Create metrics object
        metrics = AlgorithmMetrics(
            algorithm_name=algorithm_name,
            raw_data=data,
        )
        
        # Try to detect format and parse
        metrics = self._parse_by_format(data, metrics)
        
        # Calculate missing metrics
        metrics = self._calculate_derived_metrics(metrics)
        
        self._metrics = metrics
        return metrics
    
    def _parse_by_format(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """Parse based on detected format."""
        
        # Nested quality metrics need format-specific handling before the flat
        # score checks because InductiveMiner also writes top-level scores.
        if "quality_metrics" in data:
            quality_metrics = data.get("quality_metrics", {})
            if (
                "fitness_details" in quality_metrics
                or "precision_details" in quality_metrics
                or data.get("algorithm", "").lower() == "inductive miner"
            ):
                metrics = self._parse_inductive_format(data, metrics)
            else:
                metrics = self._parse_alpha_format(data, metrics)
        # Check for GeneticMiner/SplitMiner flat format
        elif "fitness_score" in data:
            metrics = self._parse_genetic_format(data, metrics)
        # Check for SplitMiner format (similar to genetic)
        elif "overall_score" in data:
            metrics = self._parse_split_format(data, metrics)
        else:
            # Generic fallback
            metrics = self._parse_generic(data, metrics)
        
        return metrics

    def _as_float(self, value: Any, default: float = 0.0) -> float:
        """Extract a numeric metric value from scalars or common wrappers."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict):
            for key in ("value", "fitness", "precision", "token_replay", "score"):
                if key in value:
                    return self._as_float(value[key], default)
        return default
    
    def _parse_genetic_format(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """
        Parse GeneticMiner format.
        
        Example:
        {
            "overall_score": 0.87224,
            "fitness_score": 0.791866,
            "precision_score": 1.0,
            "simplicity_score": 0.902174,
            ...
        }
        """
        metrics.algorithm_name = "Genetic Miner"
        metrics.fitness = self._as_float(data.get("fitness_score", 0.0))
        metrics.precision = self._as_float(data.get("precision_score", 0.0))
        metrics.simplicity = self._as_float(data.get("simplicity_score", 0.0))
        #metrics.generalization = data.get("generalization_score", 0.0)  # ADD THIS LINE
        metrics.overall_score = self._as_float(data.get("overall_score", 0.0))
        metrics.f_score = self._as_float(data.get("f_score", 0.0))
        
        # Event log stats
        metrics.num_activities = data.get("num_activities", 0)
        metrics.num_cases = data.get("num_cases", data.get("total_traces", 0))
        
        # Timestamp
        metrics.timestamp = data.get("timestamp", datetime.now().isoformat())
        
        return metrics
    
    def _parse_inductive_format(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """
        Parse InductiveMiner format.
        
        Example:
        {
            "overall_score": 0.5044,
            "fitness_score": 0.5014,
            "simplicity_score": 0.013,
            "quality_metrics": {
                "fitness_details": {"fitness": 0.5014},
                "precision_details": {"precision": 1.0},
                "f_score": 0.6678
            },
            "model_structure": {...}
        }
        """
        metrics.algorithm_name = "Inductive Miner"
        
        # Primary metrics at top level
        metrics.fitness = self._as_float(data.get("fitness_score", 0.0))
        metrics.simplicity = self._as_float(data.get("simplicity_score", 0.0))
        metrics.overall_score = self._as_float(data.get("overall_score", 0.0))
        
        # Nested quality_metrics
        if "quality_metrics" in data:
            qm = data["quality_metrics"]
            
            # Fitness
            if "fitness_details" in qm:
                metrics.fitness = self._as_float(
                    qm["fitness_details"].get("fitness", metrics.fitness),
                    metrics.fitness
                )
            
            # Precision
            if "precision_details" in qm:
                metrics.precision = self._as_float(
                    qm["precision_details"].get("precision", 0.0)
                )
            
            # F-score
            metrics.f_score = self._as_float(qm.get("f_score", 0.0))
        
        # Event log
        if "event_log" in data:
            el = data["event_log"]
            metrics.num_cases = el.get("num_cases", 0)
            metrics.num_events = el.get("num_events", 0)
            metrics.num_activities = el.get("num_activities", 0)
        
        # Model structure (optional)
        if "model_structure" in data:
            ms = data["model_structure"]
            metrics.num_places = ms.get("num_places", 0)
            metrics.num_transitions = ms.get("num_transitions", 0)
            metrics.num_arcs = ms.get("num_arcs", 0)
        
        metrics.timestamp = data.get("timestamp", datetime.now().isoformat())
        
        return metrics
    
    def _parse_alpha_format(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """
        Parse AlphaMiner/pm4py format.
        
        Example:
        {
            "quality_metrics": {
                "fitness": {"token_replay": 0.3826},
                "precision": {"value": 0.0904},
                "f_score": {"value": 0.1462}
            },
            "model_structure": {...}
        }
        """
        metrics.algorithm_name = data.get("algorithm", "Alpha Miner")
        
        # Nested quality_metrics
        if "quality_metrics" in data:
            qm = data["quality_metrics"]
            
            # Fitness - try multiple field names
            fitness_data = qm.get("fitness", {})
            metrics.fitness = self._as_float(fitness_data)
            
            # Precision - try multiple field names
            precision_data = qm.get("precision", {})
            metrics.precision = self._as_float(precision_data)
            
            # F-score
            fscore_data = qm.get("f_score", {})
            metrics.f_score = self._as_float(fscore_data)
        
        # Alpha's metrics JSON does not include simplicity; Compare can enrich
        # it from PNML structure after parsing.
        metrics.simplicity = self._as_float(data.get("simplicity_score", 0.0))
        
        # Calculate overall from available metrics
        metrics.overall_score = self._as_float(data.get("overall_score", 0.0))
        
        # Event log
        if "event_log" in data:
            el = data["event_log"]
            metrics.num_cases = el.get("num_cases", 0)
            metrics.num_events = el.get("num_events", 0)
            metrics.num_activities = el.get("num_activities", 0)
        
        # Model structure (optional)
        if "model_structure" in data:
            ms = data["model_structure"]
            metrics.num_places = ms.get("num_places", 0)
            metrics.num_transitions = ms.get("num_transitions", 0)
            metrics.num_arcs = ms.get("num_arcs", 0)
        
        metrics.timestamp = data.get("timestamp", datetime.now().isoformat())
        
        return metrics
    
    def _parse_split_format(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """
        Parse SplitMiner format (similar to GeneticMiner).
        """
        metrics.algorithm_name = "Split Miner"
        metrics.fitness = self._as_float(data.get("fitness_score", data.get("fitness", 0.0)))
        metrics.precision = self._as_float(data.get("precision_score", data.get("precision", 0.0)))
        metrics.simplicity = self._as_float(data.get("simplicity_score", 0.0))
        metrics.overall_score = self._as_float(data.get("overall_score", 0.0))
        metrics.f_score = self._as_float(data.get("f_score", 0.0))
        
        metrics.timestamp = data.get("timestamp", datetime.now().isoformat())
        
        return metrics
    
    def _parse_generic(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """
        Generic fallback parser for unknown formats.
        """
        # Try to find any fitness-related field
        metrics.fitness = self._as_float(
            data.get("fitness") or
            data.get("fitness_score") or
            data.get("log_fitness") or
            0.0
        )
        
        # Try to find any precision-related field
        metrics.precision = self._as_float(
            data.get("precision") or
            data.get("precision_score") or
            data.get("precision_value") or
            0.0
        )
        
        # Try to find any simplicity-related field
        metrics.simplicity = self._as_float(
            data.get("simplicity") or
            data.get("simplicity_score") or
            0.0
        )
        
        # Try to find any overall-related field
        metrics.overall_score = self._as_float(
            data.get("overall") or
            data.get("overall_score") or
            0.0
        )
        
        metrics.timestamp = datetime.now().isoformat()
        
        return metrics
    
    def _calculate_derived_metrics(
        self,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """Calculate derived metrics if missing."""
        
        # Calculate F-score from fitness and precision
        if metrics.f_score == 0.0 and metrics.fitness > 0 and metrics.precision > 0:
            metrics.f_score = 2 * (metrics.fitness * metrics.precision) / (metrics.fitness + metrics.precision)
        
        # Calculate overall score if missing
        if metrics.overall_score == 0.0 and metrics.fitness > 0:
            weights = {"fitness": 0.4, "precision": 0.3, "simplicity": 0.3}
            metrics.overall_score = (
                metrics.fitness * weights["fitness"] +
                metrics.precision * weights["precision"] +
                metrics.simplicity * weights["simplicity"]
            )
        
        return metrics
