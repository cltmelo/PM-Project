"""
Event Log Analysis Script
Load and explore the BPI Challenge 2017 event data
"""

# USE THE CONDA ENVIRONMENT WITH PM4PY INSTALLED TO RUN THIS SCRIPT
# conda activate process-mining

import pm4py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import json

# Set up plotting style
plt.style.use('default')
sns.set_palette("husl")

# Path to event data
DATA_DIR = Path(__file__).parent.parent / "BPI Challenge 2017_1_all"
# use the compressed XES if present
XES_FILE = DATA_DIR / "BPI Challenge 2017.xes.gz"

# Output directory inside ERNESTO folder
OUTPUT_DIR = Path(__file__).parent / "output"

class Tee:
    """Simple tee to write stdout/stderr to both console and a file."""
    def __init__(self, *files):
        self.files = files

    def write(self, data):
        for f in self.files:
            f.write(data)

    def flush(self):
        for f in self.files:
            try:
                f.flush()
            except Exception:
                pass


def load_event_log():
    """Load the XES event log"""
    print(f"Loading event log from: {XES_FILE}")
    # pm4py.read_xes() returns a DataFrame in newer versions
    df = pm4py.read_xes(str(XES_FILE))
    print(f"Loaded DataFrame with shape: {df.shape}")
    return df


def explore_log(df):
    """Print basic statistics about the event log DataFrame"""
    print("\n=== Event Log Statistics ===")
    print(f"DataFrame shape: {df.shape}")
    print(f"Number of events: {len(df)}")
    print(f"Number of unique cases: {df['case:concept:name'].nunique()}")

    print(f"\nColumns: {list(df.columns)}")

    # Show data types
    print(f"\nData types:")
    print(df.dtypes)

    # Show first few rows
    print(f"\nFirst few events:")
    print(df.head())

    # Show case distribution
    case_counts = df['case:concept:name'].value_counts()
    print(f"\nCase length distribution (first 10):")
    print(case_counts.head(10))


def convert_to_dataframe(df):
    """The data is already a DataFrame, just return it"""
    print("\n=== DataFrame Already Loaded ===")
    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {list(df.columns)}")
    return df


def analyze_loan_goals(df):
    """Analyze loan goal distribution"""
    print("\n=== Loan Goal Analysis ===")
    goals = df['case:LoanGoal'].value_counts()
    print(goals)

def analyze_processing_times(df):
    """Analyze case processing times"""
    print("\n=== Processing Time Analysis ===")
    # Group by case and calculate duration
    case_durations = df.groupby('case:concept:name')['time:timestamp'].agg(['min', 'max'])
    case_durations['duration_days'] = (case_durations['max'] - case_durations['min']).dt.days
    print(f"Average processing time: {case_durations['duration_days'].mean():.1f} days")

def analyze_acceptance_rates(df):
    """Analyze loan acceptance rates"""
    print("\n=== Acceptance Rate Analysis ===")
    accepted = df.groupby('case:concept:name')['Accepted'].last()
    acceptance_rate = accepted.value_counts(normalize=True)
    print(f"Acceptance rate: {acceptance_rate.get(True, 0):.1%}")


def visualize_loan_goals(df):
    """Visualize loan goal distribution"""
    plt.figure(figsize=(12, 6))
    goals = df['case:LoanGoal'].value_counts()
    goals.plot(kind='bar', color='skyblue')
    plt.title('Distribution of Loan Goals', fontsize=14, fontweight='bold')
    plt.xlabel('Loan Goal')
    plt.ylabel('Number of Applications')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(str(OUTPUT_DIR / 'loan_goals_distribution.png'), dpi=300, bbox_inches='tight')
    plt.show()


def visualize_processing_times(df):
    """Visualize processing time distribution"""
    case_durations = df.groupby('case:concept:name')['time:timestamp'].agg(['min', 'max'])
    case_durations['duration_days'] = (case_durations['max'] - case_durations['min']).dt.days

    plt.figure(figsize=(10, 6))
    plt.hist(case_durations['duration_days'], bins=50, alpha=0.7, color='lightcoral', edgecolor='black')
    plt.title('Distribution of Processing Times', fontsize=14, fontweight='bold')
    plt.xlabel('Processing Time (Days)')
    plt.ylabel('Number of Cases')
    plt.axvline(case_durations['duration_days'].mean(), color='red', linestyle='--',
                label=f'Mean: {case_durations["duration_days"].mean():.1f} days')
    plt.legend()
    plt.tight_layout()
    plt.savefig(str(OUTPUT_DIR / 'processing_times_distribution.png'), dpi=300, bbox_inches='tight')
    plt.show()


