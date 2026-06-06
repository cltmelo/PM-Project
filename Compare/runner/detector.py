"""
Output detection functionality.

Detects which algorithms have completed output available.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..config import AlgorithmConfig, AlgorithmType


class OutputStatus(Enum):
    """Status of algorithm output detection."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    NOT_FOUND = "not_found"


@dataclass
class AlgorithmOutput:
    """Container for detected algorithm output."""
    config: AlgorithmConfig
    status: OutputStatus
    pnml_path: str = ""
    png_path: str = ""
    json_path: str = ""
    txt_path: str = ""
    missing_files: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if all required outputs are present."""
        return self.status == OutputStatus.COMPLETE


class OutputDetector:
    """
    Detects algorithm outputs and their status.
    
    Checks for presence of required output files:
    - alpha_miner.pnml (or similar .pnml file)
    - alpha_miner.png (or similar .png file)
    - alpha_miner_metrics.json (or similar .json file)
    - run_output.txt (or similar .txt file)
    
    Example:
        detector = OutputDetector()
        results = detector.detect_all(algorithms)
    """
    
    REQUIRED_FILES = [
        "pnml",      # Petri net definition
        "png",       # Visualization
        "json",      # Metrics
        "txt",       # Text summary
    ]
    
    def __init__(self):
        """Initialize the output detector."""
        self._outputs: Dict[str, AlgorithmOutput] = {}
    
    @property
    def outputs(self) -> Dict[str, AlgorithmOutput]:
        """Get the detected outputs."""
        return self._outputs.copy()
    
    def detect(
        self,
        config: AlgorithmConfig,
        base_dir: str = "."
    ) -> AlgorithmOutput:
        """
        Detect output for a single algorithm.
        
        Args:
            config: Algorithm configuration
            base_dir: Base directory of the project
            
        Returns:
            AlgorithmOutput with detected status
        """
        output_dir = os.path.join(base_dir, config.output_dir)
        
        # Try common file patterns
        patterns = [
            f"{config.module_name}.pnml",
            f"{config.type.value.lower()}.pnml",
            "result.pnml",
            "petri_net.pnml",
        ]
        
        # Detect each file type
        result = AlgorithmOutput(
            config=config,
            status=OutputStatus.NOT_FOUND,
        )
        
        # Find PNML file
        result.pnml_path = self._find_file(output_dir, patterns)
        
        # Find PNG file
        png_patterns = [
            f"{config.module_name}.png",
            f"{config.type.value.lower()}.png",
            "result.png",
            "petri_net.png",
        ]
        result.png_path = self._find_file(output_dir, png_patterns)
        
        # Find JSON metrics file
        json_patterns = [
            f"{config.module_name}_metrics.json",
            f"{config.type.value.lower()}_metrics.json",
            "metrics.json",
            "result_scores.json",
        ]
        result.json_path = self._find_file(output_dir, json_patterns)
        
        # Find TXT summary file
        txt_patterns = [
            f"run_output.txt",
            "summary.txt",
            "result.txt",
        ]
        result.txt_path = self._find_file(output_dir, txt_patterns)
        
        # Determine status
        result.missing_files = self._get_missing_files(result)
        result.status = self._determine_status(result)
        
        return result
    
    def detect_all(
        self,
        configs: List[AlgorithmConfig],
        base_dir: str = "."
    ) -> Dict[str, AlgorithmOutput]:
        """
        Detect outputs for all algorithms.
        
        Args:
            configs: List of algorithm configurations
            base_dir: Base directory of the project
            
        Returns:
            Dictionary mapping algorithm names to outputs
        """
        self._outputs = {}
        
        for config in configs:
            if config.enabled:
                output = self.detect(config, base_dir)
                self._outputs[config.name] = output
        
        return self._outputs
    
    def _find_file(
        self,
        directory: str,
        patterns: List[str]
    ) -> str:
        """Find a file matching any of the patterns."""
        if not os.path.exists(directory):
            return ""
        
        for pattern in patterns:
            path = os.path.join(directory, pattern)
            if os.path.exists(path):
                return path
        
        # Search recursively
        for root, dirs, files in os.walk(directory):
            for pattern in patterns:
                for filename in files:
                    if filename == pattern:
                        return os.path.join(root, filename)
        
        return ""
    
    def _get_missing_files(self, output: AlgorithmOutput) -> List[str]:
        """Get list of missing required files."""
        missing = []
        
        if not output.pnml_path:
            missing.append("pnml")
        if not output.png_path:
            missing.append("png")
        if not output.json_path:
            missing.append("json")
        if not output.txt_path:
            missing.append("txt")
        
        return missing
    
    def _determine_status(self, output: AlgorithmOutput) -> OutputStatus:
        """Determine the output status."""
        num_present = 4 - len(output.missing_files)
        
        if num_present == 4:
            return OutputStatus.COMPLETE
        elif num_present > 0:
            return OutputStatus.PARTIAL
        elif output.config.output_dir != "":
            # Directory exists but files missing
            if os.path.exists(os.path.dirname(output.pnml_path) if output.pnml_path else ""):
                return OutputStatus.PARTIAL
            return OutputStatus.MISSING
        else:
            return OutputStatus.NOT_FOUND