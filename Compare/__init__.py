"""
Process Mining Algorithm Comparison Framework

A framework for comparing the results of multiple process mining
algorithms (GeneticMiner, AlphaMiner, InductiveMiner, SplitMiner).

Author: University Process Mining Project
"""

from .config import COMPARE_CONFIG, AlgorithmConfig
from .runner.executor import AlgorithmExecutor
from .runner.detector import OutputDetector
from .parser.pnml_parser import PNMLParser
from .parser.json_parser import JSONMetricsParser
from .metrics.calculator import MetricsCalculator
from .visualization.charts import ComparisonCharts
from .visualization.table import ComparisonTable
from .report.generator import ReportGenerator

__version__ = "1.0.0"

__all__ = [
    "COMPARE_CONFIG",
    "AlgorithmConfig",
    "AlgorithmExecutor",
    "OutputDetector",
    "PNMLParser",
    "JSONMetricsParser",
    "MetricsCalculator",
    "ComparisonCharts",
    "ComparisonTable",
    "ReportGenerator",
]