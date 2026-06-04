import pandas as pd
import io
from collections import Counter



def parse_sample_data(raw_text):
    """
    Parse whitespace-separated raw text into a Pandas DataFrame.
    
    Uses manual line-by-line parsing to handle activity names with spaces.
    Splits each line on the FIRST whitespace only:
      - Part 1: case ID (no spaces)
      - Part 2: activity name (may contain spaces)
    
    Parameters:
        raw_text: String containing the raw event log data
    
    Returns:
        df: Pandas DataFrame with columns 'case:concept:name' and 'concept:name'
    """
    lines = raw_text.strip().split('\n')
    
    case_ids = []
    activities = []
    
    for line in lines[1:]:
        line = line.strip()
        
        if not line:
            continue
        
        parts = line.split(None, 1)
        
        case_id = parts[0]
        activity_name = parts[1] if len(parts) > 1 else ''
        
        case_ids.append(case_id)
        activities.append(activity_name)
    
    df = pd.DataFrame({
        'case:concept:name': case_ids,
        'concept:name': activities
    })
    
    return df


def load_real_log(file_path):
    import pm4py
    """
    Load a real XES event log file using pm4py and convert to DataFrame.
    
    Only pm4py's read/convert functions are used here.
    NO discovery algorithms are called.
    
    Parameters:
        file_path: Path to the .xes or .xes.gz file
    
    Returns:
        df: Pandas DataFrame with standard XES column names
            ('case:concept:name' and 'concept:name')
    """
    # Read the .xes file into pm4py's internal format
    event_log = pm4py.read_xes(file_path)
    
    # Convert directly to Pandas DataFrame
    df = pm4py.convert_to_dataframe(event_log)
    
    # BPI logs use standard XES column names, so pm4py preserves them correctly
    # Common column names from pm4py:
    #   - 'case:concept:name' for case ID
    #   - 'concept:name' for activity name
    #   - 'time:timestamp' for event timestamp
    
    return df


def _filter_noise(df, noise_threshold):
    """
    Internal helper function to filter out low-frequency activities and arcs.
    
    Steps:
    1. Calculate activity frequencies
    2. Keep activities with count >= threshold * max_activity_count
    3. Filter DataFrame to only rows with valid activities
    4. Calculate arc frequencies
    5. Keep arcs with count >= threshold * max_arc_frequency
    
    Parameters:
        df: Input DataFrame
        noise_threshold: Minimum frequency ratio (e.g., 0.02 = 2%)
    
    Returns:
        df_filtered: Filtered DataFrame
        valid_activities: Set of activities that passed the filter
        valid_arcs: Set of arcs that passed the filter
        arc_freq_filtered: Dictionary of arc frequencies (filtered)
    """
    
    case_col = 'case:concept:name'
    activity_col = 'concept:name'
    
    # ============================================================
    # STEP 1: Global Activity Filter
    # ============================================================
    activity_counts = df[activity_col].value_counts()
    max_activity_count = activity_counts.max()
    min_activity_freq = noise_threshold * max_activity_count
    
    # Keep activities with frequency >= threshold
    valid_activities = set(activity_counts[activity_counts >= min_activity_freq].index)
    
    # Filter DataFrame to keep only rows with valid activities
    df_filtered = df[df[activity_col].isin(valid_activities)].copy().reset_index(drop=True)
    
    # ============================================================
    # STEP 2: Build Arcs from Filtered DataFrame
    # ============================================================
    df_work = df_filtered.copy()
    df_work['next_activity'] = df_work[activity_col].shift(-1)
    df_work['next_case'] = df_work[case_col].shift(-1)
    
    same_case_mask = df_work[case_col] == df_work['next_case']
    df_valid = df_work[same_case_mask]
    
    # Calculate arc frequencies
    arc_pairs = list(zip(df_valid[activity_col], df_valid['next_activity']))
    arc_freq = Counter(arc_pairs)
    
    # ============================================================
    # STEP 3: Arc Filter
    # ============================================================
    if len(arc_freq) > 0:
        max_arc_frequency = max(arc_freq.values())
        min_arc_freq = noise_threshold * max_arc_frequency
        
        # Keep arcs with frequency >= threshold
        valid_arcs = {arc for arc, freq in arc_freq.items() if freq >= min_arc_freq}
        arc_freq_filtered = {arc: freq for arc, freq in arc_freq.items() if freq >= min_arc_freq}
    else:
        valid_arcs = set()
        arc_freq_filtered = {}
    
    return df_filtered, valid_activities, valid_arcs, arc_freq_filtered


