import json
from datetime import datetime
from collections import defaultdict


# ============================================================================
# HIGH-PERFORMANCE DATA EXTRACTION (DETERMINISTIC - FIXED)
# ============================================================================

def extract_net_structure_fast(net):
    """
    Extract Petri net into pre-indexed Python structures for O(1) lookups.
    
    FIXED: All iterations sorted by name attribute for deterministic results.
    
    Creates:
    - input_arcs: list of lists (indexed by transition index)
    - output_arcs: list of lists (indexed by transition index)
    - place_to_trans: list of lists (indexed by place index)
    - label_to_trans: dict mapping label -> list of transition indices
    - silent_trans: set of transition indices with label None
    - all_places: list of place objects (sorted by name)
    - all_trans: list of transition objects (sorted by name)
    """
    # Sort transitions by name for deterministic indexing
    sorted_trans = sorted(net.transitions, key=lambda t: t.name if t.name else '')
    num_trans = len(sorted_trans)
    
    # Sort places by name for deterministic indexing
    sorted_places = sorted(net.places, key=lambda p: p.name if p.name else '')
    num_places = len(sorted_places)
    
    # Map objects to indices
    trans_to_idx = {t: i for i, t in enumerate(sorted_trans)}
    place_to_idx = {p: i for i, p in enumerate(sorted_places)}
    
    # Initialize arc lists
    input_arcs = [[] for _ in range(num_trans)]
    output_arcs = [[] for _ in range(num_trans)]
    place_to_trans = [[] for _ in range(num_places)]
    
    # Build arc structures
    for arc in net.arcs:
        src, tgt = arc.source, arc.target
        
        src_idx = trans_to_idx.get(src)
        tgt_idx = trans_to_idx.get(tgt)
        src_pidx = place_to_idx.get(src)
        tgt_pidx = place_to_idx.get(tgt)
        
        if src_idx is not None and tgt_pidx is not None:
            output_arcs[src_idx].append(tgt_pidx)
        
        if tgt_idx is not None and src_pidx is not None:
            input_arcs[tgt_idx].append(src_pidx)
            place_to_trans[src_pidx].append(tgt_idx)
    
    # Build label to transitions mapping
    label_to_trans = defaultdict(list)
    silent_trans = set()
    
    for i, trans in enumerate(sorted_trans):
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
        'all_places': sorted_places,
        'all_trans': sorted_trans,
        'num_trans': num_trans,
        'num_places': num_places
    }


# ============================================================================
# HIGH-PERFORMANCE LOG PREPROCESSING
# ============================================================================

def preprocess_log_fast(df):
    """
    Pre-process log once: group by case, extract traces.
    """
    case_col = 'case:concept:name'
    activity_col = 'concept:name'
    
    grouped = df.groupby(case_col)[activity_col].apply(list)
    traces = grouped.tolist()
    
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
# OPTIMIZED TOKEN-BASED REPLAY (FITNESS)
# ============================================================================

def fire_silent_transitions(marking, net_struct):
    """
    Fire all possible silent transitions until no more can fire.
    Uses changed flag for efficient iteration.
    """
    input_arcs = net_struct['input_arcs']
    output_arcs = net_struct['output_arcs']
    silent_trans = net_struct['silent_trans']
    num_trans = net_struct['num_trans']
    
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


def replay_trace_fast(trace, net_struct, init_marking_list):
    """
    Optimized trace replay with in-place state updates.
    """
    input_arcs = net_struct['input_arcs']
    output_arcs = net_struct['output_arcs']
    label_to_trans = net_struct['label_to_trans']
    silent_trans = net_struct['silent_trans']
    num_trans = net_struct['num_trans']
    
    marking = init_marking_list.copy()
    
    # Fire initial silent transitions
    fire_silent_transitions(marking, net_struct)
    
    missing = 0
    
    for activity in trace:
        trans_list = label_to_trans.get(activity)
        
        if not trans_list:
            missing += 1
            continue
        
        fired = False
        for tidx in trans_list:
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
                fired = True
                break
        
        if not fired:
            missing += 1
        
        fire_silent_transitions(marking, net_struct)
    
    remaining = sum(marking)
    
    return missing, remaining


