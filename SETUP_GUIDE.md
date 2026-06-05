# Process Mining Project Setup & Usage Guide

## Environment: `process-mining`

This project uses a dedicated conda environment called `process-mining` to ensure all dependencies are properly isolated and managed.

### Quick Start

#### Option 1: Using the convenience script (Recommended)
```bash
cd /Users/ernestou/Desktop/HOF/Process_Mining/PROJECT/PM-Project
./run.sh
```

#### Option 2: Using conda directly
```bash
conda run -n process-mining python -m AlphaMiner.main
```

#### Option 3: Using the Python interpreter path
```bash
/opt/anaconda3/envs/process-mining/bin/python -m AlphaMiner.main
```

---

## Running Individual Miners

### AlphaMiner
```bash
conda run -n process-mining python -m AlphaMiner.main
```

### GeneticMiner
```bash
conda run -n process-mining python -m GeneticMiner.main
```

### InductiveMiner
```bash
conda run -n process-mining python -m InductiveMiner.main
```

### SplitMiner
```bash
conda run -n process-mining python -m SplitMiner.main
```

---

## Running All Miners

```bash
./run_all_miners.sh
```

Or to run specific miners:
```bash
./run_all_miners.sh AlphaMiner GeneticMiner
```

---

## Environment Setup

### Verify the environment exists
```bash
conda env list
```

### Activate the environment manually
```bash
conda activate process-mining
```

### Install/Update dependencies
```bash
pip install -r requirements.txt
```

### Create a fresh environment (if needed)
```bash
conda create -n process-mining python=3.13 -y
conda activate process-mining
pip install -r requirements.txt
```

---

## Project Structure

```
PM-Project/
├── AlphaMiner/           # Alpha Miner implementation
│   ├── main.py          # Entry point
│   ├── config.py        # Configuration
│   ├── discovery/       # Discovery algorithms
│   ├── evaluation/      # Metrics & evaluation
│   ├── output/          # Export formats
│   └── utils/           # Utilities
├── GeneticMiner/        # Genetic algorithm miner
├── InductiveMiner/      # Inductive mining algorithm
├── SplitMiner/          # Split miner algorithm
├── Analizer/            # Analysis tools
├── BPI Challenge 2017_1_all/  # Event log data
├── run.sh               # Run AlphaMiner
├── run_all_miners.sh    # Run all miners
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## Output Files

After running a miner, results are saved in the respective `output/` directory:

- **PNML files**: Petri net model (standard XML format)
- **PNG files**: Visual representation of the discovered model
- **JSON files**: Metrics and evaluation results
- **TXT files**: Detailed text summary

Example outputs for AlphaMiner:
- `AlphaMiner/output/alpha_miner.pnml`
- `AlphaMiner/output/alpha_miner.png`
- `AlphaMiner/output/alpha_miner_metrics.json`
- `AlphaMiner/output/run_output.txt`

---

## Available Python Interpreters

### Primary (Recommended)
- **Path**: `/opt/anaconda3/envs/process-mining/bin/python`
- **Conda Env**: `process-mining`
- **Status**: ✅ All dependencies installed

### Alternative (if needed)
- **Path**: `/opt/anaconda3/bin/python`
- **Conda Env**: `base`
- **Note**: May have different dependencies

---

## Troubleshooting

### "No module named 'pm4py'"
Ensure you're using the process-mining environment:
```bash
conda activate process-mining
python -m AlphaMiner.main
```

### "ImportError: attempted relative import with no known parent package"
Always use the `-m` flag when running:
```bash
python -m AlphaMiner.main  ✅ Correct
python AlphaMiner/main.py  ❌ Wrong
```

### Graphviz warning for PNG export
The script handles this gracefully by creating a fallback text visualization if Graphviz is not installed. To install Graphviz:
```bash
brew install graphviz  # macOS
apt-get install graphviz  # Linux
```

---

## Dependencies

Core dependencies installed in `process-mining`:
- **pm4py** (2.7.22.4) - Process mining library
- **pandas** (2.2.3) - Data analysis
- **graphviz** (0.21) - Graph visualization
- **numpy** (2.2.4) - Numerical computing
- **networkx** (3.5) - Network analysis
- **scipy** (1.15.3) - Scientific computing
- **matplotlib** (3.10.1) - Plotting

See `requirements.txt` for full list.

---

## Next Steps

1. ✅ Environment configured
2. ✅ Dependencies installed
3. ✅ AlphaMiner tested and working
4. Run other miners as needed
5. Analyze results in output directories

Happy mining! 🚀
