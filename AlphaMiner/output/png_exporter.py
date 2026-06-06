"""
PNG visualization export.
"""

import os
import pm4py

from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success, print_warning


class PNGExporter:
    """Exports Petri nets to PNG images."""
    
    def __init__(self):
        self._last_export_path = None
    
    @property
    def last_export_path(self):
        return self._last_export_path
    
    def export(
        self,
        net,
        output_path: str,
        initial_marking=None,
        final_marking=None,
        pnml_path: str = None,
        dpi: int = 150,
    ) -> str:
        """Export a Petri net to PNG image by reading from PNML file."""
        print_header("EXPORTING PNG VISUALIZATION")
        
        ensure_dir(os.path.dirname(output_path))
        print("⏳ Generating visualization...")
        
        # Read net from PNML file (use provided path or create from output_path)
        if pnml_path is None:
            pnml_path = output_path.replace('.png', '.pnml')
        
        if not os.path.exists(pnml_path):
            raise FileNotFoundError(f"PNML file not found: {pnml_path}")
        
        net, im, fm = pm4py.read_pnml(pnml_path)
        
        # Save visualization directly - that's it!
        pm4py.save_vis_petri_net(net, im, fm, output_path)
        
        self._last_export_path = output_path
        print_success(f"PNG saved: {output_path}")
        
        return self._last_export_path