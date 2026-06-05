# to run use: python -m AlphaMiner.main

"""
Alpha Miner - Main Entry Point

Executes the complete Alpha Miner process discovery pipeline:
1. Load event log
2. Preprocess data
3. Discover Petri net
4. Compute metrics
5. Export results

Usage:
    python -m AlphaMiner.main
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from .config import CONFIG, get_config
from .utils.file_utils import ensure_dir, validate_file
from .utils.logging_utils import print_header, print_stage, print_info, print_success

from .discovery.loader import EventLogLoader
from .discovery.preprocessing import LogPreprocessor
from .discovery.alpha_miner import AlphaMinerDiscoverer

from .evaluation.metrics import MetricsCollector

from .output.pnml_exporter import PNMLExporter
from .output.png_exporter import PNGExporter
from .output.json_exporter import JSONExporter
from .output.txt_exporter import TXTExporter


def run_pipeline(
    log_path: str = None,
    output_dir: str = None,
    noise_threshold: float = None,
) -> dict:
    """
    Run the complete Alpha Miner pipeline.
    
    Args:
        log_path: Path to the event log file
        output_dir: Directory for output files
        noise_threshold: Minimum activity frequency threshold
        
    Returns:
        Dictionary containing all results and outputs
    """
    # Get configuration
    config = get_config()
    log_path = log_path or config.log_path
    output_dir = output_dir or config.output_dir
    noise_threshold = noise_threshold if noise_threshold is not None else config.noise_threshold
    
    # Print header
    print("\n" + "#" * 70)
    print("#" + " ALPHA MINER - PROCESS DISCOVERY ".center(68) + "#")
    print("#" + " BPI Challenge 2017 Event Log ".center(68) + "#")
    print("#" * 70)
    
    print(f"\n⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create output directory
    ensure_dir(output_dir)
    
    # ==========================================================================
    # Stage 1: Load Event Log
    # ==========================================================================
    loader = EventLogLoader()
    df = loader.load(log_path)
    
    # ==========================================================================
    # Stage 2: Preprocess
    # ==========================================================================
    if noise_threshold > 0:
        preprocessor = LogPreprocessor()
        df = preprocessor.preprocess(df, activity_threshold=int(noise_threshold))
    else:
        print_stage(2, "PREPROCESSING (SKIPPED)")
        print("   ℹ️  noise_threshold = 0, no filtering applied")
    
    # ==========================================================================
    # Stage 3: Discover Petri Net
    # ==========================================================================
    discoverer = AlphaMinerDiscoverer()
    result = discoverer.discover(df)
    
    # ==========================================================================
    # Stage 4: Compute Metrics
    # ==========================================================================
    metrics_collector = MetricsCollector()
    metrics = metrics_collector.collect(
        df,
        result.net,
        result.initial_marking,
        result.final_marking,
        compute_fitness=config.compute_fitness,
        compute_precision=config.compute_precision,
    )
    
    # ==========================================================================
    # Stage 5: Export Results
    # ==========================================================================
    print_stage(5, "EXPORTING RESULTS")
    
    # Export PNML
    pnml_exporter = PNMLExporter()
    pnml_path = pnml_exporter.export(
        result.net,
        result.initial_marking,
        result.final_marking,
        os.path.join(output_dir, "alpha_miner.pnml")
    )
    
    # Export PNG
    png_exporter = PNGExporter()
    png_path = png_exporter.export(
        result.net,
        os.path.join(output_dir, "alpha_miner.png"),
        initial_marking=result.initial_marking,
        final_marking=result.final_marking,
        dpi=config.png_dpi
    )
    
    # Export JSON
    json_exporter = JSONExporter()
    json_path = json_exporter.export(
        metrics.to_dict(),
        os.path.join(output_dir, "alpha_miner_metrics.json")
    )
    
    # Export TXT
    txt_exporter = TXTExporter()
    txt_path = txt_exporter.export(
        df,
        result.net,
        metrics.to_dict(),
        os.path.join(output_dir, "run_output.txt")
    )
    
    # ==========================================================================
    # Final Summary
    # ==========================================================================
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    print_info("Fitness", f"{metrics.fitness:.4f}" if metrics.fitness else "N/A")
    print_info("Precision", f"{metrics.precision:.4f}" if metrics.precision else "N/A")
    print_info("F-Score", f"{metrics.f_score:.4f}" if metrics.f_score else "N/A")
    
    print(f"\n📁 Output directory: {output_dir}")
    print(f"⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_success("Pipeline completed successfully!")
    
    return {
        "dataframe": df,
        "result": result,
        "metrics": metrics,
        "output_dir": output_dir,
        "output_files": {
            "pnml": pnml_path,
            "png": png_path,
            "json": json_path,
            "txt": txt_path,
        },
    }


def main():
    """Main entry point for the script."""
    import os
    
    try:
        run_pipeline()
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure the event log file exists at:")
        print(f"  {CONFIG.log_path}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()