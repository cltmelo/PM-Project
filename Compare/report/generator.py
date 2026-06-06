"""
Report generation for algorithm comparison.

Creates comprehensive HTML and Markdown reports.
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

from ..metrics.calculator import ComparisonResult
from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success


class ReportGenerator:
    """
    Generates comprehensive comparison reports.
    
    Creates:
    - HTML report with charts embedded
    - Markdown summary report
    - Executive summary text
    
    Example:
        generator = ReportGenerator()
        generator.create_all(result, output_dir)
    """
    
    def __init__(self):
        """Initialize the report generator."""
        self._output_dir: str = ""
    
    def create_all(
        self,
        result: ComparisonResult,
        output_dir: str,
    ) -> List[str]:
        """
        Create all reports.
        
        Args:
            result: Comparison result
            output_dir: Directory to save reports
            
        Returns:
            List of saved file paths
        """
        print_header("GENERATING REPORTS")
        
        ensure_dir(output_dir)
        self._output_dir = output_dir
        
        saved_files = []
        
        # Create HTML report
        path = self._create_html_report(result)
        if path:
            saved_files.append(path)
        
        # Create Markdown report
        path = self._create_markdown_report(result)
        if path:
            saved_files.append(path)
        
        # Create executive summary
        path = self._create_executive_summary(result)
        if path:
            saved_files.append(path)
        
        print_success(f"Created {len(saved_files)} reports")
        
        return saved_files
    
    def _create_html_report(self, result: ComparisonResult) -> str:
        """Create a comprehensive HTML report."""
        if result.dataframe is None or result.dataframe.empty:
            return ""
        
        df = result.dataframe
        
        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html lang="en">')
        html.append('<head>')
        html.append('<meta charset="UTF-8">')
        html.append('<title>Process Mining Algorithm Comparison Report</title>')
        html.append('<style>')
        html.append(self._get_html_styles())
        html.append('</style>')
        html.append('</head>')
        html.append('<body>')
        
        # Header
        html.append('<div class="header">')
        html.append('<h1>Process Mining Algorithm Comparison Report</h1>')
        html.append(f'<p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
        html.append('</div>')
        
        # Executive Summary
        html.append('<div class="section">')
        html.append('<h2>Executive Summary</h2>')
        html.append(self._get_executive_summary_html(df))
        html.append('</div>')
        
        # Quality Metrics Table
        html.append('<div class="section">')
        html.append('<h2>Quality Metrics</h2>')
        html.append(self._dataframe_to_html_table(df[['name', 'fitness', 'precision', 'f_score']]))
        html.append('</div>')
        
        # Structure Metrics Table
        html.append('<div class="section">')
        html.append('<h2>Model Structure</h2>')
        html.append(self._dataframe_to_html_table(df[['name', 'num_places', 'num_transitions', 'num_arcs', 'complexity']]))
        html.append('</div>')
        
        # Best Algorithms
        html.append('<div class="section">')
        html.append('<h2>Best Performers</h2>')
        html.append(self._get_best_performers_html(df))
        html.append('</div>')
        
        # Charts
        html.append('<div class="section">')
        html.append('<h2>Visualizations</h2>')
        html.append('<div class="charts">')
        html.append('<img src="quality_comparison.png" alt="Quality Comparison">')
        html.append('<img src="structure_comparison.png" alt="Structure Comparison">')
        html.append('<img src="summary_comparison.png" alt="Summary Comparison">')
        html.append('</div>')
        html.append('</div>')
        
        html.append('</body>')
        html.append('</html>')
        
        path = os.path.join(self._output_dir, "comparison_report.html")
        with open(path, 'w') as f:
            f.write('\n'.join(html))
        
        return path
    
    def _create_markdown_report(self, result: ComparisonResult) -> str:
        """Create a Markdown report."""
        if result.dataframe is None or result.dataframe.empty:
            return ""
        
        df = result.dataframe
        
        md = []
        md.append('# Process Mining Algorithm Comparison Report')
        md.append('')
        md.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        md.append('')
        
        # Executive Summary
        md.append('## Executive Summary')
        md.append('')
        md.append(self._get_executive_summary_markdown(df))
        md.append('')
        
        # Quality Metrics
        md.append('## Quality Metrics')
        md.append('')
        md.append(self._dataframe_to_markdown(df[['name', 'fitness', 'precision', 'f_score']]))
        md.append('')
        
        # Structure Metrics
        md.append('## Model Structure')
        md.append('')
        md.append(self._dataframe_to_markdown(df[['name', 'num_places', 'num_transitions', 'num_arcs']]))
        md.append('')
        
        # Rankings
        md.append('## Rankings')
        md.append('')
        md.append(self._get_rankings_markdown(df))
        
        path = os.path.join(self._output_dir, "comparison_report.md")
        with open(path, 'w') as f:
            f.write('\n'.join(md))
        
        return path
    
    def _create_executive_summary(self, result: ComparisonResult) -> str:
        """Create a text executive summary."""
        if result.dataframe is None or result.dataframe.empty:
            return ""
        
        df = result.dataframe
        
        lines = []
        lines.append("=" * 70)
        lines.append("EXECUTIVE SUMMARY - ALGORITHM COMPARISON".center(70))
        lines.append("=" * 70)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"Algorithms compared: {len(df)}")
        lines.append("")
        
        # Best performers
        lines.append("BEST PERFORMERS")
        lines.append("-" * 40)
        
        if 'fitness' in df.columns and df['fitness'].max() > 0:
            best_fit = df.loc[df['fitness'].idxmax()]
            lines.append(f"Best Fitness: {best_fit['name']} ({best_fit['fitness']:.4f})")
        
        if 'precision' in df.columns and df['precision'].max() > 0:
            best_prec = df.loc[df['precision'].idxmax()]
            lines.append(f"Best Precision: {best_prec['name']} ({best_prec['precision']:.4f})")
        
        if 'f_score' in df.columns and df['f_score'].max() > 0:
            best_f = df.loc[df['f_score'].idxmax()]
            lines.append(f"Best F-Score: {best_f['name']} ({best_f['f_score']:.4f})")
        
        if 'num_places' in df.columns:
            simplest = df.loc[df['num_places'].idxmin()]
            lines.append(f"Simplest Model: {simplest['name']} ({simplest['num_places']} places)")
        
        lines.append("")
        lines.append("=" * 70)
        
        path = os.path.join(self._output_dir, "executive_summary.txt")
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
        
        return path
    
    def _get_html_styles(self) -> str:
        """Get HTML CSS styles."""
        return """
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }
            .header h1 { margin: 0 0 10px 0; }
            .section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .section h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            table { border-collapse: collapse; width: 100%; margin: 10px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #3498db; color: white; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
            .best { background-color: #d4edda !important; font-weight: bold; }
            .charts img { max-width: 100%; margin: 10px 0; }
            .highlight { background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }
        """
    
    def _get_executive_summary_html(self, df: pd.DataFrame) -> str:
        """Get executive summary as HTML."""
        html = ['<div class="highlight">']
        
        if 'fitness' in df.columns:
            best = df.loc[df['fitness'].idxmax()]
            html.append(f'<p><strong>Best Fitness:</strong> {best["name"]} ({best["fitness"]:.4f})</p>')
        
        if 'precision' in df.columns:
            best = df.loc[df['precision'].idxmax()]
            html.append(f'<p><strong>Best Precision:</strong> {best["name"]} ({best["precision"]:.4f})</p>')
        
        html.append('</div>')
        return '\n'.join(html)
    
    def _get_executive_summary_markdown(self, df: pd.DataFrame) -> str:
        """Get executive summary as Markdown."""
        md = []
        
        if 'fitness' in df.columns:
            best = df.loc[df['fitness'].idxmax()]
            md.append(f'**Best Fitness:** {best["name"]} ({best["fitness"]:.4f})')
        
        if 'precision' in df.columns:
            best = df.loc[df['precision'].idxmax()]
            md.append(f'**Best Precision:** {best["name"]} ({best["precision"]:.4f})')
        
        return '\n'.join(md)
    
    def _get_best_performers_html(self, df: pd.DataFrame) -> str:
        """Get best performers as HTML."""
        html = ['<ul>']
        
        if 'fitness' in df.columns:
            best = df.loc[df['fitness'].idxmax()]
            html.append(f'<li><strong>Best Fitness:</strong> {best["name"]} with {best["fitness"]:.4f}</li>')
        
        if 'precision' in df.columns:
            best = df.loc[df['precision'].idxmax()]
            html.append(f'<li><strong>Best Precision:</strong> {best["name"]} with {best["precision"]:.4f}</li>')
        
        if 'num_places' in df.columns:
            best = df.loc[df['num_places'].idxmin()]
            html.append(f'<li><strong>Simplest Model:</strong> {best["name"]} with {best["num_places"]} places</li>')
        
        html.append('</ul>')
        return '\n'.join(html)
    
    def _get_rankings_markdown(self, df: pd.DataFrame) -> str:
        """Get rankings as Markdown."""
        md = []
        
        md.append('### By Fitness')
        md.append('| Rank | Algorithm | Fitness |')
        md.append('|------|-----------|---------|')
        if 'fitness' in df.columns:
            for i, (_, row) in enumerate(df.sort_values('fitness', ascending=False).iterrows()):
                md.append(f'| {i+1} | {row["name"]} | {row["fitness"]:.4f} |')
        
        md.append('')
        md.append('### By Precision')
        md.append('| Rank | Algorithm | Precision |')
        md.append('|------|-----------|-----------|')
        if 'precision' in df.columns:
            for i, (_, row) in enumerate(df.sort_values('precision', ascending=False).iterrows()):
                md.append(f'| {i+1} | {row["name"]} | {row["precision"]:.4f} |')
        
        return '\n'.join(md)
    
    def _dataframe_to_html_table(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to HTML table."""
        html = ['<table>', '<tr>']
        
        for col in df.columns:
            html.append(f'<th>{col.replace("_", " ").title()}</th>')
        html.append('</tr>')
        
        for _, row in df.iterrows():
            html.append('<tr>')
            for i, val in enumerate(row):
                if isinstance(val, float):
                    html.append(f'<td>{val:.4f}</td>')
                else:
                    html.append(f'<td>{val}</td>')
            html.append('</tr>')
        
        html.append('</table>')
        return '\n'.join(html)
    
    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to Markdown table."""
        md = []
        
        # Header
        headers = '| ' + ' | '.join(df.columns.str.replace('_', ' ').str.title()) + ' |'
        md.append(headers)
        md.append('|' + '|'.join(['---'] * len(df.columns)) + '|')
        
        # Data rows
        for _, row in df.iterrows():
            values = []
            for val in row:
                if isinstance(val, float):
                    values.append(f'{val:.4f}')
                else:
                    values.append(str(val))
            md.append('| ' + ' | '.join(values) + ' |')
        
        return '\n'.join(md)