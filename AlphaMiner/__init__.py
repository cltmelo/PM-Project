"""
Alpha Miner - Process Discovery Package

A modular implementation of the Alpha Miner algorithm for discovering
Petri nets from event logs using pm4py.

Author: University Process Mining Project
"""

from .config import CONFIG
from .discovery.alpha_miner import AlphaMinerDiscoverer
from .discovery.loader import EventLogLoader
from .discovery.preprocessing import LogPreprocessor
from .evaluation.metrics import ProcessMetrics
from .output.pnml_exporter import PNMLExporter
from .output.json_exporter import JSONExporter
from .output.txt_exporter import TXTExporter

__version__ = "1.0.0"
__all__ = [
    "CONFIG",
    "AlphaMinerDiscoverer",
    "EventLogLoader",
    "LogPreprocessor",
    "ProcessMetrics",
    "PNMLExporter",
    "JSONExporter",
    "TXTExporter",
]