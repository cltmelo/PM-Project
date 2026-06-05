import json
from datetime import datetime
from collections import defaultdict


# ============================================================================
# HIGH-PERFORMANCE DATA EXTRACTION
# ============================================================================

def extract_net_structure_fast(net):
    """
    Extract Petri net into pre-indexed Python structures for O(1) lookups.
    
    Creates:
    - input_arcs: dict mapping transition_index -> list of input place indices
    - output_arcs: dict mapping transition_index -> list of output place indices
    - place_to_trans: dict mapping place_index -> list of output transition indices
    - label_to_trans: dict mapping label (str) -> list of transition indices
    - silent_trans: set of transition indices with label None
    - all_places: list of place objects by index
    - all_trans: list of transition objects by index
    - all_places_set: set of all place objects
    """
    num_trans = len(net.transitions)
    num_places = len(net.places)
    
    # Map objects to indices for fast lookup
    trans_to_idx = {t: i for i, t in enumerate(net.transitions)}
    place_to_idx = {p: i for i, p in enumerate(net.places)}
    
    # Initialize arc lists
    input_arcs = [[] for _ in range(num_trans)]  # list of input place indices per trans
    output_arcs = [[] for _ in range(num_trans)]  # list of output place indices per trans
    place_to_trans = [[] for _ in range(num_places)]  # list of output trans per place
    
    # Build arc structures
    for arc in net.arcs:
        src, tgt = arc.source, arc.target
        
        src_idx = trans_to_idx.get(src)
        tgt_idx = trans_to_idx.get(tgt)
        src_pidx = place_to_idx.get(src)
        tgt_pidx = place_to_idx.get(tgt)
        
        if src_idx is not None and tgt_pidx is not None:
            # Transition -> Place (output arc for transition)
            output_arcs[src_idx].append(tgt_pidx)
        
        if tgt_idx is not None and src_pidx is not None:
            # Place -> Transition (input arc for transition)
            input_arcs[tgt_idx].append(src_pidx)
            place_to_trans[src_pidx].append(tgt_idx)
    
    # Build label to transitions mapping
    label_to_trans = defaultdict(list)
    silent_trans = set()
    
    for i, trans in enumerate(net.transitions):
        label = trans.label
        if label is None:
            silent_trans.add(i)
        else:
            label_to_trans[label].append(i)
    
    return {
        'input_arcs': input_arcs,
        'output_arcs': output_arcs,
        'place_to_trans': place_to_trans,
        'label_to_trans': dict(label_to_trans),
        'silent_trans': silent_trans,
        'all_places': list(net.places),
        'all_trans': list(net.transitions),
        'num_trans': num_trans,
        'num_places': num_places
    }


# ============================================================================
# HIGH-PERFORMANCE LOG PREPROCESSING
# ============================================================================

def preprocess_log_fast(df):
    """
    Pre-process log once: group by case, extract traces.
    
    Returns:
    - traces: list of activity name lists (one per case)
    - case_info: dict with aggregated statistics
    """
    case_col = 'case:concept:name'
    activity_col = 'concept:name'
    
    # Group by case once using groupby
    grouped = df.groupby(case_col)[activity_col].apply(list)
    traces = grouped.tolist()
    
    # Get statistics
    all_activities = set()
    for trace in traces:
        all_activities.update(trace)
    
    case_info = {
        'num_cases': len(traces),
        'num_events': len(df),
        'num_activities': len(all_activities),
        'activities': sorted(list(all_activities)),
        'unique_traces': len(set(tuple(t) for t in traces))
    }
    
    return traces, case_info


# ============================================================================
# OPTIMIZED TOKEN-BASED REPLAY
# ============================================================================

