def detect_rule_a(arcs, start_activities, end_activities):
    """
    Rule A: Groups with no connection (Exclusive Choice cut)
    
    Find connected components in the undirected version of the graph.
    Each component must have at least one start AND one end activity.
    
    Returns:
        List of sets (groups) if 2+ valid groups found, else None
    """
    
    all_activities = set()
    for a, b in arcs:
        all_activities.add(a)
        all_activities.add(b)
    
    if len(all_activities) == 0:
        return None
    
    adjacency = {act: set() for act in all_activities}
    
    for a, b in arcs:
        adjacency[a].add(b)
        adjacency[b].add(a)
    
    visited = set()
    components = []
    
    for start_node in all_activities:
        if start_node not in visited:
            component = set()
            queue = [start_node]
            
            while queue:
                node = queue.pop(0)
                if node not in visited:
                    visited.add(node)
                    component.add(node)
                    for neighbor in adjacency[node]:
                        if neighbor not in visited:
                            queue.append(neighbor)
            
            components.append(component)
    
    valid_components = []
    
    for comp in components:
        has_start = len(comp & start_activities) > 0
        has_end = len(comp & end_activities) > 0
        
        if has_start and has_end:
            valid_components.append(comp)
        else:
            return None
    
    if len(valid_components) >= 2:
        return valid_components
    
    return None