def visualize_acceptance_by_goal(df):
    """Visualize acceptance rates by loan goal"""
    # Get acceptance status for each case
    case_acceptance = df.groupby('case:concept:name').agg({
        'Accepted': 'last',
        'case:LoanGoal': 'first'
    })

    # Calculate acceptance rates by loan goal
    acceptance_by_goal = case_acceptance.groupby('case:LoanGoal')['Accepted'].value_counts(normalize=True).unstack()

    plt.figure(figsize=(12, 6))
    acceptance_by_goal[True].plot(kind='bar', color='lightgreen', alpha=0.7)
    plt.title('Acceptance Rates by Loan Goal', fontsize=14, fontweight='bold')
    plt.xlabel('Loan Goal')
    plt.ylabel('Acceptance Rate')
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(str(OUTPUT_DIR / 'acceptance_by_goal.png'), dpi=300, bbox_inches='tight')
    plt.show()


def visualize_requested_amounts(df):
    """Visualize requested amount distribution"""
    plt.figure(figsize=(10, 6))
    # Filter out NaN values and amounts over reasonable range for better visualization
    amounts = df['case:RequestedAmount'].dropna()
    amounts = amounts[amounts < amounts.quantile(0.95)]  # Remove top 5% outliers

    plt.hist(amounts, bins=50, alpha=0.7, color='lightblue', edgecolor='black')
    plt.title('Distribution of Requested Loan Amounts', fontsize=14, fontweight='bold')
    plt.xlabel('Requested Amount (€)')
    plt.ylabel('Number of Applications')
    plt.axvline(amounts.mean(), color='red', linestyle='--',
                label=f'Mean: €{amounts.mean():,.0f}')
    plt.legend()
    plt.tight_layout()
    plt.savefig(str(OUTPUT_DIR / 'requested_amounts_distribution.png'), dpi=300, bbox_inches='tight')
    plt.show()


def visualize_applications_over_time(df):
    """Visualize number of applications over time"""
    # Group by month
    df['month'] = df['time:timestamp'].dt.to_period('M')
    monthly_apps = df.groupby('month')['case:concept:name'].nunique()

    plt.figure(figsize=(12, 6))
    monthly_apps.plot(kind='line', marker='o', color='purple')
    plt.title('Number of Loan Applications Over Time', fontsize=14, fontweight='bold')
    plt.xlabel('Month')
    plt.ylabel('Number of Applications')
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(OUTPUT_DIR / 'applications_over_time.png'), dpi=300, bbox_inches='tight')
    plt.show()


def visualize_credit_score_vs_acceptance(df):
    """Visualize credit score distribution by acceptance status"""
    # Get credit score and acceptance for each case
    case_data = df.groupby('case:concept:name').agg({
        'CreditScore': 'first',
        'Accepted': 'last'
    }).dropna()

    plt.figure(figsize=(10, 6))
    sns.boxplot(data=case_data, x='Accepted', y='CreditScore',
                palette=['lightcoral', 'lightgreen'])
    plt.title('Credit Score Distribution by Acceptance Status', fontsize=14, fontweight='bold')
    plt.xlabel('Accepted')
    plt.ylabel('Credit Score')
    plt.xticks([0, 1], ['Rejected', 'Accepted'])
    plt.tight_layout()
    plt.savefig(str(OUTPUT_DIR / 'credit_score_vs_acceptance.png'), dpi=300, bbox_inches='tight')
    plt.show()


