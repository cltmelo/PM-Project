"""
PNG visualization export.
"""

import os
from typing import Optional

import pm4py
from pm4py.objects.petri.net import PetriNet

from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success, print_warning


class PNGExporter:
    """
    Exports Petri nets to PNG images.
    
    Creates visual representations of Petri nets showing
    places, transitions, and arcs.
    
    Example:
        exporter = PNGExporter()
        exporter.export(net, "output/model.png")
    """
    
    def __init__(self):
        """Initialize the PNG exporter."""
        self._last_export_path: Optional[str] = None
    
    @property
    def last_export_path(self) -> Optional[str]:
        """Get the path of the last export."""
        return self._last_export_path
    
    def export(
        self,
        net: PetriNet,
        output_path: str,
        dpi: int = 150,
    ) -> str:
        """
        Export a Petri net to PNG image.
        
        Args:
            net: Petri net to visualize
            output_path: Path for the output image
            dpi: Resolution of the output image
            
        Returns:
            Path to the exported file
        """
        print_header("EXPORTING PNG VISUALIZATION")
        
        # Ensure directory exists
        ensure_dir(os.path.dirname(output_path))
        
        print(f"⏳ Generating visualization...")
        
        try:
            # Use pm4py's built-in visualization
            pm4py.visualization_petri_net(
                net,
                variant=pm4py.Variants.WO_DECORATION,
                format="png"
            ).save(output_path)
            
            self._last_export_path = output_path
            print_success(f"PNG saved: {output_path}")
            
        except Exception as e:
            print_warning(f"Visualization failed: {e}")
            # Create a fallback text-based visualization
            self._create_fallback(net, output_path, dpi)
        
        return self._last_export_path
    
    def _create_fallback(
        self,
        net: PetriNet,
        output_path: str,
        dpi: int,
    ) -> None:
        """Create a fallback text-based visualization."""
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.set_aspect('equal')
        
        # Draw simple representation
        ax.text(0, 0.8, "Petri Net", fontsize=16, ha='center', fontweight='bold')
        ax.text(0, 0.5, f"Places: {len(net.places)}", fontsize=12, ha='center')
        ax.text(0, 0.2, f"Transitions: {len(net.transitions)}", fontsize=12, ha='center')
        ax.text(0, -0.1, f"Arcs: {len(net.arcs)}", fontsize=12, ha='center')
        
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        self._last_export_path = output_path
        print_success(f"Fallback visualization saved: {output_path}")