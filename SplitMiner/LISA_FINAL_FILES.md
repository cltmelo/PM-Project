# LISA — Final Complete File Versions
Send one prompt at a time. Each asks for a COMPLETE file (not snippets).

---

## PROMPT A — Complete `SplitMiner/dfg_builder.py`

Write the complete final content of `SplitMiner/dfg_builder.py`, incorporating all changes we discussed. The file must contain exactly these functions, in order:

1. **`add_source_sink_to_filtered_dfg(dfg, activity_freq, event_log_df, start_marker='>>', end_marker='<<')`**
   - Sorts event_log_df, uses groupby first/last to get per-case start/end activities
   - Counts them with Counter, adds `(start_marker, act)` and `(act, end_marker)` edges to dfg
   - Adds start_marker and end_marker to activity_freq with total case count
   - Returns `(dfg, activity_freq)` — must be called AFTER filter_dfg, never before

2. **`add_source_sink_to_log(event_log_df, start_marker='>>', end_marker='<<')`**
   - For each case: adds a row with concept:name=start_marker at timestamp = case_min - 24h
   - For each case: adds a row with concept:name=end_marker at timestamp = case_max + 24h
   - Uses vectorized groupby agg(['min','max']) — no per-case loop
   - Concatenates and returns re-sorted DataFrame

3. **`filter_rare_variants(event_log_df, min_variant_freq=3)`**
   - Sorts by case and timestamp
   - Builds variant tuple per case with groupby apply(tuple)
   - Keeps only cases whose variant appears >= min_variant_freq times
   - Prints: kept N/total cases, M/total variants retained
   - Returns filtered DataFrame

4. **`build_dfg(log_path)`**
   - Loads XES, converts to DataFrame
   - Vectorized: sort, groupby+shift(-1) for next_activity, filter valid transitions, groupby().size()
   - Returns `(dfg_dict, activity_freq_dict, event_log_df)` — 3 values

5. **`build_dfg_fast(log_path)`**
   - Loads XES, converts to DataFrame
   - Calls `pm4py.discover_directly_follows_graph(event_log_df)` (Cython-backed)
   - Converts result to plain `{(src, tgt): int}` dict
   - Returns `(dfg_dict, activity_freq_dict, event_log_df)` — 3 values

6. **`filter_dfg(dfg, activity_freq, threshold_type='frequency', threshold_value=0.02, event_log_df=None)`**
   - When threshold_type='frequency' AND event_log_df is not None: use CASE-BASED filtering
     - groupby+shift to get next activity column
     - groupby(['concept:name', '_next'])['case:concept:name'].nunique() for case counts
     - min_cases = max(threshold_value * num_cases, 2)
     - Keep edges where case_count >= min_cases
   - When event_log_df is None: fallback to occurrence-based (max_freq denominator)
   - Returns filtered dict

7. **`get_start_activities(dfg, activity_freq)`** — activities never appearing as target
8. **`get_end_activities(dfg, activity_freq)`** — activities never appearing as source

Do not include any references to paper authors, publication names, or phrases like "paper method" in docstrings or comments.

---

## PROMPT B — Complete `SplitMiner/concurrency.py`

Write the complete final content of `SplitMiner/concurrency.py`, incorporating all changes we discussed. The file must contain:

1. **`detect_concurrency_fast(event_log_df, dfg, min_support=0.01)`**
   - Takes pre-loaded DataFrame (not file path)
   - Finds candidate pairs where BOTH (A→B) and (B→A) exist in dfg (excluding self-loops)
   - Sorts DataFrame, uses groupby+shift(-1) to build next-activity column
   - Counts distinct cases per edge in ONE pass: `groupby(['concept:name', '_next'])['case:concept:name'].nunique()`
   - For each candidate pair (A,B): both `cases_A_to_B` and `cases_B_to_A` must be >= `min_support * num_cases`
   - Returns set of canonical pairs `{(min(A,B), max(A,B)), ...}`

2. **`detect_concurrency(log_path, dfg, min_support=0.01)`** — DEPRECATED wrapper
   - Loads DataFrame from log_path, calls detect_concurrency_fast
   - Docstring marks it as deprecated

3. **`is_parallel(act1, act2, concurrent_pairs)`** — checks canonical pair in set

4. **`get_parallel_groups(concurrent_pairs)`** — connected components via DFS

Do not include any references to paper authors or publication names in docstrings or comments.

---

