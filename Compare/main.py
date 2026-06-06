"""
Comparison Framework - Main Entry Point

Executes the complete comparison pipeline:
1. Detect existing outputs
2. Execute missing algorithms
3. Parse metrics and structure
4. Calculate comparison metrics
5. Generate visualizations and reports

Usage:
    python -m compare.main
    
Or simply:
    python compare/main.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Compare.config import get_enabled_algorithms, get_compare_config
from Compare.utils.file_utils import ensure_dir
from Compare.utils.logging_utils import print_header, print_info, print_success

from Compare.runner.detector import OutputDetector
from Compare.runner.executor import AlgorithmExecutor
from Compare.metrics.calculator import MetricsCalculator
from Compare.visualization.charts import ComparisonCharts
from Compare.visualization.table import ComparisonTable
from Compare.report.generator import ReportGenerator


def run_comparison(
    base_dir: str = None,
    run_missing: bool = True,
    force_rerun: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Run the complete comparison pipeline.
    
    Args:
        base_dir: Base directory of the project
        run_missing: Whether to run algorithms with missing output
        force_rerun: Whether to force re-execution of all algorithms
        dry_run: If True, only simulate execution
        
    Returns:
        Dictionary containing all results and outputs
    """
    # Get configuration
    config = get_compare_config()
    base_dir = base_dir or config.base_dir
    algorithms = get_enabled_algorithms()
    
    # Print header
    print("\n" + "#" * 70)
    print("#" + " PROCESS MINING ALGORITHM COMPARISON ".center(68) + "#")
    print("#" + " " * 68 + "#")
    print("#" * 70)
    
    # Ensure output directory exists
    ensure_dir(Path(base_dir) / config.output_dir)
    
    # ==========================================================================
    # Stage 1: Detect Outputs
    # ==========================================================================
    print_header("STAGE 1: DETECTING ALGORITHM OUTPUTS")
    
    detector = OutputDetector()
    outputs = detector.detect_all(algorithms, base_dir)
    
    print_info("Total algorithms", len(outputs))
    complete_count = sum(1 for o in outputs.values() if o.is_complete)
    print_info("Complete outputs", complete_count)
    print_info("Missing outputs", len(outputs) - complete_count)
    
    # Print status for each algorithm
    for name, output in outputs.items():
        status = output.status.value.title()
        if output.is_complete:
            print_success(f"{name}: {status}")
        else:
            print_info(f"{name}: {status}", f"Missing: {', '.join(output.missing_files)}")
    
    # ==========================================================================
    # Stage 2: Execute Missing Algorithms
    # ==========================================================================
    if run_missing and not dry_run:
        executor = AlgorithmExecutor()
        if force_rerun:
            execution_results = executor.run_all(algorithms, base_dir, force=True, dry_run=dry_run)
        else:
            execution_results = executor.run_missing(outputs, base_dir, dry_run)
        
        # Re-detect outputs after execution
        if execution_results:
            outputs = detector.detect_all(algorithms, base_dir)
    
    # ==========================================================================
    # Stage 3: Calculate Metrics
    # ==========================================================================
    calculator = MetricsCalculator()
    comparison_result = calculator.calculate(outputs)
    
    # ==========================================================================
    # Stage 4: Generate Visualizations
    # ==========================================================================
    output_dir = str(Path(base_dir) / config.output_dir)
    
    if config.generate_charts:
        charts = ComparisonCharts()
        chart_files = charts.create_all(comparison_result, output_dir, config.chart_dpi)
        print_success(f"Created {len(chart_files)} charts")
    
    # Create tables
    table = ComparisonTable()
    table_files = table.create_all(comparison_result, output_dir)
    print_success(f"Created {len(table_files)} tables")
    
    # ==========================================================================
    # Stage 5: Generate Reports
    # ==========================================================================
    if config.generate_report:
        generator = ReportGenerator()
        report_files = generator.create_all(comparison_result, output_dir)
        print_success(f"Created {len(report_files)} reports")
    
    # ==========================================================================
    # Final Summary
    # ==========================================================================
    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)
    
    print_info("Output directory", output_dir)
    
    return {
        "outputs": outputs,
        "comparison_result": comparison_result,
        "output_dir": output_dir,
    }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process Mining Algorithm Comparison")
    parser.add_argument("--base-dir", default=".", help="Base directory")
    parser.add_argument("--no-run", action="store_true", help="Don't run missing algorithms")
    parser.add_argument("--force", action="store_true", help="Force re-run all algorithms")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution only")
    
    args = parser.parse_args()
    
    try:
        run_comparison(
            base_dir=args.base_dir,
            run_missing=not args.no_run,
            force_rerun=args.force,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
