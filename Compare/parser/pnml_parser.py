"""
PNML (Petri Net Markup Language) parser.

Parses PNML files to extract model structure metrics.
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from ..utils.logging_utils import print_header, print_info, print_success


@dataclass
class PetriNetStructure:
    """Container for Petri net structure metrics."""
    name: str = ""
    num_places: int = 0
    num_transitions: int = 0
    num_arcs: int = 0
    num_silent_transitions: int = 0
    places: Set[str] = field(default_factory=set)
    transitions: Set[str] = field(default_factory=set)
    initial_place: str = ""
    final_place: str = ""
    
    @property
    def total_elements(self) -> int:
        """Get total number of elements."""
        return self.num_places + self.num_transitions + self.num_arcs
    
    @property
    def complexity(self) -> float:
        """Calculate a simple complexity score."""
        return self.num_arcs / max(self.num_places + self.num_transitions, 1)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "num_places": self.num_places,
            "num_transitions": self.num_transitions,
            "num_arcs": self.num_arcs,
            "num_silent_transitions": self.num_silent_transitions,
            "total_elements": self.total_elements,
            "complexity": round(self.complexity, 2),
        }


class PNMLParser:
    """
    Parses PNML files to extract structure metrics.
    
    Extracts information about:
    - Number of places, transitions, and arcs
    - Silent transitions (tau transitions)
    - Initial and final markings
    
    Example:
        parser = PNMLParser()
        structure = parser.parse("path/to/model.pnml")
    """
    
    # PNML namespace
    PNML_NS = "http://www.pnml.org/version-2009/grammar/pnmlcoremodel"
    
    def __init__(self):
        """Initialize the PNML parser."""
        self._structure: Optional[PetriNetStructure] = None
    
    @property
    def structure(self) -> Optional[PetriNetStructure]:
        """Get the parsed structure."""
        return self._structure
    
    def parse(self, pnml_path: str) -> PetriNetStructure:
        """
        Parse a PNML file.
        
        Args:
            pnml_path: Path to the PNML file
            
        Returns:
            PetriNetStructure with extracted metrics
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is not valid PNML
        """
        if not pnml_path or not os.path.exists(pnml_path):
            raise FileNotFoundError(f"PNML file not found: {pnml_path}")
        
        # Parse XML
        tree = ET.parse(pnml_path)
        root = tree.getroot()
        
        # Extract structure
        structure = PetriNetStructure(
            name=self._get_net_name(root)
        )
        
        # Find the page element when present. Some exporters write places,
        # transitions, and arcs directly under the net element.
        page = root.find(f".//{{{self.PNML_NS}}}page")
        if page is None:
            page = root.find(".//page")  # Try without namespace
        
        structure = self._parse_page(page or root, structure)
        
        self._structure = structure
        return structure
    
    def _get_net_name(self, root: ET.Element) -> str:
        """Get the net name from the root element."""
        name_elem = root.find(f".//{{{self.PNML_NS}}}name/{{{self.PNML_NS}}}text")
        if name_elem is None:
            name_elem = root.find(".//name/text")
        return name_elem.text if name_elem is not None else "Unknown"
    
    def _parse_page(
        self,
        page: ET.Element,
        structure: PetriNetStructure
    ) -> PetriNetStructure:
        """Parse a page element to extract places and transitions."""
        
        # Parse places
        for place in self._iter_by_local_name(page, "place"):
            place_id = place.get("id", "")
            structure.places.add(place_id)
            
            # Check if initial/final place
            if self._is_initial_place(place):
                structure.initial_place = place_id
            elif self._is_final_place(place):
                structure.final_place = place_id
        
        # Parse transitions
        for transition in self._iter_by_local_name(page, "transition"):
            trans_id = transition.get("id", "")
            structure.transitions.add(trans_id)
            
            # Check if silent transition
            if self._is_silent_transition(transition):
                structure.num_silent_transitions += 1
        
        # Parse arcs
        for arc in self._iter_by_local_name(page, "arc"):
            structure.num_arcs += 1
        
        # Update counts
        structure.num_places = len(structure.places)
        structure.num_transitions = len(structure.transitions)
        
        return structure

    def _iter_by_local_name(self, element: ET.Element, local_name: str):
        """Yield descendants with a tag name, ignoring XML namespaces."""
        for child in element.iter():
            if self._local_name(child.tag) == local_name:
                yield child

    def _local_name(self, tag: str) -> str:
        """Return the local portion of an XML tag."""
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag
    
    def _is_initial_place(self, place: ET.Element) -> bool:
        """Check if a place is an initial place."""
        return place.get("id", "").startswith("source")
    
    def _is_final_place(self, place: ET.Element) -> bool:
        """Check if a place is a final place."""
        return place.get("id", "").startswith("sink")
    
    def _is_silent_transition(self, transition: ET.Element) -> bool:
        """Check if a transition is a silent transition."""
        name_elem = None
        for child in transition.iter():
            if self._local_name(child.tag) == "text":
                name_elem = child
                break
        
        if name_elem is not None:
            return name_elem.text in ("tau", "silent", "t")
        
        return False
