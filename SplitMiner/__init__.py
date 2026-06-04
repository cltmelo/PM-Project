"""
SplitMiner - Python Implementation
Automated Discovery of Accurate and Simple Business Process Models from Event Logs

Based on the algorithm by:
Augusto, A., Conforti, R., Dumas, M., La Rosa, M., & Polyvyanyy, A. (2017).
"Split Miner: Automated Discovery of Accurate and Simple Business Process Models from Event Logs"
"""

from .dfg_builder import (
    build_dfg,
    build_dfg_fast,
    filter_dfg,
    get_start_activities,
    get_end_activities
)
from .concurrency import (
    detect_concurrency,
    detect_concurrency_fast,
    is_parallel,
    get_parallel_groups
)
from .gateway_discovery import (
    discover_split_gateway,
    discover_join_gateway,
    discover_all_gateways,
    GatewayType
)
from .loop_discovery import detect_back_edges, detect_loops, get_loop_structures
from .bpmn_exporter import export_model, BPMNExporter
from .metrics import (
    calculate_replay_fitness,
    calculate_precision_petri_net,  # FIX Line 33: Renamed from calculate_precision
    calculate_simplicity,
    calculate_generalization,
    evaluate_model,
    save_metrics
)

__version__ = '1.0.0'
__author__ = 'PM-Project Team'

__all__ = [
    # DFG Builder
    'build_dfg',
    'build_dfg_fast',  # Optimized version
    'filter_dfg',
    'get_start_activities',
    'get_end_activities',

    # Concurrency
    'detect_concurrency',
    'detect_concurrency_fast',  # Optimized version
    'is_parallel',
    'get_parallel_groups',

    # Gateway Discovery
    'discover_split_gateway',
    'discover_join_gateway',
    'discover_all_gateways',
    'GatewayType',

    # Loop Discovery
    'detect_back_edges',
    'detect_loops',
    'get_loop_structures',

    # Export
    'export_model',
    'BPMNExporter',

    # Metrics
    'calculate_replay_fitness',
    'calculate_precision_petri_net',  # FIX Line 74: Renamed from calculate_precision
    'calculate_simplicity',
    'calculate_generalization',
    'evaluate_model',
    'save_metrics'
]
