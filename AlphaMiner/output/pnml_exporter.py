"""
PNML (Petri Net Markup Language) export.
"""

import os
from typing import Optional

import pm4py
from pm4py import PetriNet, Marking

from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success


class PNMLExporter:
    """
    Exports Petri nets to PNML format.
    
    PNML is the standard XML-based format for exchanging
    Petri nets between tools.
    
    Example:
        exporter = PNMLExporter()
        exporter.export(net, initial_marking, final_marking, "output/model.pnml")
    """
    
    def __init__(self):
        """Initialize the PNML exporter."""
        self._last_export_path: Optional[str] = None
    
    @property
    def last_export_path(self) -> Optional[str]:
        """Get the path of the last export."""
        return self._last_export_path
    
    def export(
        self,
        net: PetriNet,
        initial_marking: Marking,
        final_marking: Marking,
        output_path: str,
    ) -> str:
        """
        Export a Petri net to PNML format.
        
        Args:
            net: Petri net to export
            initial_marking: Initial marking
            final_marking: Final marking
            output_path: Path for the output file
            
        Returns:
            Path to the exported file
        """
        print_header("EXPORTING PNML")
        
        # Ensure directory exists
        ensure_dir(os.path.dirname(output_path))
        
        print(f"⏳ Exporting to: {output_path}")
        
        # Export using pm4py
        pm4py.write_pnml(net, initial_marking, final_marking, output_path)
        
        self._last_export_path = output_path
        print_success(f"PNML saved: {output_path}")
        
        return output_path