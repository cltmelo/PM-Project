# LISA Prompts — SplitMiner Fixes
Send each prompt in order. Wait for LISA to finish each one before sending the next.

---

## PROMPT 1 — Remove external references from code

In all files inside `SplitMiner/`, remove any references to author names, paper titles, or external sources from docstrings, comments, and print statements.

Specifically:
- Remove any text like `"Based on: Augusto et al. (2017)"`, `"(Augusto et al., 2017)"`, `"Augusto et al."`, `"paper method"`, or any variation that names the algorithm's origin paper.
- In `main.py`, the print line `print("Based on: Augusto et al. (2017)")` should be removed or replaced with a neutral description.
- Module-level docstrings can say what the module does algorithmically but must not name the source paper or authors.

Do not change any logic, only the text of comments, docstrings, and print statements.

---

## PROMPT 2 — Vectorize DFG building and reuse the event log DataFrame

In `SplitMiner/dfg_builder.py`, replace the current `build_dfg` function that iterates over cases one by one with two new functions:

**`build_dfg(log_path)`** — keep a pure-pandas version for reference:
- Load the XES file, convert to DataFrame.
- Sort by `case:concept:name` and `time:timestamp` (stable sort).
- Use `groupby + shift(-1)` to create a `next_activity` column in one vectorized step.
- Filter rows where the next activity belongs to the same case and is not null.
- Count `(concept:name, next_activity)` pairs with `groupby().size()` to build the DFG dict.
- Return `(dfg_dict, activity_freq_dict, event_log_df)` — three values, including the DataFrame.

**`build_dfg_fast(log_path)`** — the preferred variant:
- Load the XES file, convert to DataFrame.
- Call `pm4py.discover_directly_follows_graph(event_log_df)` which is Cython-backed and 10–50× faster.
- Convert the result to a plain `dict` of `{(src, tgt): int}`.
- Return `(dfg_dict, activity_freq_dict, event_log_df)` — three values, including the DataFrame.

Both functions must return the DataFrame as the third return value so it can be reused in later steps without reloading the file.

Update `main.py` to call `build_dfg_fast` and store the returned DataFrame in a variable (e.g. `event_log_df`) that is passed to the subsequent steps.

---

## PROMPT 3 — Fix DFG filtering to use case-based edge frequency

In `SplitMiner/dfg_builder.py`, rewrite the `filter_dfg` function so that when `threshold_type='frequency'` and `event_log_df` is provided, it filters edges by how many **unique cases** contain that edge — not by raw occurrence count.

The current implementation computes `max_freq = max(dfg.values())` and uses that as the normalization denominator. This is broken because self-loops inflate raw occurrence counts, making `max_freq` artificially large and causing the filter to eliminate most valid edges (leaving as few as 11 forward edges for 22 activities).

New logic for `threshold_type='frequency'` when `event_log_df` is not None:

1. Sort `event_log_df` by `case:concept:name` and `time:timestamp`.
2. Use `groupby + shift(-1)` to get the next activity within each case.
3. For each `(src, tgt)` pair, count the number of **distinct cases** in which that pair appears: `groupby(['concept:name', '_next'])['case:concept:name'].nunique()`.
4. Compute `num_cases = event_log_df['case:concept:name'].nunique()`.
5. Compute `min_cases = max(threshold_value * num_cases, 2)`.
6. Keep only edges where the case count is ≥ `min_cases`.

Keep the old occurrence-based logic as a fallback when `event_log_df is None`.

Update the function signature to accept an optional `event_log_df` parameter:
```python
def filter_dfg(dfg, activity_freq, threshold_type='frequency', threshold_value=0.02, event_log_df=None)
```

Update `main.py` to pass `event_log_df=event_log_df` when calling `filter_dfg`, and set `FILTER_THRESHOLD_VALUE = 0.15`.

---

## PROMPT 4 — Add source/sink injection after filtering

In `SplitMiner/dfg_builder.py`, add a new function `add_source_sink_to_filtered_dfg` that runs **after** the DFG has been filtered. It must never be called before filtering, because source/sink edges must not be subject to removal.

Function signature:
```python
def add_source_sink_to_filtered_dfg(dfg, activity_freq, event_log_df,
                                     start_marker='>>', end_marker='<<')
```

Logic:
1. Sort `event_log_df` by `case:concept:name` and `time:timestamp`.
2. Use `groupby('case:concept:name')['concept:name'].first()` to get the first activity of each case.
3. Use `groupby('case:concept:name')['concept:name'].last()` to get the last activity of each case.
4. Count how many cases start with each activity (`Counter(first_acts.values)`) and add edges `(start_marker, activity)` with those counts to the DFG.
5. Count how many cases end with each activity (`Counter(last_acts.values)`) and add edges `(activity, end_marker)` with those counts.
6. Add `start_marker` and `end_marker` to `activity_freq` with the total case count.
7. Return the updated `(dfg, activity_freq)` tuple.