## PROMPT C — Complete `SplitMiner/gateway_discovery.py`

Write the complete final content of `SplitMiner/gateway_discovery.py`, incorporating all changes we discussed. The file must contain:

1. **`GatewayType`** class with AND, XOR, OR constants

2. **`discover_split_gateway(activity, successors, dfg, concurrent_pairs, activity_freq)`**
   - Returns None if len(successors) <= 1
   - Returns AND if ALL successor pairs are concurrent
   - Returns XOR otherwise

3. **`discover_join_gateway(activity, predecessors, dfg, concurrent_pairs, activity_freq)`**
   - Returns None if len(predecessors) <= 1
   - Returns AND if ALL predecessor pairs are concurrent
   - Returns XOR otherwise

4. **`validate_and_joins(split_gateways, join_gateways, dfg)`**
   - Builds successors dict from dfg
   - For each AND join: gets its predecessor set from dfg
   - Checks if any AND split's successor set contains ALL those predecessors
   - If no matching AND split → downgrades join to XOR
   - Returns updated join_gateways dict

5. **`discover_all_gateways(dfg, concurrent_pairs, activity_freq)`**
   - Builds successors and predecessors dicts
   - Discovers split_gateways and join_gateways
   - Calls `validate_and_joins` at the end before returning
   - Returns `(split_gateways, join_gateways)`

Do not include any references to paper authors or publication names.

---

## PROMPT D — Complete `SplitMiner/bpmn_exporter.py`

Write the complete final content of `SplitMiner/bpmn_exporter.py`, incorporating all changes we discussed. This is the most critical file.

The file must contain a `BPMNExporter` class with:

**`export_bpmn(dfg, split_gateways, join_gateways, concurrent_pairs, loop_info, output_path)`**
- Builds BPMN 2.0 XML with tasks and gateways
- Routes flows through gateways
- Returns output_path

**`export_pnml(dfg, output_path, start_activities=None, end_activities=None, split_gateways=None, join_gateways=None, concurrent_pairs=None)`**
- Returns `output_path` (string, NOT a Petri net object)
- Uses the following Petri net structure:
  - Per activity: `src_ACT` place → labeled transition `trans_ACT` → `snk_ACT` place
  - Per DFG edge (A→B): one invisible tau transition `tau_A__B` connecting `snk_A` → tau → `src_B`
- **CRITICAL**: For every tau (invisible) transition, add this XML child element — WITHOUT this, pm4py treats all transitions as visible and fitness collapses:
  ```python
  ts = ET.SubElement(tr, 'toolspecific')
  ts.set('tool', 'ProM')
  ts.set('version', '6.4')
  ts.set('activity', '$invisible$')
  ```
  This element must ONLY be added to transitions with label=None. Labeled transitions must NOT have it.
- Initial marking: token in `src_>>` (or the source place of the start activity)
- Final marking: token in `snk_<<` (or the sink place of the end activity), using `<finalmarkings>` element

And a standalone **`export_model(dfg, split_gateways, join_gateways, concurrent_pairs, loop_info, output_dir, format='bpmn', start_activities=None, end_activities=None)`**
- Creates a BPMNExporter instance
- If format='bpmn': calls export_bpmn, saves to `output_dir/result_split_miner.bpmn`
- If format='pnml': calls export_pnml, saves to `output_dir/result_split_miner.pnml`
- Returns the output file path (string)

Do not include any references to paper authors or publication names.

---

## PROMPT E — Complete `SplitMiner/metrics.py`

Write the complete final content of `SplitMiner/metrics.py`, incorporating all changes we discussed. The file must contain:

1. **`_ensure_dataframe(event_log_or_path)`** — loads from path if string, returns as-is if DataFrame

2. **`_run_alignments(event_log_df, net, initial_marking, final_marking)`**
   - Imports: `from pm4py.algo.evaluation.replay_fitness import algorithm as rf_algo` and `from pm4py.algo.evaluation.replay_fitness.variants import alignment_based as ab_variant`
   - Calls `add_source_sink_to_log(event_log_df)` to add >> and << events
   - Calls `rf_algo.apply(log_with_ss, net, im, fm, variant=ab_variant)`
   - Extracts `result.get('log_fitness', result.get('average_trace_fitness', None))`
   - Returns float or None on exception

