"""
Event log preprocessing functionality.

Handles filtering and cleaning of event logs before discovery.
"""

from typing import Optional, List, Set
import pandas as pd

from ..utils.logging_utils import print_header, print_info, print_success, print_warning


class LogPreprocessor:
    """
    Preprocesses event logs for process discovery.
    
    Provides filtering capabilities to handle noisy event logs
    and improve discovery quality.
    
    Example:
        preprocessor = LogPreprocessor()
        df_clean = preprocessor.preprocess(df, noise_threshold=50)
    """
    
    def __init__(self):
        """Initialize the preprocessor."""
        self._filtered_activities: Set[str] = set()
        self._events_removed: int = 0
    
    @property
    def filtered_activities(self) -> Set[str]:
        """Get the set of filtered activities."""
        return self._filtered_activities.copy()
    
    @property
    def events_removed(self) -> int:
        """Get the number of events removed."""
        return self._events_removed
    
    def preprocess(
        self,
        df: pd.DataFrame,
        sort_by: Optional[List[str]] = None,
        remove_duplicates: bool = True,
        activity_threshold: int = 0,
    ) -> pd.DataFrame:
        """
        Apply preprocessing steps to the event log.
        
        Args:
            df: Input event log DataFrame
            sort_by: Columns to sort by (default: case, timestamp)
            remove_duplicates: Whether to remove duplicate consecutive events
            activity_threshold: Minimum occurrences for activities (0 = keep all)
            
        Returns:
            Preprocessed DataFrame
        """
        print_header("PREPROCESSING EVENT LOG")
        
        initial_events = len(df)
        print_info("Input events", initial_events)
        
        # Make a copy to avoid modifying the original
        df_processed = df.copy()
        
        # Sort the data
        df_processed = self._sort_log(df_processed, sort_by)
        
        # Remove duplicate consecutive events
        if remove_duplicates:
            df_processed = self._remove_duplicates(df_processed)
        
        # Filter rare activities
        if activity_threshold > 0:
            df_processed = self._filter_rare_activities(df_processed, activity_threshold)
        
        # Calculate statistics
        self._events_removed = initial_events - len(df_processed)
        removal_pct = (self._events_removed / initial_events * 100) if initial_events > 0 else 0
        
        print_success(f"Output events: {len(df_processed):,}")
        print_info("Events removed", f"{self._events_removed:,} ({removal_pct:.2f}%)")
        
        return df_processed
    
    def _sort_log(
        self,
        df: pd.DataFrame,
        sort_by: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Sort the event log by case and timestamp."""
        if sort_by is None:
            sort_by = ['case:concept:name', 'time:timestamp']
        
        df_sorted = df.sort_values(sort_by).reset_index(drop=True)
        print_success("Sorted by case and timestamp")
        
        return df_sorted
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate consecutive events from each case."""
        # Remove rows where activity is same as previous row for same case
        mask = (
            (df['case:concept:name'] == df['case:concept:name'].shift(1)) &
            (df['concept:name'] == df['concept:name'].shift(1))
        )
        
        df_filtered = df[~mask].reset_index(drop=True)
        duplicates_removed = len(df) - len(df_filtered)
        
        if duplicates_removed > 0:
            print_success(f"Removed {duplicates_removed:,} duplicate events")
        else:
            print_info("Duplicate removal", "None found")
        
        return df_filtered
    
    def _filter_rare_activities(
        self,
        df: pd.DataFrame,
        threshold: int
    ) -> pd.DataFrame:
        """Filter out activities that occur less than threshold times."""
        activity_counts = df['concept:name'].value_counts()
        self._filtered_activities = set(
            activity_counts[activity_counts < threshold].index
        )
        
        if self._filtered_activities:
            df_filtered = df[
                ~df['concept:name'].isin(self._filtered_activities)
            ].reset_index(drop=True)
            
            print_success(f"Filtered {len(self._filtered_activities)} rare activities")
            print_info("Threshold", f"{threshold} occurrences")
            
            return df_filtered
        
        print_info("Activity filtering", "No activities exceeded threshold")
        return df