Also add a second function `add_source_sink_to_log(event_log_df, start_marker='>>', end_marker='<<')` that inserts synthetic start/end events into every trace (used later for replay):
1. For each case, add a row with `concept:name = start_marker` and `time:timestamp = case_min_timestamp - 24h`.
2. For each case, add a row with `concept:name = end_marker` and `time:timestamp = case_max_timestamp + 24h`.
3. Concatenate with the original DataFrame, sort by `(case:concept:name, time:timestamp)` with stable sort, and return.

Update `main.py` to call `add_source_sink_to_filtered_dfg` immediately after `filter_dfg`, and set:
```python
start_activities = {'>>'}
end_activities = {'<<'}
```
(Do not call `get_start_activities` / `get_end_activities` for the export step — only use `>>` and `<<`.)

---

## PROMPT 5 — Vectorize concurrency detection

In `SplitMiner/concurrency.py`, replace the current `detect_concurrency` function (which loops over every case and every candidate pair) with a vectorized implementation called `detect_concurrency_fast`.

New function signature:
```python
def detect_concurrency_fast(event_log_df, dfg, min_support=0.01)
```

It takes the pre-loaded DataFrame (not a file path) and returns a set of concurrent activity pairs.

Algorithm:
1. From `dfg`, collect all activities that appear as both sources and targets.
2. Sort `event_log_df` by case and timestamp. Use `groupby + shift` to build a next-activity column.
3. For each pair `(A, B)` where both `(A→B)` and `(B→A)` exist in the DFG:
   a. Count unique cases containing the edge `A→B`.
   b. Count unique cases containing the edge `B→A`.
   c. If both counts ≥ `min_support * num_cases`, the pair is concurrent.
4. Use `set` of canonical pairs `(min(A,B), max(A,B))` as the return value.

This replaces the slow O(pairs × cases) approach. Use `groupby().nunique()` to count cases per edge in a single pass over the DataFrame (you can reuse the same shifted DataFrame from step 2).

Update `main.py` to call `detect_concurrency_fast(event_log_df=event_log_df, dfg=dfg_filtered, min_support=MIN_CONCURRENCY_SUPPORT)`, passing the DataFrame directly instead of the log path.

---

## PROMPT 6 — Validate AND join gateways

In `SplitMiner/gateway_discovery.py`, after all split and join gateways have been discovered, add a validation pass that downgrades AND join gateways to XOR when there is no corresponding AND split gateway.

Add this logic inside `discover_all_gateways` (or in a new helper `validate_and_joins`) after both `split_gateways` and `join_gateways` have been populated:

```
For each activity that has an AND join gateway:
    Get the set of predecessor activities (from the DFG).
    Check whether any AND split gateway exists such that its successor set
    contains all of those predecessors.
    If no such AND split exists → downgrade the join to XOR.
```

Build a `successors` dict from the DFG to check which activities an AND split can reach.

This prevents unsound Petri nets where tokens accumulate at AND joins that were never preceded by a matching AND split.

---

## PROMPT 7 — Fix PNML export: mark invisible transitions correctly

In `SplitMiner/bpmn_exporter.py`, in the `export_pnml` function, find where tau (invisible) transitions are created in the XML.

When a transition has no visible label (i.e. it is a routing transition added for gateway logic), the PNML `<transition>` element must include a specific `<toolspecific>` child element so that pm4py's PNML importer recognizes the transition as invisible.

Without this element, pm4py sets `trans_visible = True` for every transition, uses the transition's `id` attribute as its label, and then alignment-based replay charges a move cost for every such transition — causing fitness to drop from ~0.94 to ~0.22.

For every transition that should be invisible (label is None or empty), add this child element inside the `<transition>` tag:
```xml
<toolspecific tool="ProM" version="6.4" activity="$invisible$"/>
```

Concretely, in the Python XML construction (using `xml.etree.ElementTree`):
```python
ts = ET.SubElement(transition_element, 'toolspecific')
ts.set('tool', 'ProM')
ts.set('version', '6.4')
ts.set('activity', '$invisible$')
```

This must be added for every transition whose label is None (tau/routing transitions). Transitions that represent real activities keep their label and must NOT get this element.

---

## PROMPT 8 — Fix fitness evaluation: use alignment-based replay

In `SplitMiner/metrics.py`, replace or supplement the token-based replay fitness calculation with alignment-based fitness.

