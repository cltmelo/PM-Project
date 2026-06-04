from event_log import build_directly_follows_graph_with_frequency
from cut_detection import (
    detect_rule_a,
    detect_rule_b,
    detect_rule_c,
    detect_rule_d
)


MAX_RECURSION_DEPTH = 20


def discover_process_tree(df_sublog, depth=0):
    """
    Recursively discover a process tree from an event log DataFrame.
    """
    
    case_col = 'case:concept:name'
    activity_col = 'concept:name'
    
    if depth > MAX_RECURSION_DEPTH:
        all_activities = set(df_sublog[activity_col].unique()) if len(df_sublog) > 0 else set()
        return {"operator": "FLOWER", "activities": sorted(list(all_activities))}
    
    if len(df_sublog) == 0:
        return {"operator": "SILENT", "activity": "τ"}
    
    all_activities = set(df_sublog[activity_col].unique())
    
    original_arcs, original_arc_freq, start_activities, end_activities = \
        build_directly_follows_graph_with_frequency(df_sublog)
    
    if len(all_activities) == 1:
        activity_name = list(all_activities)[0]
        
        if (activity_name, activity_name) in original_arcs:
            return {
                "operator": "D",
                "children": [
                    {"operator": "LEAF", "activity": activity_name},
                    {"operator": "SILENT", "activity": "τ"}
                ]
            }
        else:
            return {"operator": "LEAF", "activity": activity_name}
    
    winning_rule = None
    rule_result = None
    
    result_a = detect_rule_a(original_arcs, start_activities, end_activities)
    if result_a is not None:
        winning_rule = 'A'
        rule_result = result_a
    
    if winning_rule is None:
        result_b = detect_rule_b(original_arcs, start_activities, end_activities)
        if result_b is not None:
            winning_rule = 'B'
            rule_result = result_b
    
    if winning_rule is None:
        result_c = detect_rule_c(original_arcs, start_activities, end_activities)
        if result_c is not None:
            winning_rule = 'C'
            rule_result = result_c
    
    if winning_rule is None:
        result_d = detect_rule_d(original_arcs, start_activities, end_activities)
        if result_d is not None:
            winning_rule = 'D'
            rule_result = result_d
    
    if winning_rule is None:
        working_arcs = set(original_arcs)
        max_arcs_to_remove = int(len(original_arcs) * 0.30)
        arcs_removed_count = 0
        
        while True:
            if arcs_removed_count >= max_arcs_to_remove or len(working_arcs) == 0:
                break
            
            if detect_rule_a(working_arcs, start_activities, end_activities) is not None:
                winning_rule = 'A'
                rule_result = detect_rule_a(working_arcs, start_activities, end_activities)
                break
            
            if detect_rule_b(working_arcs, start_activities, end_activities) is not None:
                winning_rule = 'B'
                rule_result = detect_rule_b(working_arcs, start_activities, end_activities)
                break
            
            if detect_rule_c(working_arcs, start_activities, end_activities) is not None:
                winning_rule = 'C'
                rule_result = detect_rule_c(working_arcs, start_activities, end_activities)
                break
            
            if detect_rule_d(working_arcs, start_activities, end_activities) is not None:
                winning_rule = 'D'
                rule_result = detect_rule_d(working_arcs, start_activities, end_activities)
                break
            
            min_freq = float('inf')
            min_arc = None
            
            for arc in working_arcs:
                freq = original_arc_freq.get(arc, 1)
                if freq < min_freq:
                    min_freq = freq
                    min_arc = arc
            
            if min_arc is not None:
                working_arcs = working_arcs - {min_arc}
                arcs_removed_count += 1
            else:
                break
    
    if winning_rule is None:
        return {"operator": "FLOWER", "activities": sorted(list(all_activities))}
    
    if winning_rule == 'A':
        groups = rule_result
        case_to_group = {}
        
        for case_id in df_sublog[case_col].unique():
            case_activities = set(df_sublog[df_sublog[case_col] == case_id][activity_col])
            best_group_idx = 0
            best_overlap = 0
            
            for i, group in enumerate(groups):
                overlap = len(case_activities & group)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_group_idx = i
            
            case_to_group[case_id] = best_group_idx
        
        child_sublogs = []
        for i, group in enumerate(groups):
            case_ids_for_group = [cid for cid, gidx in case_to_group.items() if gidx == i]
            sublog = df_sublog[df_sublog[case_col].isin(case_ids_for_group)].copy().reset_index(drop=True)
            child_sublogs.append(sublog)
        
        children = [discover_process_tree(sl, depth + 1) for sl in child_sublogs]
    
    elif winning_rule in ['B', 'C']:
        groups = rule_result
        child_sublogs = []
        for group in groups:
            sublog = df_sublog[df_sublog[activity_col].isin(group)].copy().reset_index(drop=True)
            child_sublogs.append(sublog)
        
        children = [discover_process_tree(sl, depth + 1) for sl in child_sublogs]
    
    elif winning_rule == 'D':
        main_group, return_groups = rule_result
        
        main_sublog = df_sublog[df_sublog[activity_col].isin(main_group)].copy().reset_index(drop=True)
        main_tree = discover_process_tree(main_sublog, depth + 1)
        
        if len(return_groups) == 1:
            return_sublog = df_sublog[df_sublog[activity_col].isin(return_groups[0])].copy().reset_index(drop=True)
            return_tree = discover_process_tree(return_sublog, depth + 1)
            children = [main_tree, return_tree]
        
        elif len(return_groups) >= 2:
            choice_children = []
            
            for return_group in return_groups:
                return_sublog = df_sublog[df_sublog[activity_col].isin(return_group)].copy().reset_index(drop=True)
                return_tree = discover_process_tree(return_sublog, depth + 1)
                choice_children.append(return_tree)
            
            redo_choice_node = {"operator": "A", "children": choice_children}
            children = [main_tree, redo_choice_node]
        
        else:
            children = [main_tree]
    
    parent_activities = all_activities
    
    split_invalid = False
    for child_tree in children:
        def get_tree_activities(tree):
            if tree["operator"] == "LEAF" or tree["operator"] == "SILENT":
                return {tree.get("activity", "")}
            elif tree["operator"] == "FLOWER":
                return set(tree["activities"])
            else:
                acts = set()
                for c in tree["children"]:
                    acts.update(get_tree_activities(c))
                return acts
        
        child_activities = get_tree_activities(child_tree)
        if child_activities == parent_activities:
            split_invalid = True
            break
    
    if split_invalid:
        return {"operator": "FLOWER", "activities": sorted(list(all_activities))}
    
    return {"operator": winning_rule, "children": children}


def print_process_tree(tree, indent=0):
    """
    Print a process tree with proper indentation.
    """
    prefix = "    " * indent
    
    if tree["operator"] == "LEAF":
        print(f"{prefix}· {tree['activity']}")
    
    elif tree["operator"] == "SILENT":
        print(f"{prefix}· τ")
    
    elif tree["operator"] == "FLOWER":
        activities_str = ", ".join(tree["activities"])
        print(f"{prefix}⊕ FLOWER({activities_str})")
    
    else:
        operator_names = {
            'A': '× (Exclusive Choice)',
            'B': '→ (Sequence)',
            'C': '∧ (Parallel)',
            'D': '⟳ (Loop)'
        }
        op_name = operator_names.get(tree["operator"], tree["operator"])
        print(f"{prefix}[{op_name}]")
        
        for child in tree["children"]:
            print_process_tree(child, indent + 1)