def build_directly_follows_graph(df, noise_threshold=0.015):
    """
    Build the directly-follows graph from the event log DataFrame.
    
    Includes noise filtering to remove infrequent activities and arcs.
    Uses ONLY vectorized Pandas operations - no row iteration.
    
    Parameters:
        df: Pandas DataFrame with columns 'case:concept:name' and 'concept:name'
            Rows must be in chronological order (as loaded from .xes file)
        noise_threshold: Minimum frequency ratio for activities/arcs (default 0.015 = 1.5%)
            Activities/arcs appearing less than this ratio of max frequency are filtered out
    
    Returns:
        arcs: set of tuples (A, B) where B directly follows A in some trace (filtered)
        start_activities: set of activities that start traces (from filtered data)
        end_activities: set of activities that end traces (from filtered data)
    """
    
    case_col = 'case:concept:name'
    activity_col = 'concept:name'
    
    # Apply noise filtering
    df_filtered, valid_activities, valid_arcs, _ = _filter_noise(df, noise_threshold)
    
    # Check if filtering removed too much
    if len(df_filtered) == 0 or len(valid_arcs) == 0:
        # Fallback: use original data without filtering
        df_filtered = df
    
    # Build start/end activities from filtered DataFrame
    start_activities = set(df_filtered.groupby(case_col)[activity_col].first())
    end_activities = set(df_filtered.groupby(case_col)[activity_col].last())
    
    # Build arcs from filtered DataFrame
    df_work = df_filtered.copy()
    df_work['next_activity'] = df_work[activity_col].shift(-1)
    df_work['next_case'] = df_work[case_col].shift(-1)
    
    same_case_mask = df_work[case_col] == df_work['next_case']
    df_valid_arcs = df_work[same_case_mask]
    
    arcs_raw = set(zip(df_valid_arcs[activity_col], df_valid_arcs['next_activity']))
    
    # Apply arc filter (only keep arcs that passed noise threshold)
    arcs = arcs_raw & valid_arcs if len(valid_arcs) > 0 else arcs_raw
    
    return arcs, start_activities, end_activities


def build_directly_follows_graph_with_frequency(df, noise_threshold=0.015):
    """
    Build DFG with arc frequencies for dynamic fallback.
    
    Includes noise filtering to remove infrequent activities and arcs.
    
    Parameters:
        df: Pandas DataFrame with columns 'case:concept:name' and 'concept:name'
        noise_threshold: Minimum frequency ratio for activities/arcs (default 0.015 = 1.5%)
    
    Returns:
        arcs: set of tuples (A, B) where B directly follows A (filtered)
        arc_freq: dict mapping arcs to their frequencies (filtered)
        start_activities: set of activities that start traces (from filtered data)
        end_activities: set of activities that end traces (from filtered data)
    """
    
    case_col = 'case:concept:name'
    activity_col = 'concept:name'
    
    # Apply noise filtering
    df_filtered, valid_activities, valid_arcs, arc_freq_filtered = _filter_noise(df, noise_threshold)
    
    # Check if filtering removed too much
    if len(df_filtered) == 0 or len(valid_arcs) == 0:
        # Fallback: use original data without filtering
        df_filtered = df
        valid_arcs = set()
        arc_freq_filtered = {}
    
    # Build start/end activities from filtered DataFrame
    start_activities = set(df_filtered.groupby(case_col)[activity_col].first())
    end_activities = set(df_filtered.groupby(case_col)[activity_col].last())
    
    # Build arcs with frequencies from filtered DataFrame
    df_work = df_filtered.copy()
    df_work['next_activity'] = df_work[activity_col].shift(-1)
    df_work['next_case'] = df_work[case_col].shift(-1)
    
    same_case_mask = df_work[case_col] == df_work['next_case']
    df_valid = df_work[same_case_mask]
    
    arc_pairs = list(zip(df_valid[activity_col], df_valid['next_activity']))
    arc_freq_raw = Counter(arc_pairs)
    
    # Use pre-filtered frequencies if available, otherwise filter now
    if len(arc_freq_filtered) > 0:
        arc_freq = arc_freq_filtered
        arcs = set(arc_freq.keys())
    else:
        # Fallback: apply threshold manually
        if len(arc_freq_raw) > 0:
            max_arc_frequency = max(arc_freq_raw.values())
            min_arc_freq = noise_threshold * max_arc_frequency
            arc_freq = {arc: freq for arc, freq in arc_freq_raw.items() if freq >= min_arc_freq}
            arcs = set(arc_freq.keys())
        else:
            arc_freq = {}
            arcs = set()
    
    return arcs, arc_freq, start_activities, end_activities