def replay_trace_fast(trace, net_struct, init_marking_list):
    """
    Optimized trace replay with in-place state updates.
    
    Parameters:
    - trace: list of activity names
    - net_struct: pre-indexed net structure
    - init_marking_list: list of token counts (mutated in place)
    
    Returns:
    - missing: count of missing tokens
    - remaining: sum of tokens after replay
    """
    input_arcs = net_struct['input_arcs']
    output_arcs = net_struct['output_arcs']
    label_to_trans = net_struct['label_to_trans']
    silent_trans = net_struct['silent_trans']
    num_trans = net_struct['num_trans']
    
    missing = 0
    num_places = net_struct['num_places']
    
    # Marking as list (index = place index)
    marking = init_marking_list.copy()
    
    # Fire initial silent transitions
    changed = True
    while changed:
        changed = False
        for tidx in range(num_trans):
            if tidx in silent_trans:
                # Check if enabled
                enabled = True
                for pidx in input_arcs[tidx]:
                    if marking[pidx] < 1:
                        enabled = False
                        break
                
                if enabled:
                    for pidx in input_arcs[tidx]:
                        marking[pidx] -= 1
                    for pidx in output_arcs[tidx]:
                        marking[pidx] += 1
                    changed = True
                    break
    
    # Process activities
    for activity in trace:
        trans_list = label_to_trans.get(activity)
        
        if not trans_list:
            missing += 1
            continue
        
        # Find enabled transition
        fired = False
        for tidx in trans_list:
            enabled = True
            for pidx in input_arcs[tidx]:
                if marking[pidx] < 1:
                    enabled = False
                    break
            
            if enabled:
                # Fire it
                for pidx in input_arcs[tidx]:
                    marking[pidx] -= 1
                for pidx in output_arcs[tidx]:
                    marking[pidx] += 1
                fired = True
                break
        
        if not fired:
            missing += 1
        
        # Fire silent transitions after each activity
        changed = True
        while changed:
            changed = False
            for tidx in range(num_trans):
                if tidx in silent_trans:
                    enabled = True
                    for pidx in input_arcs[tidx]:
                        if marking[pidx] < 1:
                            enabled = False
                            break
                    
                    if enabled:
                        for pidx in input_arcs[tidx]:
                            marking[pidx] -= 1
                        for pidx in output_arcs[tidx]:
                            marking[pidx] += 1
                        changed = True
                        break
    
    # Count remaining tokens
    remaining = sum(marking)
    
    return missing, remaining


def calculate_fitness_fast(traces, net_struct, init_marking_list):
    """
    Calculate fitness for all traces efficiently.
    
    Parameters:
    - traces: list of activity name lists
    - net_struct: pre-indexed net structure
    - init_marking_list: initial marking as list
    
    Returns:
    - fitness: float [0, 1]
    - details: dict with breakdown
    """
    total_missing = 0
    total_remaining = 0
    total_activities = 0
    
    # Process all traces
    for trace in traces:
        missing, remaining = replay_trace_fast(trace, net_struct, init_marking_list)
        total_missing += missing
        total_remaining += remaining
        total_activities += len(trace)
    
    # Calculate fitness
    if total_activities == 0:
        fitness = 1.0
    else:
        fitness = 1.0 - ((total_missing + total_remaining) / (2.0 * total_activities))
    
    fitness = max(0.0, min(1.0, fitness))
    
    details = {
        'fitness': fitness,
        'total_traces': len(traces),
        'total_activities': total_activities,
        'total_missing_tokens': total_missing,
        'total_remaining_tokens': total_remaining
    }
    
    return details


def calculate_simplicity_fast(net):
    """Calculate simplicity: 1 / (1 + num_arcs)."""
    num_arcs = len(net.arcs)
    return 1.0 / (1.0 + float(num_arcs))


# ============================================================================
# METRICS COLLECTION AND EXPORT
# ============================================================================

def collect_metrics(df, net, initial_marking, final_marking):
    """
    Collect all metrics and return as a dictionary.
    Main entry point for the external framework.
    """
    # Pre-process log once
    traces, case_info = preprocess_log_fast(df)
    
    # Pre-index net once
    net_struct = extract_net_structure_fast(net)
    
    # Convert initial marking to list
    init_marking_list = [0] * net_struct['num_places']
    for place, count in initial_marking.items():
        for i, p in enumerate(net_struct['all_places']):
            if p == place:
                init_marking_list[i] = count
                break
    
    # Calculate fitness
    fitness_details = calculate_fitness_fast(traces, net_struct, init_marking_list)
    fitness_score = fitness_details['fitness']
    
    # Calculate simplicity
    simplicity_score = calculate_simplicity_fast(net)
    
    # Precision (placeholder until implemented)
    precision_score = 1.0
    
    # Overall score
    overall_score = 0.4 * fitness_score + 0.3 * precision_score + 0.3 * simplicity_score
    
    # F-score
    if fitness_score + precision_score > 0:
        f_score = 2.0 * (fitness_score * precision_score) / (fitness_score + precision_score)
    else:
        f_score = 0.0
    
    # Build JSON structure (exact same format as before)
    metrics = {
        'overall_score': overall_score,
        'fitness_score': fitness_score,
        'simplicity_score': simplicity_score,
        'activities': case_info['activities'],
        'algorithm': 'inductive miner',
        'timestamp': datetime.now().isoformat(),
        'event_log': {
            'num_cases': case_info['num_cases'],
            'num_events': case_info['num_events'],
            'num_activities': case_info['num_activities']
        },
        'model_structure': {
            'num_places': net_struct['num_places'],
            'num_transitions': net_struct['num_trans'],
            'num_arcs': len(net.arcs)
        },
        'quality_metrics': {
            'fitness_details': fitness_details,
            'precision_details': {
                'precision': precision_score
            },
            'f_score': f_score
        }
    }
    
    return metrics


def save_metrics(metrics, output_path='output/result_scores.json'):
    """Save metrics dictionary to JSON file."""
    import os
    
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2)