Add a helper function `_run_alignments(event_log_df, net, initial_marking, final_marking)`:

```python
from pm4py.algo.evaluation.replay_fitness import algorithm as rf_algo
from pm4py.algo.evaluation.replay_fitness.variants import alignment_based as ab_variant

def _run_alignments(event_log_df, net, initial_marking, final_marking):
    from SplitMiner.dfg_builder import add_source_sink_to_log
    log_with_ss = add_source_sink_to_log(event_log_df)
    result = rf_algo.apply(
        log_with_ss, net, initial_marking, final_marking,
        variant=ab_variant
    )
    fitness = result.get('log_fitness', result.get('average_trace_fitness', None))
    return float(fitness) if fitness is not None else None
```

In the main `evaluate_model` function:
1. Try to compute alignment fitness using `_run_alignments`. If it succeeds, use it as `fitness_score`.
2. If alignment raises an exception, fall back to token-based replay (`pm4py.fitness_token_based_replay`) and use `perc_fit_traces` as fitness.
3. Keep the token-based replay result available for `generalization_score` calculation regardless.

Make sure `evaluate_model` accepts and passes `event_log_df` (the DataFrame) directly — it must not reload the log from disk.

---

## PROMPT 9 — Add rare variant pre-filtering

In `SplitMiner/dfg_builder.py`, add a function `filter_rare_variants(event_log_df, min_variant_freq=3)` that removes cases whose activity sequence (ordered by timestamp) appears fewer than `min_variant_freq` times across all cases.

Logic:
1. Sort by `case:concept:name` and `time:timestamp`.
2. Build a variant per case: `groupby('case:concept:name')['concept:name'].apply(tuple)`.
3. Count variant occurrences: `variant_counts = case_variants.value_counts()`.
4. Keep only cases whose variant appears ≥ `min_variant_freq` times.
5. Return the filtered DataFrame.

Print a summary line: how many cases and variants were kept vs. removed.

In `main.py`, add a pre-processing step between "Build DFG" and "Filter DFG":
```python
FILTER_RARE_VARIANTS = True
MIN_VARIANT_FREQ = 3
```

If `FILTER_RARE_VARIANTS` is True:
1. Call `filter_rare_variants(event_log_df, MIN_VARIANT_FREQ)` to get a filtered DataFrame.
2. Rebuild the DFG from the filtered DataFrame using `pm4py.discover_directly_follows_graph`.
3. Recompute `activity_freq` from the filtered DataFrame.

This removes noise traces before the main filtering step.

---

## PROMPT 10 — Final main.py wiring and configuration review

Review `SplitMiner/main.py` end-to-end and make sure all steps are wired together correctly:

1. **Step 1** calls `build_dfg_fast(EVENT_LOG_PATH)` and stores `dfg_raw, activity_freq, event_log_df`.
2. **Step 1.5** optionally calls `filter_rare_variants` and rebuilds DFG if `FILTER_RARE_VARIANTS=True`.
3. **Step 2** calls `filter_dfg(dfg_raw, activity_freq, threshold_type='frequency', threshold_value=0.15, event_log_df=event_log_df)`, then immediately calls `add_source_sink_to_filtered_dfg(dfg_filtered, activity_freq, event_log_df)` to get the final `dfg_filtered` and updated `activity_freq`.
4. **Step 3** calls `detect_concurrency_fast(event_log_df=event_log_df, dfg=dfg_filtered, min_support=MIN_CONCURRENCY_SUPPORT)`.
5. **Step 4** calls `discover_all_gateways(dfg_filtered, concurrent_pairs, activity_freq)`.
6. **Step 5** calls `get_loop_structures(dfg_filtered)`.
7. **Step 6** exports BPMN and PNML, passing `start_activities={'>>'}` and `end_activities={'<<'}` explicitly (do not use `get_start_activities` / `get_end_activities` here).
8. **Step 7** generates the PNG visualization from the PNML.
9. **Step 8** calls `evaluate_model(event_log_df, dfg_filtered, start_activities, end_activities, pnml_file, split_gateways, join_gateways)`.

The configuration constants at the top of `main.py` must include:
```python
FILTER_THRESHOLD_TYPE = 'frequency'
FILTER_THRESHOLD_VALUE = 0.15
MIN_CONCURRENCY_SUPPORT = 0.01
FILTER_RARE_VARIANTS = True
MIN_VARIANT_FREQ = 3
```

Make sure no step reloads the event log from disk after Step 1 — every subsequent step receives `event_log_df` as a parameter.

Remove any remaining references to paper author names, publication titles, or phrases like "paper method" from all print statements, comments, and docstrings across all files in `SplitMiner/`.
