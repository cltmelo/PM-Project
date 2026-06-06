"""
Metrics calculation and comparison.

Calculates aggregate metrics and compares algorithms.
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

from ..parser.pnml_parser import PNMLParser, PetriNetStructure
from ..parser.json_parser import JSONMetricsParser, AlgorithmMetrics
from ..runner.detector import OutputDetector, AlgorithmOutput
from ..utils.logging_utils import print_header, print_info, print_success, print_stage
from ..utils.file_utils import ensure_dir


@dataclass
class AlgorithmResult:
    """Combined result for a single algorithm."""
    name: str
    output: AlgorithmOutput
    structure: PetriNetStructure = None
    metrics: AlgorithmMetrics = None
    
    @property
    def is_complete(self) -> bool:
        """Check if all data is available."""
        return self.structure is not None or self.metrics is not None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "structure": self.structure.to_dict() if self.structure else {},
            "metrics": self.metrics.to_dict() if self.metrics else {},
        }


@dataclass
class ComparisonResult:
    """Result of comparing all algorithms."""
    results: Dict[str, AlgorithmResult] = field(default_factory=dict)
    dataframe: pd.DataFrame = None
    
    @property
    def best_fitness(self) -> str:
        """Get algorithm with best fitness."""
        if self.dataframe is None:
            return ""
        return self.dataframe.loc[self.dataframe['fitness'].idxmax(), 'name']
    
    @property
    def best_precision(self) -> str:
        """Get algorithm with best precision."""
        if self.dataframe is None:
            return ""
        return self.dataframe.loc[self.dataframe['precision'].idxmax(), 'name']
    
    @property
    def simplest_model(self) -> str:
        """Get algorithm with simplest model."""
        if self.dataframe is None:
            return ""
        return self.dataframe.loc[self.dataframe['num_places'].idxmin(), 'name']


class MetricsCalculator:
    """
    Calculates and compares metrics across algorithms.
    
    Aggregates data from all available outputs and produces
    a comparison DataFrame.
    
    Example:
        calculator = MetricsCalculator()
        result = calculator.calculate(outputs)
    """
    
    def __init__(self):
        """Initialize the metrics calculator."""
        self._result: Optional[ComparisonResult] = None
        self._pnml_parser = PNMLParser()
        self._json_parser = JSONMetricsParser()
    
    @property
    def result(self) -> Optional[ComparisonResult]:
        """Get the comparison result."""
        return self._result
    
    def calculate(
        self,
        outputs: Dict[str, AlgorithmOutput]
    ) -> ComparisonResult:
        """
        Calculate metrics for all algorithms.
        
        Args:
            outputs: Dictionary of detected outputs
            
        Returns:
            ComparisonResult with all aggregated data
        """
        print_stage(2, "CALCULATING METRICS")
        
        results = {}
        
        for name, output in outputs.items():
            result = self._calculate_single(output, name)
            if result:
                results[name] = result
        
        # Create DataFrame
        df = self._create_dataframe(results)
        
        self._result = ComparisonResult(
            results=results,
            dataframe=df,
        )
        
        self._print_summary(df)
        
        return self._result
    
    def _calculate_single(
        self,
        output: AlgorithmOutput,
        name: str
    ) -> Optional[AlgorithmResult]:
        """Calculate metrics for a single algorithm."""
        result = AlgorithmResult(
            name=name,
            output=output,
        )
        
        # Parse PNML
        if output.pnml_path:
            try:
                result.structure = self._pnml_parser.parse(output.pnml_path)
            except Exception:
                pass
        
        # Parse JSON
        if output.json_path:
            try:
                result.metrics = self._json_parser.parse(output.json_path, name)
            except Exception:
                pass
        
        return result
    
    def _create_dataframe(
        self,
        results: Dict[str, AlgorithmResult]
    ) -> pd.DataFrame:
        """Create a comparison DataFrame."""
        rows = []
        
        for name, result in results.items():
            row = {"name": name}
            
            # Add structure metrics
            if result.structure:
                row["num_places"] = result.structure.num_places
                row["num_transitions"] = result.structure.num_transitions
                row["num_arcs"] = result.structure.num_arcs
                row["complexity"] = result.structure.complexity
            else:
                row["num_places"] = 0
                row["num_transitions"] = 0
                row["num_arcs"] = 0
                row["complexity"] = 0.0
            
            # Add quality metrics
            if result.metrics:
                row["fitness"] = result.metrics.fitness
                row["precision"] = result.metrics.precision
                row["f_score"] = result.metrics.f_score
                row["num_cases"] = result.metrics.num_cases
                row["num_events"] = result.metrics.num_events
            else:
                row["fitness"] = 0.0
                row["precision"] = 0.0
                row["f_score"] = 0.0
                row["num_cases"] = 0
                row["num_events"] = 0
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        return df
    
    def _print_summary(self, df: pd.DataFrame) -> None:
        """Print a summary of the comparison."""
        if df.empty:
            print_warning("No data to compare")
            return
        
        print_success(f"Compared {len(df)} algorithms")
        
        if "fitness" in df.columns and df["fitness"].max() > 0:
            print_info("Best fitness", df.loc[df['fitness'].idxmax(), 'name'])
        if "precision" in df.columns and df["precision"].max() > 0:
            print_info("Best precision", df.loc[df['precision'].idxmax(), 'name'])
        if "num_places" in df.columns:
            print_info("Simplest model", df.loc[df['num_places'].idxmin(), 'name'])