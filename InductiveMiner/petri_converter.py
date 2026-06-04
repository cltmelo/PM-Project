def dict_to_pm4py_tree(node, parent=None):
    """
    Recursively convert custom process tree dictionary to pm4py ProcessTree objects.
    
    Maps our operators to pm4py ProcessTree structure:
        - 'A' → XOR (Exclusive Choice)
        - 'B' → SEQUENCE
        - 'C' → PARALLEL
        - 'D' → LOOP (with main body and redo path)
        - 'LEAF' → Activity leaf node
        - 'SILENT' → Silent transition (τ)
        - 'FLOWER' → XOR of all activities (approximation)
    
    Parameters:
        node: Dictionary representing a process tree node
        parent: Parent pm4py ProcessTree node (for linking)
    
    Returns:
        pm4py.objects.process_tree.obj.ProcessTree object
    """
    from pm4py.objects.process_tree.obj import ProcessTree
    from pm4py.objects.process_tree.obj import Operator
    
    operator = node.get("operator", "")
    
    # ============================================================
    # LEAF Node: Create activity node
    # ============================================================
    if operator == "LEAF":
        activity_name = node.get("activity", "unknown")
        
        # CRITICAL FIX: Use keyword argument 'label=' for leaf nodes
        pt_node = ProcessTree(label=activity_name)
        
        if parent is not None:
            parent.children.append(pt_node)
            pt_node.parent = parent
        
        return pt_node
    
    # ============================================================
    # SILENT Node: Create silent transition (τ)
    # ============================================================
    elif operator == "SILENT":
        # CRITICAL FIX: Use keyword argument 'label=None' for silent transitions
        pt_node = ProcessTree(label=None)
        
        if parent is not None:
            parent.children.append(pt_node)
            pt_node.parent = parent
        
        return pt_node
    
    # ============================================================
    # FLOWER Node: Approximate as XOR of all activities
    # ============================================================
    elif operator == "FLOWER":
        activities = node.get("activities", [])
        
        # CRITICAL FIX: Use keyword argument 'operator=' for operator nodes
        pt_node = ProcessTree(operator=Operator.XOR)
        
        if parent is not None:
            parent.children.append(pt_node)
            pt_node.parent = parent
        
        # Add each activity as a child leaf
        for activity in activities:
            if activity == "τ":
                child = ProcessTree(label=None)  # Silent
            else:
                child = ProcessTree(label=activity)
            pt_node.children.append(child)
            child.parent = pt_node
        
        return pt_node
    
    # ============================================================
    # Internal Operator Nodes (A, B, C, D)
    # ============================================================
    else:
        # Map our operators to pm4py operators
        # CRITICAL FIX: Use 'Operator.PARALLEL' not 'Operator.AND'
        operator_mapping = {
            'A': Operator.XOR,       # Exclusive Choice
            'B': Operator.SEQUENCE,  # Sequence
            'C': Operator.PARALLEL,  # Parallel (FIXED from Operator.AND)
            'D': Operator.LOOP       # Loop
        }
        
        pm4py_operator = operator_mapping.get(operator, Operator.XOR)
        
        # CRITICAL FIX: Use keyword argument 'operator=' for operator nodes
        pt_node = ProcessTree(operator=pm4py_operator)
        
        if parent is not None:
            parent.children.append(pt_node)
            pt_node.parent = parent
        
        # Recursively process children
        children = node.get("children", [])
        
        for child_node in children:
            dict_to_pm4py_tree(child_node, parent=pt_node)
        
        return pt_node


def export_tree_to_pnml(custom_tree, output_path):
    """
    Export a custom process tree dictionary to PNML format.
    
    Uses pm4py for conversion and I/O (allowed per project rules).
    
    Parameters:
        custom_tree: Dictionary representing the process tree
        output_path: Path to save the PNML file
    
    Returns:
        True if successful, False otherwise
    """
    import os
    
    try:
        # Lazy load pm4py (only when needed)
        import pm4py
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Convert custom tree to pm4py ProcessTree
        pm4py_tree = dict_to_pm4py_tree(custom_tree)
        
        # Convert ProcessTree to Petri Net
        petri_net, initial_marking, final_marking = pm4py.convert_to_petri_net(pm4py_tree)
        
        # Assign internal name to the Petri net object
        petri_net.name = 'InductiveMinerResult'
        
        # Export to PNML
        pm4py.write_pnml(petri_net, initial_marking, final_marking, output_path)
        
        print(f"✓ Process model exported to: {output_path}")
        return True
        
    except Exception as e:
        print(f"✗ Error exporting to PNML: {e}")
        return False