def create_comprehensive_dashboard(df):
    """Create a comprehensive dashboard with multiple visualizations"""
    print("\n=== Generating Comprehensive Dashboard ===")

    # Create a figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('BPI Challenge 2017 - Loan Application Process Dashboard',
                 fontsize=16, fontweight='bold')

    # 1. Loan Goals Distribution
    goals = df['case:LoanGoal'].value_counts()
    goals.plot(kind='bar', ax=axes[0,0], color='skyblue')
    axes[0,0].set_title('Loan Goals Distribution')
    axes[0,0].tick_params(axis='x', rotation=45)

    # 2. Processing Times
    case_durations = df.groupby('case:concept:name')['time:timestamp'].agg(['min', 'max'])
    case_durations['duration_days'] = (case_durations['max'] - case_durations['min']).dt.days
    axes[0,1].hist(case_durations['duration_days'], bins=30, alpha=0.7, color='lightcoral', edgecolor='black')
    axes[0,1].set_title('Processing Time Distribution')
    axes[0,1].set_xlabel('Days')
    axes[0,1].axvline(case_durations['duration_days'].mean(), color='red', linestyle='--', alpha=0.7)

    # 3. Acceptance by Goal
    case_acceptance = df.groupby('case:concept:name').agg({
        'Accepted': 'last',
        'case:LoanGoal': 'first'
    })
    acceptance_by_goal = case_acceptance.groupby('case:LoanGoal')['Accepted'].mean()
    acceptance_by_goal.plot(kind='bar', ax=axes[0,2], color='lightgreen', alpha=0.7)
    axes[0,2].set_title('Acceptance Rate by Loan Goal')
    axes[0,2].tick_params(axis='x', rotation=45)
    axes[0,2].set_ylim(0, 1)

    # 4. Requested Amounts
    amounts = df['case:RequestedAmount'].dropna()
    amounts = amounts[amounts < amounts.quantile(0.95)]
    axes[1,0].hist(amounts, bins=30, alpha=0.7, color='lightblue', edgecolor='black')
    axes[1,0].set_title('Requested Amount Distribution')
    axes[1,0].set_xlabel('Amount (€)')

    # 5. Applications Over Time
    df['month'] = df['time:timestamp'].dt.to_period('M')
    monthly_apps = df.groupby('month')['case:concept:name'].nunique()
    monthly_apps.plot(kind='line', ax=axes[1,1], marker='o', color='purple')
    axes[1,1].set_title('Applications Over Time')
    axes[1,1].tick_params(axis='x', rotation=45)

    # 6. Credit Score vs Acceptance
    case_data = df.groupby('case:concept:name').agg({
        'CreditScore': 'first',
        'Accepted': 'last'
    }).dropna()
    sns.boxplot(data=case_data, x='Accepted', y='CreditScore', ax=axes[1,2],
                palette=['lightcoral', 'lightgreen'])
    axes[1,2].set_title('Credit Score by Acceptance')
    axes[1,2].set_xticklabels(['Rejected', 'Accepted'])

    plt.tight_layout()
    plt.savefig(str(OUTPUT_DIR / 'comprehensive_dashboard.png'), dpi=300, bbox_inches='tight')
    plt.show()


def analyze_resource_workload(df):
    """Analyze which users handle most applications"""
    workload = df['org:resource'].value_counts()
    print(f"\nTop 5 busiest resources:\n{workload.head()}")


def analyze_bottlenecks(df):
    """Find process bottlenecks"""
    # Group by activity and calculate average times
    activity_times = df.groupby('concept:name')['time:timestamp'].agg(['count', 'min', 'max'])
    print(f"\nMost frequent activities:\n{activity_times['count'].sort_values(ascending=False).head()}")


def main():
    try:
        # Ensure output directory exists and start logging
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        log_path = OUTPUT_DIR / 'run_output.txt'
        log_f = open(log_path, 'w', encoding='utf-8')
        sys.stdout = Tee(sys.__stdout__, log_f)
        sys.stderr = Tee(sys.__stderr__, log_f)

        # Load the event log (returns DataFrame)
        df = load_event_log()

        # Basic exploration
        explore_log(df)

        # Run all analyses
        analyze_loan_goals(df)
        analyze_processing_times(df)
        analyze_acceptance_rates(df)
        analyze_resource_workload(df)
        analyze_bottlenecks(df)

        # Generate visualizations
        print("\n=== Generating Visualizations ===")
        print("Creating individual plots...")

        visualize_loan_goals(df)
        visualize_processing_times(df)
        visualize_acceptance_by_goal(df)
        visualize_requested_amounts(df)
        visualize_applications_over_time(df)
        visualize_credit_score_vs_acceptance(df)

        print("Creating comprehensive dashboard...")
        create_comprehensive_dashboard(df)

        print("\n✓ Analysis complete!")
        print(f"✓ All visualizations saved to {OUTPUT_DIR}/ directory")
        print("\nYou can now work with the 'df' DataFrame for further analysis")

        # Write a JSON summary of key results
        try:
            case_durations = df.groupby('case:concept:name')['time:timestamp'].agg(['min', 'max'])
            case_durations['duration_days'] = (case_durations['max'] - case_durations['min']).dt.days
            avg_processing = float(case_durations['duration_days'].mean())
        except Exception:
            avg_processing = None

        try:
            accepted = df.groupby('case:concept:name')['Accepted'].last()
            acceptance_rate = float(accepted.value_counts(normalize=True).get(True, 0))
        except Exception:
            acceptance_rate = None

        summary = {
            'shape': list(df.shape),
            'num_events': int(len(df)),
            'num_cases': int(df['case:concept:name'].nunique()) if 'case:concept:name' in df.columns else None,
            'avg_processing_days': avg_processing,
            'acceptance_rate': acceptance_rate
        }

        with open(OUTPUT_DIR / 'run_output.json', 'w', encoding='utf-8') as jf:
            json.dump(summary, jf, indent=2)

        # restore stdout/stderr and close log file so the file is flushed properly
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        log_f.close()

    except FileNotFoundError:
        print(f"Error: Could not find event log at {XES_FILE}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


