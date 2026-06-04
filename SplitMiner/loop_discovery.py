"""
loop_discovery.py - Detect loops and back-edges in the process model
"""
from typing import Dict, Set, Tuple, List
from collections import defaultdict


def detect_back_edges(dfg: Dict[Tuple[str, str], int]) -> Set[Tuple[str, str]]:
    """Detect back-edges in the DFG that indicate loops (DFS-based)."""
    adj_list = defaultdict(set)
    for (src, tgt) in dfg.keys():
        adj_list[src].add(tgt)

    if not adj_list:
        return set()

    all_nodes = set(adj_list.keys())
    for targets in adj_list.values():
        all_nodes.update(targets)

    incoming = defaultdict(set)
    for (src, tgt) in dfg.keys():
        incoming[tgt].add(src)

    start_nodes = {node for node in all_nodes if node not in incoming}
    if not start_nodes:
        start_nodes = {list(all_nodes)[0]}

    back_edges = set()
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in adj_list.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path + [node])
            elif neighbor in rec_stack:
                # Found a back-edge
                back_edges.add((node, neighbor))

        rec_stack.remove(node)

    # Run DFS from each start node
    for start in start_nodes:
        if start not in visited:
            dfs(start, [])

    # Also check for cycles in disconnected components
    for node in all_nodes:
        if node not in visited:
            dfs(node, [])

    return back_edges


def find_path(adj_list: Dict[str, Set[str]],
              start: str,
              end: str,
              visited: Set[str],
              path: List[str] = None) -> List[str]:
    """Find a path from start to end using DFS."""
    if path is None:
        path = []
    if start == end:
        return path + [start]
    if start in visited:
        return None

    visited.add(start)
    path.append(start)

    for neighbor in adj_list.get(start, []):
        result = find_path(adj_list, neighbor, end, visited, path)
        if result:
            return result

    path.pop()
    visited.remove(start)
    return None


def detect_loops(dfg: Dict[Tuple[str, str], int]) -> List[List[str]]:
    """Detect all loops (cycles) in the process model."""
    back_edges = detect_back_edges(dfg)
    if not back_edges:
        return []

    adj_list = defaultdict(set)
    for (src, tgt) in dfg.keys():
        adj_list[src].add(tgt)

    loops = []
    for (src, tgt) in back_edges:
        path = find_path(adj_list, tgt, src, set())
        if path:
            loops.append(path + [tgt])

    return loops


def is_loop_activity(activity: str,
                     back_edges: Set[Tuple[str, str]],
                     dfg: Dict[Tuple[str, str], int]) -> bool:
    """Check if an activity is part of a loop."""
    for (src, tgt) in back_edges:
        if activity == src or activity == tgt:
            return True
    return False


def get_loop_structures(dfg: Dict[Tuple[str, str], int]) -> dict:
    """Get detailed loop structures for BPMN export."""
    back_edges = detect_back_edges(dfg)
    loops = detect_loops(dfg)

    return {
        'back_edges': list(back_edges),
        'loops': loops,
        'has_loops': len(loops) > 0,
        'loop_count': len(loops)
    }
