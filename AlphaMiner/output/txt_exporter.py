"""
Text summary export.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime

import pandas as pd

import pm4py
from pm4py import PetriNet

from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success


class TXTExporter:
    """
    Exports process discovery results to text format.
    
    Creates human-readable summary files with all
    important information about the discovery run.
    
    Example:
        exporter = TXTExporter()
        exporter.export(df, net, metrics, "output/summary.txt")
    """
    
    def __init__(self):
        """Initialize the TXT exporter."""
        self._last_export_path: Optional[str] = None
    
    @property
    def last_export_path(self) -> Optional[str]:
        """Get the path of the last export."""
        return self._last_export_path
    
    def export(
        self,
        df: pd.DataFrame,
        net: PetriNet,
        metrics: Dict[str, Any],
        output_path: str,
    ) -> str:
        """
        Export a text summary of the discovery results.
        
        Args:
            df: Event log DataFrame
            net: Petri net
            metrics: Computed metrics dictionary
            output_path: Path for the output file
            
        Returns:
            Path to the exported file
        """
        print_header("EXPORTING TEXT SUMMARY")
        
        # Ensure directory exists
        ensure_dir(os.path.dirname(output_path))
        
        print(f"⏳ Exporting to: {output_path}")
        
        # Build summary content
        lines = self._build_summary(df, net, metrics)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        
        self._last_export_path = output_path
        print_success(f"Text summary saved: {output_path}")
        
        return output_path
    
    def _build_summary(
        self,
        df: pd.DataFrame,
        net: PetriNet,
        metrics: Dict[str, Any],
    ) -> list:
        """Build the summary content lines."""
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("ALPHA MINER - PROCESS DISCOVERY OUTPUT".center(70))
        lines.append("=" * 70)
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Event log summary
        lines.append("EVENT LOG SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total cases: {df['case:concept:name'].nunique():,}")
        lines.append(f"Total events: {len(df):,}")
        lines.append(f"Unique activities: {df['concept:name'].nunique()}")
        lines.append("")
        
        # Model structure
        lines.append("MODEL STRUCTURE")
        lines.append("-" * 40)
        lines.append(f"Places: {len(net.places)}")
        lines.append(f"Transitions: {len(net.transitions)}")
        lines.append(f"Arcs: {len(net.arcs)}")
        lines.append("")
        
        # Quality metrics
        lines.append("QUALITY METRICS")
        lines.append("-" * 40)
        
        if "quality_metrics" in metrics:
            qm = metrics["quality_metrics"]
            if "fitness" in qm and qm["fitness"].get("token_replay"):
                lines.append(f"Fitness: {qm['fitness']['token_replay']:.4f}")
            if "precision" in qm and qm["precision"].get("value"):
                lines.append(f"Precision: {qm['precision']['value']:.4f}")
            if "f_score" in qm and qm["f_score"].get("value"):
                lines.append(f"F-Score: {qm['f_score']['value']:.4f}")
        
        lines.append("")
        
        # Output files
        lines.append("OUTPUT FILES")
        lines.append("-" * 40)
        lines.append(f"PNML: AlphaMiner/output/alpha_miner.pnml")
        lines.append(f"PNG: AlphaMiner/output/alpha_miner.png")
        lines.append(f"JSON: AlphaMiner/output/alpha_miner_metrics.json")
        lines.append("")
        lines.append("=" * 70)
        
        return lines