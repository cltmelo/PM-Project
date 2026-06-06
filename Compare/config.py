"""
Configuration for the comparison framework.

Centralizes all settings for comparing process mining algorithms.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class AlgorithmType(Enum):
    """Enumeration of supported process mining algorithms."""
    GENETIC = "GeneticMiner"
    ALPHA = "AlphaMiner"
    INDUCTIVE = "InductiveMiner"
    SPLIT = "SplitMiner"


@dataclass
class AlgorithmConfig:
    """Configuration for a single algorithm."""
    name: str
    type: AlgorithmType
    module_name: str
    output_dir: str
    main_script: str
    enabled: bool = True


@dataclass
class CompareConfig:
    """Configuration for the comparison framework."""
    
    # Base directory
    base_dir: str = "."
    
    # Event log
    event_log_path: str = "BPI Challenge 2017_1_all/BPI Challenge 2017.xes.gz"
    
    # Algorithms to compare
    algorithms: List[AlgorithmConfig] = field(default_factory=list)
    
    # Output settings
    output_dir: str = "compare/output"
    generate_charts: bool = True
    generate_report: bool = True
    
    # Chart settings
    chart_dpi: int = 150
    chart_style: str = "seaborn-v0_8-darkgrid"
    
    # Thresholds
    min_fitness_threshold: float = 0.8
    min_precision_threshold: float = 0.6


# Default algorithm configurations
DEFAULT_ALGORITHMS = [
    AlgorithmConfig(
        name="Genetic Miner",
        type=AlgorithmType.GENETIC,
        module_name="genetic_miner",
        output_dir="GeneticMiner/Output",
        main_script="GeneticMiner/genetic_miner.py",
        enabled=True,
    ),
    AlgorithmConfig(
        name="Alpha Miner",
        type=AlgorithmType.ALPHA,
        module_name="alpha_miner",
        output_dir="AlphaMiner/output",
        main_script="AlphaMiner/main.py",
        enabled=True,
    ),
    AlgorithmConfig(
        name="Inductive Miner",
        type=AlgorithmType.INDUCTIVE,
        module_name="inductive_miner",
        output_dir="InductiveMiner/Output",
        main_script="InductiveMiner/inductive_miner.py",
        enabled=True,
    ),
    AlgorithmConfig(
        name="Split Miner",
        type=AlgorithmType.SPLIT,
        module_name="split_miner",
        output_dir="SplitMiner/Output",
        main_script="SplitMiner/split_miner.py",
        enabled=True,
    ),
]


# Global configuration
COMPARE_CONFIG = CompareConfig(
    algorithms=DEFAULT_ALGORITHMS
)


def get_compare_config() -> CompareConfig:
    """Get the global comparison configuration."""
    return COMPARE_CONFIG


def get_algorithm_config(algo_type: AlgorithmType) -> Optional[AlgorithmConfig]:
    """Get configuration for a specific algorithm type."""
    for algo in COMPARE_CONFIG.algorithms:
        if algo.type == algo_type:
            return algo
    return None


def get_enabled_algorithms() -> List[AlgorithmConfig]:
    """Get list of enabled algorithms."""
    return [a for a in COMPARE_CONFIG.algorithms if a.enabled]