def detect_rule_b(arcs, start_activities, end_activities):
    """
    Rule B: Groups in strict order (Sequence cut)
    
    Uses Strongly Connected Components (SCCs) to detect sequence structure.
    Activities in cycles belong to same SCC. SCCs form a DAG that can be
    topologically ordered.
    
    Returns:
        List of sets (ordered groups) if 2+ SCCs found, else None
    """
    
    all_activities = set()
    for a, b in arcs:
        all_activities.add(a)
        all_activities.add(b)
    
    if len(all_activities) < 2:
        return None
    
    adjacency = {act: [] for act in all_activities}
    for a, b in arcs:
        adjacency[a].append(b)
    
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = {}
    sccs = []
    
    def strongconnect(node):
        index[node] = index_counter[0]
        lowlink[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True
        
        for successor in adjacency.get(node, []):
            if successor not in index:
                strongconnect(successor)
                lowlink[node] = min(lowlink[node], lowlink[successor])
            elif on_stack.get(successor, False):
                lowlink[node] = min(lowlink[node], index[successor])
        
        if lowlink[node] == index[node]:
            scc = set()
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.add(w)
                if w == node:
                    break
            sccs.append(scc)
    
    for node in all_activities:
        if node not in index:
            strongconnect(node)
    
    if len(sccs) < 2:
        return None
    
    activity_to_scc = {}
    for scc_idx, scc in enumerate(sccs):
        for act in scc:
            activity_to_scc[act] = scc_idx
    
    condensation_edges = set()
    for a, b in arcs:
        scc_a = activity_to_scc[a]
        scc_b = activity_to_scc[b]
        if scc_a != scc_b:
            condensation_edges.add((scc_a, scc_b))
    
    condensation_adj = {i: set() for i in range(len(sccs))}
    condensation_in_degree = {i: 0 for i in range(len(sccs))}
    
    for scc_from, scc_to in condensation_edges:
        if scc_to not in condensation_adj[scc_from]:
            condensation_adj[scc_from].add(scc_to)
            condensation_in_degree[scc_to] += 1
    
    queue = [i for i in range(len(sccs)) if condensation_in_degree[i] == 0]
    topological_order = []
    
    while queue:
        node = queue.pop(0)
        topological_order.append(node)
        
        for neighbor in condensation_adj[node]:
            condensation_in_degree[neighbor] -= 1
            if condensation_in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(topological_order) != len(sccs):
        return None
    
    ordered_groups = [sccs[idx] for idx in topological_order]
    
    return ordered_groups


def detect_rule_c(arcs, start_activities, end_activities):
    """
    Rule C: Fully interleaved groups (Parallel cut)
    
    Finds groups where activities are connected via bidirectional arcs only.
    Uses connected components on bidirectional-only graph.
    
    Returns:
        List of sets (parallel groups) if 2+ valid groups found, else None
    """
    
    all_activities = set()
    for a, b in arcs:
        all_activities.add(a)
        all_activities.add(b)
    
    if len(all_activities) < 2:
        return None
    
    arc_set = set(arcs)
    
    bidirectional_arcs = set()
    for a, b in arcs:
        if (b, a) in arc_set:
            bidirectional_arcs.add((a, b))
            bidirectional_arcs.add((b, a))
    
    if len(bidirectional_arcs) == 0:
        return None
    
    adjacency = {act: set() for act in all_activities}
    
    for a, b in bidirectional_arcs:
        adjacency[a].add(b)
        adjacency[b].add(a)
    
    visited = set()
    components = []
    
    for start_node in all_activities:
        if start_node not in visited:
            if len(adjacency[start_node]) == 0:
                visited.add(start_node)
                continue
            
            component = set()
            queue = [start_node]
            
            while queue:
                node = queue.pop(0)
                if node not in visited:
                    visited.add(node)
                    component.add(node)
                    for neighbor in adjacency[node]:
                        if neighbor not in visited:
                            queue.append(neighbor)
            
            if len(component) > 0:
                components.append(component)
    
    valid_components = []
    
    for comp in components:
        has_start = len(comp & start_activities) > 0
        has_end = len(comp & end_activities) > 0
        
        if has_start and has_end:
            valid_components.append(comp)
    
    if len(valid_components) >= 2:
        return valid_components
    
    return None


def detect_rule_d(arcs, start_activities, end_activities):
    """
    Rule D: Loop Cut detection using graph partitioning.
    
    Algorithm:
    1. Initialize main group with all start and end activities
    2. Iteratively merge activities that violate edge rules
    3. Form redo groups from remaining activities
    4. Validate redo groups have proper loop connections
    5. Return (main_group, [redo_groups]) or None
    
    Returns:
        Tuple (main_group, list_of_redo_groups) if valid loop cut found, else None
    """
    
    # Get all unique activities
    all_activities = set()
    for a, b in arcs:
        all_activities.add(a)
        all_activities.add(b)
    
    if len(all_activities) < 2:
        return None
    
    # Build adjacency structures
    outgoing = {act: set() for act in all_activities}
    incoming = {act: set() for act in all_activities}
    
    for a, b in arcs:
        outgoing[a].add(b)
        incoming[b].add(a)
    
    # ============================================================
    # STEP 1: Initialize Main Group with all starts and ends
    # ============================================================
    main_group = set(start_activities | end_activities)
    
    if len(main_group) == 0:
        return None
    
    # ============================================================
    # STEP 2: Enforce Edge Rules (Iterative Merge)
    # ============================================================
    # Merge candidate into main if:
    # - Edge FROM main TO candidate does NOT originate from end activity, OR
    # - Edge FROM candidate TO main does NOT target start activity
    
    changed = True
    
    while changed:
        changed = False
        candidates = all_activities - main_group
        
        for candidate in candidates:
            should_merge = False
            
            # Check edges FROM main group TO candidate
            # If any edge does NOT originate from an end activity → merge
            incoming_from_main = incoming[candidate] & main_group
            for src in incoming_from_main:
                if src not in end_activities:
                    should_merge = True
                    break
            
            if not should_merge:
                # Check edges FROM candidate TO main group
                # If any edge does NOT target a start activity → merge
                outgoing_to_main = outgoing[candidate] & main_group
                for dst in outgoing_to_main:
                    if dst not in start_activities:
                        should_merge = True
                        break
            
            if should_merge:
                main_group.add(candidate)
                changed = True
    
    # ============================================================
    # STEP 3: Check Base Case
    # ============================================================
    # If all activities end up in main_group → return None
    if len(main_group) == len(all_activities):
        return None
    
    # ============================================================
    # STEP 4: Form Redo Groups (connected components)
    # ============================================================
    redo_candidates = all_activities - main_group
    
    # Build undirected adjacency within redo candidates
    redo_adjacency = {act: set() for act in redo_candidates}
    for a, b in arcs:
        if a in redo_candidates and b in redo_candidates:
            redo_adjacency[a].add(b)
            redo_adjacency[b].add(a)
    
    # Find connected components using BFS
    redo_visited = set()
    redo_groups = []
    
    for start_node in redo_candidates:
        if start_node not in redo_visited:
            group = set()
            queue = [start_node]
            
            while queue:
                node = queue.pop(0)
                if node not in redo_visited:
                    redo_visited.add(node)
                    group.add(node)
                    for neighbor in redo_adjacency[node]:
                        if neighbor not in redo_visited:
                            queue.append(neighbor)
            
            if len(group) > 0:
                redo_groups.append(group)
    
    # ============================================================
    # STEP 5: Validate Redo Groups
    # ============================================================
    # Each redo group needs:
    # - At least one incoming edge from an END activity of main_group
    # - At least one outgoing edge to a START activity of main_group
    
    main_end_activities = main_group & end_activities
    main_start_activities = main_group & start_activities
    
    valid_redo_groups = []
    activities_to_merge = set()
    
    for group in redo_groups:
        has_incoming_from_end = False
        has_outgoing_to_start = False
        
        for act in group:
            if not has_incoming_from_end:
                if len(incoming[act] & main_end_activities) > 0:
                    has_incoming_from_end = True
            
            if not has_outgoing_to_start:
                if len(outgoing[act] & main_start_activities) > 0:
                    has_outgoing_to_start = True
            
            if has_incoming_from_end and has_outgoing_to_start:
                break
        
        if has_incoming_from_end and has_outgoing_to_start:
            valid_redo_groups.append(group)
        else:
            activities_to_merge.update(group)
    
    # Merge invalid redo groups back into main
    if activities_to_merge:
        main_group.update(activities_to_merge)
    
    # ============================================================
    # STEP 6: Final Return
    # ============================================================
    if len(valid_redo_groups) == 0:
        return None
    
    # Validate loop connectivity
    has_enter_loop = any(a in main_group and b in redo_candidates for a, b in arcs)
    has_exit_loop = any(a in redo_candidates and b in main_group for a, b in arcs)
    
    if not (has_enter_loop and has_exit_loop):
        return None
    
    return (main_group, valid_redo_groups)