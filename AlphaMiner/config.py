"""
Configuration settings for the Alpha Miner pipeline.

This module centralizes all configuration values, making it easy to
modify settings without changing the core logic.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class Config:
    """Configuration for the Alpha Miner pipeline."""
    
    # =========================================================================
    # Paths
    # =========================================================================
    log_path: str = "BPI Challenge 2017_1_all/BPI Challenge 2017.xes.gz"
    output_dir: str = "AlphaMiner/output"
    
    # =========================================================================
    # Preprocessing
    # =========================================================================
    noise_threshold: float = 0.0  # 0 = no filtering
    min_case_duration_hours: Optional[float] = None
    filter_activities_below: Optional[int] = None
    
    # =========================================================================
    # Alpha Miner Settings
    # =========================================================================
    variant: str = "alpha"  # alpha, alpha_plus, alpha_star
    include_self_loops: bool = True
    
    # =========================================================================
    # Visualization
    # =========================================================================
    png_dpi: int = 150
    png_format: str = "png"
    
    # =========================================================================
    # Metrics
    # =========================================================================
    compute_fitness: bool = True
    compute_precision: bool = True
    
    # =========================================================================
    # Logging
    # =========================================================================
    verbose: bool = True
    show_headers: bool = True
    indent_spaces: int = 4


# Global configuration instance
CONFIG = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return CONFIG


def update_config(**kwargs) -> Config:
    """Update configuration values."""
    global CONFIG
    for key, value in kwargs.items():
        if hasattr(CONFIG, key):
            setattr(CONFIG, key, value)
    return CONFIG