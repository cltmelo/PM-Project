# Process Mining Algorithm Comparison Framework

## Overview

The **Compare** framework allows you to compare the results and performance of different process mining algorithms (Genetic Miner, Alpha Miner, Inductive Miner, and Split Miner) across common metrics.

## Quick Start

### Run Full Comparison

```bash
python -m Compare.main
```

This executes the complete pipeline:
1. **Stage 1**: Detects existing algorithm outputs
2. **Stage 2**: Executes algorithms with missing output
3. **Stage 3**: Calculates metrics and comparison data
4. **Stage 4**: Generates visualization charts
5. **Stage 5**: Generates comparison reports

### Command Options

All commands must be run from the project root directory (`/Users/ernestou/Desktop/HOF/Process_Mining/PROJECT/PM-Project`).

#### Dry Run (Recommended First Step)
```bash
python -m Compare.main --dry-run
```
**What it does**: Shows what would be executed without actually running algorithms.
- Detects available outputs
- Generates charts and tables
- Perfect for testing without computation

#### Skip Missing Algorithm Execution
```bash
python -m Compare.main --no-run
```
**What it does**: Compares only existing algorithm outputs.
- Skips running algorithms with missing output
- Useful when you just want to regenerate reports/charts

#### Force Re-run All Algorithms
```bash
python -m Compare.main --force
```
**What it does**: Re-executes all algorithms even if output exists.
- Useful for getting fresh results
- Takes longer but ensures all outputs are current

#### Specify Base Directory
```bash
python -m Compare.main --base-dir /path/to/project
```
**What it does**: Runs comparison on a different project directory.
- Default: current directory (`.`)
- Example: `python -m Compare.main --base-dir /Users/ernestou/Desktop/HOF/Process_Mining/PROJECT/PM-Project`

#### Combine Flags
```bash
python -m Compare.main --dry-run --base-dir /path/to/project
python -m Compare.main --force --base-dir /path/to/project
python -m Compare.main --no-run --dry-run
```

## Output Files

After running, results are saved in `compare/output/`:

### Generated Files:

- **comparison_table.txt** - Formatted ASCII table of results
- **comparison_table.html** - Interactive HTML table
- **comparison_table.csv** - CSV export for analysis
- **quality_metrics.png** - Bar chart of fitness/precision/f-score
- **structure_metrics.png** - Chart of Petri net structure metrics
- **radar_chart.png** - Multi-dimensional comparison
- **summary_chart.png** - Overall comparison summary
- **comparison_report.html** - Full HTML report
- **comparison_report.md** - Markdown report
- **comparison_summary.txt** - Text summary

## Framework Features

### Detected Algorithms

The framework automatically detects and compares:

1. **Genetic Miner** - Location: `GeneticMiner/Output/`
   - Expected outputs: `genetic_miner.pnml`, metrics JSON, PNG, TXT

2. **Alpha Miner** - Location: `AlphaMiner/output/`
   - Expected outputs: `alpha_miner.pnml`, `alpha_miner_metrics.json`, PNG, TXT

3. **Inductive Miner** - Location: `InductiveMiner/Output/`
   - Expected outputs: `inductive_miner.pnml`, metrics JSON, PNG, TXT

4. **Split Miner** - Location: `SplitMiner/Output/`
   - Expected outputs: `split_miner.pnml`, metrics JSON, PNG, TXT

### Metrics Calculated

For each algorithm, the framework calculates:

- **Quality Metrics**
  - Fitness score (0-1)
  - Precision score (0-1)
  - F-score (harmonic mean of fitness and precision)

- **Structure Metrics**
  - Number of places
  - Number of transitions
  - Number of arcs
  - Complexity score

- **Model Properties**
  - Event log cases count
  - Total events processed
  - Activities discovered

### Output Structure

The framework generates comparison data showing:
- Which algorithm has the best fitness
- Which algorithm has the best precision
- Which algorithm produces the simplest model
- Overall ranking of algorithms

## Workflow Examples

