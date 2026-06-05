"""
Utilities for formatting and processing metrics.
"""

from typing import Any, Dict, Optional
from datetime import datetime


def format_metrics_for_json(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format metrics dictionary for JSON serialization.
    
    Handles non-serializable types by converting them to strings.
    
    Args:
        metrics: Raw metrics dictionary
        
    Returns:
        JSON-serializable metrics dictionary
    """
    formatted = {}
    
    for key, value in metrics.items():
        if isinstance(value, dict):
            formatted[key] = format_metrics_for_json(value)
        elif isinstance(value, (datetime,)):
            formatted[key] = value.isoformat()
        elif isinstance(value, float):
            # Round floats to 4 decimal places
            formatted[key] = round(value, 4)
        elif value is None:
            formatted[key] = None
        else:
            try:
                # Test if serializable
                str(value)
                formatted[key] = value
            except:
                formatted[key] = str(value)
    
    return formatted


def calculate_f_score(fitness: float, precision: float) -> Optional[float]:
    """
    Calculate F-score (harmonic mean of fitness and precision).
    
    Args:
        fitness: Fitness value (0-1)
        precision: Precision value (0-1)
        
    Returns:
        F-score or None if calculation fails
    """
    if fitness and precision and (fitness + precision) > 0:
        return 2 * (fitness * precision) / (fitness + precision)
    return None


def format_percentage(value: float) -> str:
    """Format a decimal value as a percentage string."""
    return f"{value * 100:.2f}%"