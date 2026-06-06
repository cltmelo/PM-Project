import pandas as pd
from genetic_miner import run_genetic_miner

df = pd.DataFrame({
    'case:concept:name': [1,1,1, 2,2,2, 3,3,3],
    'concept:name':      ['A','B','C', 'A','B','D', 'A','C','D'],
    'time:timestamp':    pd.date_range('2024-01-01', periods=9, freq='h')
})

df = df.sort_values(['case:concept:name', 'time:timestamp'])

best, overall, fitness, simplicity = run_genetic_miner(
    df=df,
    population_size=5,
    num_generations=3,
    mutation_rate=0.2,
    tournament_size=2,
    w_fitness=0.7,
    w_simplicity=0.3,
    max_bindings_per_activity=2,
    random_seed=42
)

print(f"Smoke test passed — overall={overall:.4f}, fitness={fitness:.4f}, simplicity={simplicity:.4f}")