### Example 1: First Time Setup
```bash
# Step 1: See what outputs are available (no computation)
python -m Compare.main --dry-run

# Step 2: Run comparison with missing algorithm outputs
python -m Compare.main

# Step 3: Check results in compare/output/
```

### Example 2: Quick Update (Existing Outputs Only)
```bash
# Regenerate charts and reports without re-running algorithms
python -m Compare.main --no-run
```

### Example 3: Fresh Comparison (Force Re-run)
```bash
# Run all algorithms fresh and regenerate reports
python -m Compare.main --force
```

### Example 4: Testing Setup
```bash
# Safe test without actual execution
python -m Compare.main --dry-run --base-dir /Users/ernestou/Desktop/HOF/Process_Mining/PROJECT/PM-Project
```

## Configuration

The framework configuration is in `Compare/config.py`. Key settings:

```python
# Event log file
event_log_path: "BPI Challenge 2017_1_all/BPI Challenge 2017.xes.gz"

# Output directory
output_dir: "compare/output"

# Chart generation
generate_charts: True
generate_report: True

# Chart resolution
chart_dpi: 150

# Quality thresholds
min_fitness_threshold: 0.8
min_precision_threshold: 0.6
```

To modify these settings, edit `Compare/config.py`.

## Status Messages Explained

### Algorithm Status

- **✅ Complete** - All required outputs found (pnml, png, json, txt)
- **Partial** - Some outputs missing
- **Missing** - No outputs found

### Stage Progress

- **STAGE 1: DETECTING ALGORITHM OUTPUTS** - Finding existing results
- **STAGE 2: CALCULATING METRICS** - Computing comparison data
- **STAGE 3: CREATING COMPARISON CHARTS** - Generating visualizations
- **STAGE 4: CREATING COMPARISON TABLES** - Building data tables
- **STAGE 5: GENERATING REPORTS** - Creating final reports

## Troubleshooting

### Issue: "No data to compare"
**Solution**: Ensure algorithm outputs exist in their expected directories, or run without `--no-run` flag.

### Issue: Charts not generating
**Solution**: Check that matplotlib is installed: `pip install matplotlib`

### Issue: Event log not found
**Solution**: Verify the file path in `Compare/config.py` matches your setup.

### Issue: Missing required files
**Solution**: Run individual algorithms first to generate outputs, then re-run comparison.

## Integration with Other Miners

To add a new algorithm to the comparison:

1. Update `Compare/config.py` - Add `AlgorithmConfig` entry
2. Ensure algorithm produces output in expected directory with required file types
3. Re-run framework with `--force` flag

## Performance Notes

- **Dry-run**: ~5-10 seconds (no algorithm execution)
- **No-run**: ~10-30 seconds (visualization generation only)
- **Full comparison**: Depends on algorithm execution time (can be 30+ minutes with `--force`)
- **Output size**: Typically 5-50 MB depending on algorithm complexity

## File Structure

```
Compare/
├── __init__.py              # Package initialization
├── config.py                # Configuration and settings
├── main.py                  # Main entry point
├── runner/                  # Algorithm execution
│   ├── detector.py         # Output detection
│   └── executor.py         # Algorithm runner
├── parser/                  # Output parsing
│   ├── pnml_parser.py      # PNML file parser
│   └── json_parser.py      # JSON metrics parser
├── metrics/                 # Metrics calculation
│   └── calculator.py       # Comparison calculator
├── visualization/           # Visualization generation
│   ├── charts.py           # Chart generation
│   └── table.py            # Table generation
├── report/                  # Report generation
│   └── generator.py        # Report generator
├── utils/                   # Utility functions
│   ├── file_utils.py
│   └── logging_utils.py
└── output/                  # Generated results
    ├── *.txt               # Text results
    ├── *.html              # HTML reports
    ├── *.png               # Chart images
    └── *.csv               # Data exports
```

## Next Steps

1. Run: `python -m Compare.main --dry-run` to verify setup
2. Run: `python -m Compare.main` to execute full comparison
3. Review: Results in `compare/output/` directory
4. Customize: Edit `Compare/config.py` to adjust settings as needed
