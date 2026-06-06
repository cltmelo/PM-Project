"""
Table visualization for algorithm comparison.

Creates formatted tables showing comparison results.
"""

import os
from typing import List, Optional
import pandas as pd

from ..metrics.calculator import ComparisonResult
from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success


class ComparisonTable:
    """
    Creates formatted comparison tables.
    
    Generates:
    - Text tables for console output
    - HTML tables for reports
    - CSV export for further analysis
    
    Example:
        table = ComparisonTable()
        table.create_all(result, output_dir)
    """
    
    def __init__(self):
        """Initialize the comparison table."""
        self._output_dir: str = ""
    
    def create_all(
        self,
        result: ComparisonResult,
        output_dir: str,
    ) -> List[str]:
        """
        Create all comparison tables.
        
        Args:
            result: Comparison result
            output_dir: Directory to save tables
            
        Returns:
            List of saved file paths
        """
        print_header("CREATING COMPARISON TABLES")
        
        ensure_dir(output_dir)
        self._output_dir = output_dir
        
        saved_files = []
        
        # Create text table
        path = self._create_text_table(result.dataframe)
        if path:
            saved_files.append(path)
        
        # Create HTML table
        path = self._create_html_table(result.dataframe)
        if path:
            saved_files.append(path)
        
        # Create CSV export
        path = self._create_csv_export(result.dataframe)
        if path:
            saved_files.append(path)
        
        print_success(f"Created {len(saved_files)} tables")
        
        return saved_files
    
    def _create_text_table(self, df: pd.DataFrame) -> str:
        """Create a formatted text table."""
        if df is None or df.empty:
            return ""
        
        lines = []
        lines.append("=" * 100)
        lines.append("PROCESS MINING ALGORITHM COMPARISON".center(100))
        lines.append("=" * 100)
        lines.append("")
        
        # Header
        header = f"{'Algorithm':<20} {'Fitness':>10} {'Precision':>10} {'F-Score':>10} {'Places':>8} {'Trans.':>8} {'Arcs':>8}"
        lines.append(header)
        lines.append("-" * 100)
        
        # Data rows
        for _, row in df.iterrows():
            line = (
                f"{row['name']:<20} "
                f"{row.get('fitness', 0):>10.4f} "
                f"{row.get('precision', 0):>10.4f} "
                f"{row.get('f_score', 0):>10.4f} "
                f"{row.get('num_places', 0):>8} "
                f"{row.get('num_transitions', 0):>8} "
                f"{row.get('num_arcs', 0):>8}"
            )
            lines.append(line)
        
        lines.append("-" * 100)
        lines.append("")
        
        # Save to file
        path = os.path.join(self._output_dir, "comparison_table.txt")
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
        
        return path
    
    def _create_html_table(self, df: pd.DataFrame) -> str:
        """Create an HTML table."""
        if df is None or df.empty:
            return ""
        
        html = ['<html>', '<head>', '<title>Algorithm Comparison</title>']
        html.append('<style>')
        html.append('table { border-collapse: collapse; width: 100%; }')
        html.append('th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }')
        html.append('th { background-color: #4CAF50; color: white; }')
        html.append('tr:nth-child(even) { background-color: #f2f2f2; }')
        html.append('tr:hover { background-color: #ddd; }')
        html.append('</style>')
        html.append('</head>', '<body>')
        html.append('<h1>Process Mining Algorithm Comparison</h1>')
        html.append('<table>')
        
        # Header row
        html.append('<tr>')
        for col in df.columns:
            html.append(f'<th>{col.replace("_", " ").title()}</th>')
        html.append('</tr>')
        
        # Data rows
        for _, row in df.iterrows():
            html.append('<tr>')
            for val in row:
                if isinstance(val, float):
                    html.append(f'<td>{val:.4f}</td>')
                else:
                    html.append(f'<td>{val}</td>')
            html.append('</tr>')
        
        html.append('</table>')
        html.append('</body>', '</html>')
        
        path = os.path.join(self._output_dir, "comparison_table.html")
        with open(path, 'w') as f:
            f.write('\n'.join(html))
        
        return path
    
    def _create_csv_export(self, df: pd.DataFrame) -> str:
        """Create a CSV export."""
        if df is None or df.empty:
            return ""
        
        path = os.path.join(self._output_dir, "comparison_data.csv")
        df.to_csv(path, index=False)
        
        return path