def calculate_fitness_fast(traces, net_struct, init_marking_list):
    """
    Calculate fitness for all traces.
    """
    total_missing = 0
    total_remaining = 0
    total_activities = 0
    
    for trace in traces:
        missing, remaining = replay_trace_fast(trace, net_struct, init_marking_list)
        total_missing += missing
        total_remaining += remaining
        total_activities += len(trace)
    
    if total_activities == 0:
        fitness = 1.0
    else:
        fitness = 1.0 - ((total_missing + total_remaining) / (2.0 * total_activities))
    
    fitness = max(0.0, min(1.0, fitness))
    
    return {
        'fitness': fitness,
        'total_traces': len(traces),
        'total_activities': total_activities,
        'total_missing_tokens': total_missing,
        'total_remaining_tokens': total_remaining
    }


# ============================================================================
# ETC PRECISION (IMPLEMENTED - FIXED)
# ============================================================================

def get_enabled_activity_labels(marking, net_struct):
    """
    Get set of activity labels for all enabled transitions.
    Excludes silent transitions (label is None).
    """
    input_arcs = net_struct['input_arcs']
    label_to_trans = net_struct['label_to_trans']
    silent_trans = net_struct['silent_trans']
    num_trans = net_struct['num_trans']
    
    enabled_labels = set()
    
    for tidx in range(num_trans):
        if tidx in silent_trans:
            continue
        
        enabled = True
        for pidx in input_arcs[tidx]:
            if marking[pidx] < 1:
                enabled = False
                break
        
        if enabled:
            # Find the label for this transition
            for label, trans_list in label_to_trans.items():
                if tidx in trans_list:
                    enabled_labels.add(label)
                    break
    
    return enabled_labels


def fire_transition_by_label(marking, net_struct, label):
    """
    Fire a transition by its activity label.
    Returns True if fired, False if not enabled.
    """
    input_arcs = net_struct['input_arcs']
    output_arcs = net_struct['output_arcs']
    label_to_trans = net_struct['label_to_trans']
    
    trans_list = label_to_trans.get(label)
    if not trans_list:
        return False
    
    for tidx in trans_list:
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
            return True
    
    return False


def calculate_etc_precision(traces, net_struct, init_marking_list):
    """
    Calculate Escaping Edges Precision (ETC).
    
    For each activity in each trace:
    1. Collect enabled activity labels (excluding silent)
    2. Count escaping edges = enabled labels that are NOT the current activity
    3. Add to total_enabled and total_escaping
    4. Fire the matching transition if enabled
    5. Fire silent transitions
    
    Precision = 1 - (total_escaping / total_enabled)
    If total_enabled is 0, return 1.0
    """
    total_enabled = 0
    total_escaping = 0
    
    for trace in traces:
        marking = init_marking_list.copy()
        
        # Fire initial silent transitions
        fire_silent_transitions(marking, net_struct)
        
        for activity in trace:
            # Get enabled activity labels before firing
            enabled_labels = get_enabled_activity_labels(marking, net_struct)
            
            # Count escaping edges (enabled but not current activity)
            escaping = len(enabled_labels) - (1 if activity in enabled_labels else 0)
            
            total_enabled += len(enabled_labels)
            total_escaping += escaping
            
            # Fire the matching transition if enabled, else skip
            fired = fire_transition_by_label(marking, net_struct, activity)
            
            # Fire silent transitions
            fire_silent_transitions(marking, net_struct)
    
    # Calculate precision
    if total_enabled == 0:
        precision = 1.0
    else:
        precision = 1.0 - (float(total_escaping) / float(total_enabled))
    
    precision = max(0.0, min(1.0, precision))
    
    return {
        'precision': precision,
        'total_enabled': total_enabled,
        'total_escaping': total_escaping,
        'total_activities': sum(len(t) for t in traces)
    }


# ============================================================================
# SIMPLICITY
# ============================================================================

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
    
    # Calculate ETC precision (FIXED)
    precision_details = calculate_etc_precision(traces, net_struct, init_marking_list)
    precision_score = precision_details['precision']
    
    # Calculate simplicity
    simplicity_score = calculate_simplicity_fast(net)
    
    # Overall score
    overall_score = 0.4 * fitness_score + 0.3 * precision_score + 0.3 * simplicity_score
    
    # F-score
    if fitness_score + precision_score > 0:
        f_score = 2.0 * (fitness_score * precision_score) / (fitness_score + precision_score)
    else:
        f_score = 0.0
    
    # Build JSON structure
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
            'precision_details': precision_details,
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