3. **`evaluate_model(event_log_df, dfg, start_activities, end_activities, pnml_file, split_gateways, join_gateways)`**
   - This exact signature — positional args in this order
   - Loads the Petri net from pnml_file with `pm4py.read_pnml(pnml_file)`
   - **Fitness**: tries alignment via `_run_alignments`; on failure falls back to `pm4py.fitness_token_based_replay` using `perc_fit_traces`
   - **Precision**: tries `pm4py.algo.evaluation.precision.variants.etconformance_token`; on failure uses `pm4py.precision_token_based_replay`
   - **Generalization**: uses `pm4py.generalization_token_based_replay`; on failure estimates from fitness+precision
   - **Simplicity**: `1 - (num_places + num_transitions + num_arcs) / 1000.0`, clamped to [0,1]
   - **CFC** (Control Flow Complexity): sum of (len(successors)-1) for each activity with multiple successors
   - **Structuredness**: fraction of gateways that are XOR (not AND)
   - **F-score**: `2 * fitness * precision / (fitness + precision)` if both > 0, else 0
   - **Overall score**: `0.4*fitness + 0.3*precision + 0.2*generalization + 0.1*simplicity`
   - Returns dict with keys: `fitness_score`, `precision_score`, `generalization_score`, `simplicity_score`, `f_score`, `overall_score`, `cfc`, `structuredness`, `num_activities`, `num_edges`

4. **`save_metrics(metrics, output_path)`** — saves metrics dict as JSON

Do not include any references to paper authors or publication names.

---

## PROMPT F — Complete `SplitMiner/main.py`

Write the complete final content of `SplitMiner/main.py`. This is the entry point that wires all steps together. Requirements:

**Configuration constants** (at module level, before main()):
```python
FILTER_THRESHOLD_TYPE = 'frequency'
FILTER_THRESHOLD_VALUE = 0.15
MIN_CONCURRENCY_SUPPORT = 0.01
FILTER_RARE_VARIANTS = True
MIN_VARIANT_FREQ = 3
```

**Imports** from the SplitMiner package:
- `dfg_builder`: `build_dfg_fast`, `filter_dfg`, `add_source_sink_to_filtered_dfg`, `filter_rare_variants`
- `concurrency`: `detect_concurrency_fast`
- `gateway_discovery`: `discover_all_gateways`
- `loop_discovery`: `detect_back_edges`, `get_loop_structures`
- `bpmn_exporter`: `export_model`
- `metrics`: `evaluate_model`, `save_metrics`

**Pipeline steps in main()**:

- **Step 1**: `build_dfg_fast(EVENT_LOG_PATH)` → store `dfg_raw, activity_freq, event_log_df`
- **Step 1.5**: if FILTER_RARE_VARIANTS: call `filter_rare_variants(event_log_df, MIN_VARIANT_FREQ)`, then rebuild dfg with `pm4py.discover_directly_follows_graph`, recompute activity_freq
- **Step 2**: call `filter_dfg(dfg_raw, activity_freq, threshold_type=FILTER_THRESHOLD_TYPE, threshold_value=FILTER_THRESHOLD_VALUE, event_log_df=event_log_df)`, then immediately call `add_source_sink_to_filtered_dfg(dfg_filtered, activity_freq, event_log_df)` → assign result back to `dfg_filtered, activity_freq`
- **Step 3**: `detect_concurrency_fast(event_log_df=event_log_df, dfg=dfg_filtered, min_support=MIN_CONCURRENCY_SUPPORT)`
- **Step 4**: `discover_all_gateways(dfg_filtered, concurrent_pairs, activity_freq)`
- **Step 5**: `get_loop_structures(dfg_filtered)` (use only this function, not detect_back_edges)
- **Step 6**: export BPMN with `export_model(..., format='bpmn')` and PNML with `export_model(..., format='pnml')`. Pass `start_activities={'>>'}` and `end_activities={'<<'}` explicitly — do NOT call get_start_activities or get_end_activities.
- **Step 7**: generate PNG visualization from the PNML file using `pm4py.read_pnml` + `pm4py.visualization.petri_net.visualizer`
- **Step 8**: `evaluate_model(event_log_df, dfg_filtered, start_activities, end_activities, pnml_file, split_gateways, join_gateways)` then save with `save_metrics`

**No step may reload the event log from disk** — all steps after Step 1 receive `event_log_df` as a parameter.

**Do not include** any references to paper authors, publication titles, or phrases like "paper method" anywhere in the file — not in print statements, docstrings, or comments. The header print can say something like "SPLIT MINER - Process Discovery Algorithm" without citing authors.
