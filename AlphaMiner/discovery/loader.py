"""
Event log loading functionality.

Handles loading XES files and converting them to DataFrames.
"""

import gzip
from typing import Tuple
import pandas as pd

import pm4py
from pm4py.objects.conversion.log import converter as log_converter

from ..utils.file_utils import validate_file, get_file_size
from ..utils.logging_utils import print_header, print_info, print_success


class EventLogLoader:
    """
    Loads and validates event logs from XES files.
    
    Example:
        loader = EventLogLoader()
        df = loader.load("path/to/log.xes.gz")
    """
    
    def __init__(self):
        """Initialize the event log loader."""
        self._dataframe: pd.DataFrame = None
        self._num_cases: int = 0
        self._num_events: int = 0
        self._num_activities: int = 0
    
    @property
    def dataframe(self) -> pd.DataFrame:
        """Get the loaded DataFrame."""
        if self._dataframe is None:
            raise ValueError("No event log loaded. Call load() first.")
        return self._dataframe
    
    @property
    def num_cases(self) -> int:
        """Get the number of cases in the log."""
        return self._num_cases
    
    @property
    def num_events(self) -> int:
        """Get the number of events in the log."""
        return self._num_events
    
    @property
    def num_activities(self) -> int:
        """Get the number of unique activities."""
        return self._num_activities
    
    def load(self, log_path: str) -> pd.DataFrame:
        """
        Load an event log from a compressed XES file.
        
        Args:
            log_path: Path to the .xes.gz file
            
        Returns:
            DataFrame with standardized column names:
            - case:concept:name: Case identifier
            - concept:name: Activity name
            - time:timestamp: Event timestamp
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        print_header("LOADING EVENT LOG")
        
        # Validate file
        validate_file(log_path)
        file_size = get_file_size(log_path)
        print_info("File path", log_path)
        print_info("File size", f"{file_size:.2f} MB")
        
        print("\n⏳ Loading event log...")
        
        # Load compressed XES file
        with gzip.open(log_path, 'rb') as log_file:
            event_log = pm4py.read_xes(log_file)
        
        # Convert to DataFrame using pm4py's conversion function
        self._dataframe = log_converter.apply(
            event_log, 
            variant=log_converter.Variants.TO_DATA_FRAME
        )
        
        # Calculate statistics
        self._calculate_statistics()
        
        print_success(f"Loaded {self._num_events:,} events from {self._num_cases:,} cases")
        
        return self._dataframe
    
    def _calculate_statistics(self) -> None:
        """Calculate log statistics from the DataFrame."""
        df = self._dataframe
        self._num_cases = df['case:concept:name'].nunique()
        self._num_events = len(df)
        self._num_activities = df['concept:name'].nunique()
        
        print_info("Traces (cases)", self._num_cases)
        print_info("Total events", self._num_events)
        print_info("Unique activities", self._num_activities)
        
        # Show time range if available
        if 'time:timestamp' in df.columns:
            min_time = df['time:timestamp'].min()
            max_time = df['time:timestamp'].max()
            print_info("Time range", f"{min_time.strftime('%Y-%m-%d')} to {max_time.strftime('%Y-%m-%d')}")