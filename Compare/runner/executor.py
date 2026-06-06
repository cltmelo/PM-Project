"""
Algorithm execution functionality.

Runs process mining algorithms when output is missing.
"""

import os
import subprocess
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..config import AlgorithmConfig, AlgorithmType, get_enabled_algorithms
from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import (
    print_header, print_info, print_success, 
    print_warning, print_error, print_stage
)
from .detector import OutputDetector, AlgorithmOutput, OutputStatus


@dataclass
class ExecutionResult:
    """Container for algorithm execution results."""
    config: AlgorithmConfig
    success: bool
    execution_time: float = 0.0
    error_message: str = ""
    output: AlgorithmOutput = None


class AlgorithmExecutor:
    """
    Executes process mining algorithms.
    
    Automatically runs algorithms when their outputs are missing
    or incomplete.
    
    Example:
        executor = AlgorithmExecutor()
        results = executor.run_missing(algorithms, base_dir)
    """
    
    def __init__(self):
        """Initialize the algorithm executor."""
        self._results: Dict[str, ExecutionResult] = {}
        self._detector = OutputDetector()
    
    @property
    def results(self) -> Dict[str, ExecutionResult]:
        """Get the execution results."""
        return self._results.copy()
    
    def run_missing(
        self,
        outputs: Dict[str, AlgorithmOutput],
        base_dir: str = ".",
        dry_run: bool = False,
    ) -> Dict[str, ExecutionResult]:
        """
        Run algorithms that are missing output.
        
        Args:
            outputs: Dictionary of detected outputs
            base_dir: Base directory of the project
            dry_run: If True, only simulate execution
            
        Returns:
            Dictionary of execution results
        """
        print_stage(1, "EXECUTING MISSING ALGORITHMS")
        
        self._results = {}
        missing_count = 0
        
        for name, output in outputs.items():
            if output.status != OutputStatus.COMPLETE:
                missing_count += 1
        
        if missing_count == 0:
            print_success("All algorithms have complete output!")
            return self._results
        
        print_info("Algorithms to execute", missing_count)
        
        for name, output in outputs.items():
            if output.status != OutputStatus.COMPLETE:
                result = self._run_algorithm(
                    output.config, 
                    base_dir, 
                    dry_run
                )
                self._results[name] = result
        
        return self._results
    
    def run_all(
        self,
        configs: List[AlgorithmConfig],
        base_dir: str = ".",
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, ExecutionResult]:
        """
        Run all enabled algorithms.
        
        Args:
            configs: List of algorithm configurations
            base_dir: Base directory of the project
            force: If True, re-run even with complete output
            dry_run: If True, only simulate execution
            
        Returns:
            Dictionary of execution results
        """
        print_stage(1, "EXECUTING ALGORITHMS")
        
        self._results = {}
        enabled = [c for c in configs if c.enabled]
        
        print_info("Total algorithms", len(enabled))
        print_info("Dry run", dry_run)
        
        for config in enabled:
            # Check current status
            detector = OutputDetector()
            current_output = detector.detect(config, base_dir)
            
            if current_output.is_complete and not force:
                print_success(f"{config.name}: Already complete, skipping")
                continue
            
            if dry_run:
                print_warning(f"{config.name}: Would execute (dry run)")
                continue
            
            result = self._run_algorithm(config, base_dir, False)
            self._results[config.name] = result
        
        return self._results
    
    def _run_algorithm(
        self,
        config: AlgorithmConfig,
        base_dir: str,
        dry_run: bool = False,
    ) -> ExecutionResult:
        """Run a single algorithm."""
        start_time = datetime.now()
        script_path = os.path.join(base_dir, config.main_script)
        
        if dry_run:
            print_warning(f"{config.name}: Would execute {script_path}")
            return ExecutionResult(
                config=config,
                success=True,
                execution_time=0.0,
            )
        
        print(f"\n⏳ Executing {config.name}...")
        print(f"   Script: {script_path}")
        
        try:
            # Ensure output directory exists
            output_dir = os.path.join(base_dir, config.output_dir)
            ensure_dir(output_dir)
            
            # Run the script
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                print_success(f"{config.name}: Completed in {execution_time:.2f}s")
                return ExecutionResult(
                    config=config,
                    success=True,
                    execution_time=execution_time,
                    output=self._detector.detect(config, base_dir),
                )
            else:
                print_error(f"{config.name}: Failed with code {result.returncode}")
                return ExecutionResult(
                    config=config,
                    success=False,
                    execution_time=execution_time,
                    error_message=result.stderr[:500],
                )
                
        except subprocess.TimeoutExpired:
            print_error(f"{config.name}: Timed out after 10 minutes")
            return ExecutionResult(
                config=config,
                success=False,
                execution_time=600.0,
                error_message="Execution timed out",
            )
        except Exception as e:
            print_error(f"{config.name}: {str(e)}")
            return ExecutionResult(
                config=config,
                success=False,
                error_message=str(e),
            )