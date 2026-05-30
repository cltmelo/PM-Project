# PM-Project

## Genetic Miner — Process Discovery

### Overview

This project implements a genetic algorithm for process discovery, evolving populations of CausalNet process models over multiple generations using selection, crossover, and mutation. The algorithm balances replay fitness and structural simplicity through weighted multi-objective optimization, applied to the BPI Challenge 2017 loan application event log.

### Project Structure

| File | Description |
|------|-------------|
| `causal_net.py` | CausalNet data structure representing process models with input/output binding sets |
| `initialization.py` | Random individual generation for initial population creation |
| `metrics.py` | Replay fitness and simplicity evaluation functions |
| `operators.py` | Genetic operators: mutation, crossover, and tournament selection |
| `genetic_miner.py` | Main evolutionary loop orchestrating the genetic algorithm |
| `interface.py` | XES file loading and Petri net export functionality |
| `main.py` | Script entry point with hyperparameter configuration |

### Requirements

Required Python packages:

- **pm4py** — Process mining library for XES loading and Petri net construction
- **pandas** — Data manipulation and event log handling

Install with:

```bash
pip install pm4py pandas
```

### Input Data 

The BPI Challenge 2017 event log must be placed in the following location relative to the  GeneticMiner folder:
```
BPI Challenge 2017_1_all/
└── BPI Challenge 2017.xes.gz
```

The gzipped XES format is supported natively by pm4py.

Running the Algorithm

1. Navigate to the GeneticMiner folder:
```
cd GeneticMiner
```
2. Run the main script:
```
python main.py
```
Hyperparameters can be adjusted by editing the named constants at the top of main.py.

### Output

The algorithm writes two files to the output folder:
| File | Description |
|------|-------------|
| `result_petri_net.pnml` | The discovered process model as a Petri net in PNML format, viewable in tools such as pm4py or ProM |
| `result_scores.json` | Evaluation scores (overall, fitness, simplicity) and the full causal net binding structure in JSON format |

### Hyperparameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `POPULATION_SIZE` | 20 | Number of individuals maintained in the population |
| `NUM_GENERATIONS` | 30 | Number of generations to evolve the population |
| `MUTATION_RATE` | 0.2 | Probability that an activity undergoes mutation (0.0–1.0) |
| `TOURNAMENT_SIZE` | 3 | Number of individuals sampled for tournament selection |
| `W_FITNESS` | 0.7 | Weight for replay fitness in multi-objective scoring |
| `W_SIMPLICITY` | 0.3 | Weight for simplicity in multi-objective scoring |
| `MAX_BINDINGS` | 3 | Maximum binding sets per activity during initialization |
| `RANDOM_SEED` | 42 | Random seed for reproducible results |

Note: W_FITNESS and W_SIMPLICITY must sum to 1.0.


## Data Preparation

Ensure the BPI Challenge 2017 dataset is properly organized:
```
PM/
├── GeneticMiner/
│   ├── causal_net.py
│   ├── initialization.py
│   ├── metrics.py
│   ├── operators.py
│   ├── genetic_miner.py
│   ├── interface.py
│   └── main.py
├── BPI Challenge 2017_1_all/
│   └── BPI Challenge 2017.xes.gz
└── README.md
```

## How to Use
### Running the Genetic Miner
```
cd GeneticMiner
python main.py
```

### Expected Console Output
```
Loading event log from: /path/to/BPI Challenge 2017.xes.gz
Loaded 31509 cases with 1202267 events

Starting genetic process discovery...
Population size: 20
Generations: 30
Mutation rate: 0.2
Tournament size: 3
Weights: fitness=0.7, simplicity=0.3
Random seed: 42
--------------------------------------------------
Generation 1: Best overall_score = 0.452341
Generation 2: Best overall_score = 0.523156
Generation 3: Best overall_score = 0.587234
...
Generation 30: Best overall_score = 0.782451
--------------------------------------------------

Final Results:
  Overall score:   0.782451
  Fitness score:   0.834521
  Simplicity score: 0.652143

Results saved to:
  Petri net (PNML): /path/to/output/result_petri_net.pnml
  Scores (JSON):    /path/to/output/result_scores.json

Genetic process discovery completed successfully!
```

## Viewing Results

### Petri Net Visualization (using pm4py):
```
import pm4py
from pm4py.visualization.petri_net import visualizer

net, initial_marking, final_marking = pm4py.read_pnml("output/result_petri_net.pnml")
fig = visualizer.apply(net, initial_marking, final_marking)
visualizer.save(fig, "output/process_model.png")
```

### Scores Inspection:
```
cat output/result_scores.json
```

Example JSON output:
```{
  "overall_score": 0.782451,
  "fitness_score": 0.834521,
  "simplicity_score": 0.652143,
  "activities": ["A_APPROVED", "A_DECLINED", "A_ACTIVATED", ...],
  "input_bindings": {
    "A_APPROVED": [["A_ACTIVATED"], ["A_SUBMITTED"]],
    "A_DECLINED": [["A_ACTIVATED"]]
  },
  "output_bindings": {
    "A_SUBMITTED": [["A_APPROVED"], ["A_DECLINED"]]
  }
}
```