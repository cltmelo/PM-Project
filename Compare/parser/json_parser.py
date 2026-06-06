"""
JSON metrics parser.

Parses metrics JSON files to extract algorithm performance data.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.logging_utils import print_header, print_info, print_success


@dataclass
class AlgorithmMetrics:
    """Container for algorithm performance metrics."""
    algorithm_name: str = ""
    timestamp: str = ""
    
    # Event log stats
    num_cases: int = 0
    num_events: int = 0
    num_activities: int = 0
    
    # Quality metrics
    fitness: float = 0.0
    precision: float = 0.0
    f_score: float = 0.0
    
    # Extended metrics (algorithm-specific)
    simplicity_score: float = 0.0
    generalization_score: float = 0.0
    
    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def quality_average(self) -> float:
        """Get average of quality metrics."""
        metrics = [m for m in [self.fitness, self.precision, self.f_score] if m > 0]
        return sum(metrics) / len(metrics) if metrics else 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "algorithm_name": self.algorithm_name,
            "fitness": round(self.fitness, 4),
            "precision": round(self.precision, 4),
            "f_score": round(self.f_score, 4),
            "simplicity_score": round(self.simplicity_score, 4),
            "num_cases": self.num_cases,
            "num_events": self.num_events,
            "num_activities": self.num_activities,
        }


class JSONMetricsParser:
    """
    Parses metrics JSON files.
    
    Handles various JSON formats from different algorithms
    and extracts standardized metrics.
    
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
        
        # Parse based on format
        metrics = AlgorithmMetrics(
            algorithm_name=algorithm_name,
            raw_data=data,
        )
        
        # Extract common fields
        metrics = self._extract_common_fields(data, metrics)
        
        # Extract algorithm-specific fields
        metrics = self._extract_extended_fields(data, metrics)
        
        self._metrics = metrics
        return metrics
    
    def _extract_common_fields(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """Extract commonly named fields."""
        
        # Event log stats
        if "event_log" in data:
            el = data["event_log"]
            metrics.num_cases = el.get("num_cases", 0)
            metrics.num_events = el.get("num_events", 0)
            metrics.num_activities = el.get("num_activities", 0)
        
        # Direct field access
        if metrics.num_cases == 0:
            metrics.num_cases = data.get("num_cases", 0)
        if metrics.num_events == 0:
            metrics.num_events = data.get("num_events", 0)
        
        # Quality metrics
        if "quality_metrics" in data:
            qm = data["quality_metrics"]
            metrics.fitness = qm.get("fitness", {}).get("token_replay", 0.0)
            metrics.precision = qm.get("precision", {}).get("value", 0.0)
            metrics.f_score = qm.get("f_score", {}).get("value", 0.0)
        
        # Direct field access (alternative names)
        if metrics.fitness == 0.0:
            metrics.fitness = data.get("fitness", data.get("fitness_score", 0.0))
        if metrics.precision == 0.0:
            metrics.precision = data.get("precision", data.get("precision_score", 0.0))
        
        # Overall score (F-score approximation)
        if metrics.f_score == 0.0:
            overall = data.get("overall_score", 0.0)
            if overall > 0:
                metrics.f_score = overall
        
        return metrics
    
    def _extract_extended_fields(
        self,
        data: Dict,
        metrics: AlgorithmMetrics
    ) -> AlgorithmMetrics:
        """Extract algorithm-specific extended fields."""
        
        metrics.simplicity_score = data.get("simplicity_score", 0.0)
        metrics.generalization_score = data.get("generalization_score", 0.0)
        
        # If no f_score, calculate from fitness and precision
        if metrics.f_score == 0.0 and metrics.fitness > 0 and metrics.precision > 0:
            metrics.f_score = 2 * (metrics.fitness * metrics.precision) / (metrics.fitness + metrics.precision)
        
        # Timestamp
        metrics.timestamp = data.get("timestamp", datetime.now().isoformat())
        
        return metrics