"""
JSON metrics export.
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime

from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success
from ..utils.metrics_utils import format_metrics_for_json


class JSONExporter:
    """
    Exports metrics to JSON format.
    
    Creates machine-readable JSON files with all
    computed metrics and model information.
    
    Example:
        exporter = JSONExporter()
        exporter.export(metrics, "output/metrics.json")
    """
    
    def __init__(self):
        """Initialize the JSON exporter."""
        self._last_export_path: Optional[str] = None
    
    @property
    def last_export_path(self) -> Optional[str]:
        """Get the path of the last export."""
        return self._last_export_path
    
    def export(
        self,
        metrics: Dict[str, Any],
        output_path: str,
        indent: int = 2,
    ) -> str:
        """
        Export metrics to JSON format.
        
        Args:
            metrics: Metrics dictionary to export
            output_path: Path for the output file
            indent: JSON indentation level
            
        Returns:
            Path to the exported file
        """
        print_header("EXPORTING JSON METRICS")
        
        # Ensure directory exists
        ensure_dir(os.path.dirname(output_path))
        
        print(f"⏳ Exporting to: {output_path}")
        
        # Format metrics for JSON serialization
        formatted_metrics = format_metrics_for_json(metrics)
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(formatted_metrics, f, indent=indent)
        
        self._last_export_path = output_path
        print_success(f"JSON saved: {output_path}")
        
        return output_path