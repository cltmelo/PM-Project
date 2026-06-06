"""
Chart visualization for algorithm comparison.

Creates bar charts, radar charts, and other visualizations.
"""

from importlib.resources import path
import os
import tempfile
from typing import List, Optional, Tuple
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "pm_project_matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", os.path.join(tempfile.gettempdir(), "pm_project_cache"))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from ..metrics.calculator import ComparisonResult
from ..utils.file_utils import ensure_dir
from ..utils.logging_utils import print_header, print_success, print_warning


# Set style
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except:
    plt.style.use('ggplot')


class ComparisonCharts:
    """
    Creates comparison visualizations.
    
    Generates:
    - Bar charts for fitness/precision/f-score
    - Radar charts for multi-dimensional comparison
    - Structure comparison charts
    - Combined summary charts
    
    Example:
        charts = ComparisonCharts()
        charts.create_all(result, output_dir)
    """
    
    COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']#, '#ff5733']  # ADDED '#ff5733' for generalization    

    def __init__(self):
        """Initialize the comparison charts."""
        self._output_dir: str = ""
    
    def create_all(
        self,
        result: ComparisonResult,
        output_dir: str,
        dpi: int = 150,
    ) -> List[str]:
        """
        Create all comparison charts.
        
        Args:
            result: Comparison result
            output_dir: Directory to save charts
            dpi: Resolution of output images
            
        Returns:
            List of saved file paths
        """
        print_header("CREATING COMPARISON CHARTS")
        
        ensure_dir(output_dir)
        self._output_dir = output_dir
        
        saved_files = []
        
        # Create individual charts
        try:
            path = self._create_quality_bar_chart(result.dataframe, dpi)
            saved_files.append(path)
        except Exception as e:
            print_warning(f"Quality chart failed: {e}")
        
        try:
            path = self._create_structure_bar_chart(result.dataframe, dpi)
            saved_files.append(path)
        except Exception as e:
            print_warning(f"Structure chart failed: {e}")
        
        try:
            path = self._create_radar_chart(result.dataframe, dpi)
            saved_files.append(path)
        except Exception as e:
            print_warning(f"Radar chart failed: {e}")
        
        try:
            path = self._create_summary_chart(result.dataframe, dpi)
            saved_files.append(path)
        except Exception as e:
            print_warning(f"Summary chart failed: {e}")
        
        print_success(f"Created {len(saved_files)} charts")
        
        return saved_files
    
    def _create_quality_bar_chart(self, df: pd.DataFrame, dpi: int) -> str:
        """Create a bar chart with clear separation between algorithms."""
        if df is None or df.empty:
            return ""
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Metrics to compare
        metrics = ['fitness', 'precision', 'simplicity', 'overall_score']
        available = [m for m in metrics if m in df.columns and df[m].sum() > 0]
        
        if not available:
            return ""
        
        n = len(df)
        bar_width = 0.15
        group_width = bar_width * len(available)
        
        # Colors
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#ff9800', '#9b59b6']
        color_map = dict(zip(metrics, colors))
        
        # Grouped bars
        for i, metric in enumerate(available):
            positions = []
            for j in range(n):
                pos = j * (group_width + 0.1) + i * bar_width
                positions.append(pos)
                ax.bar(pos, df.iloc[j][metric], bar_width, 
                    color=color_map[metric], edgecolor='white', linewidth=0.5)
            
            # X-axis labels (only for first metric)
            if i == 0:
                for j in range(n):
                    pos = j * (group_width + 0.1) + i * bar_width + group_width / 2 - bar_width / 2
                    ax.text(pos, -0.08, df.iloc[j]['name'], 
                        ha='center', va='top', fontsize=9, rotation=45)
        
        # Add vertical lines between groups
        for j in range(1, n):
            line_pos = j * (group_width + 0.1) - 0.05
            ax.axvline(x=line_pos, color='#cccccc', linestyle='--', linewidth=1, alpha=0.5)
        
        ax.set_xlabel('')
        ax.set_ylabel('Score (0-1)', fontsize=11)
        ax.set_title('Process Mining Algorithm Comparison', fontsize=14, fontweight='bold')
        
        # Legend
        handles = [plt.Rectangle((0, 0), 1, 1, color=color_map[m]) for m in available]
        ax.legend(handles, [m.replace('_', ' ').title() for m in available],
                loc='upper right', fontsize=9, ncol=len(available))
        
        ax.set_ylim(-0.1, 1.15)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        path = os.path.join(self._output_dir, "quality_comparison.png")
        plt.savefig(path, dpi=dpi, bbox_inches='tight')
        plt.close()
        return path
    
    def _create_structure_bar_chart(
        self,
        df: pd.DataFrame,
        dpi: int,
    ) -> str:
        """Create a bar chart comparing model structure."""
        if df is None or df.empty:
            return ""
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Places/Transitions/Arcs
        ax = axes[0]
        structure_metrics = ['num_places', 'num_transitions', 'num_arcs']
        available = [m for m in structure_metrics if m in df.columns]
        
        if available:
            x = np.arange(len(df))
            width = 0.25
            
            for i, metric in enumerate(available):
                ax.bar(x + i * width, df[metric], width,
                      label=metric.replace('num_', '').title(),
                      color=self.COLORS[i])
            
            ax.set_xlabel('Algorithm')
            ax.set_ylabel('Count')
            ax.set_title('Model Structure')
            ax.set_xticks(x + width)
            ax.set_xticklabels(df['name'], rotation=45, ha='right')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
        
        # Complexity
        ax = axes[1]
        if 'complexity' in df.columns:
            bars = ax.bar(df['name'], df['complexity'], color=self.COLORS[3])
            ax.set_xlabel('Algorithm')
            ax.set_ylabel('Arc-to-Element Ratio')
            ax.set_title('Model Complexity')
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        path = os.path.join(self._output_dir, "structure_comparison.png")
        plt.savefig(path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        return path
    
    def _create_radar_chart(
        self,
        df: pd.DataFrame,
        dpi: int,
    ) -> str:
        """Create a radar chart for multi-dimensional comparison."""
        if df is None or df.empty:
            return ""
        
        # Select metrics for radar
        metrics = []
        if 'fitness' in df.columns and df['fitness'].max() > 0:
            metrics.append('fitness')
        if 'precision' in df.columns and df['precision'].max() > 0:
            metrics.append('precision')
        if 'f_score' in df.columns and df['f_score'].max() > 0:
            metrics.append('f_score')
        if 'num_places' in df.columns:
            metrics.append('num_places')
        
        if len(metrics) < 3:
            return ""
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        # Normalize metrics to 0-1 scale for comparison
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False)
        
        for i, row in df.iterrows():
            values = []
            for metric in metrics:
                if metric == 'num_places':
                    # Invert and normalize (fewer places = better)
                    max_val = df['num_places'].max()
                    val = 1 - (row[metric] / max_val) if max_val > 0 else 0
                else:
                    val = row[metric]
                values.append(val)
            
            values += values[:1]  # Close the polygon
            angles_plot = np.concatenate((angles, [angles[0]]))
            
            ax.plot(angles_plot, values, 'o-', linewidth=2,
                   label=row['name'], color=self.COLORS[i % len(self.COLORS)])
            ax.fill(angles_plot, values, alpha=0.15,
                   color=self.COLORS[i % len(self.COLORS)])
        
        ax.set_xticks(angles)
        ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics])
        ax.set_ylim(0, 1.2)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.set_title('Multi-Dimensional Comparison', pad=20)
        
        plt.tight_layout()
        
        path = os.path.join(self._output_dir, "radar_comparison.png")
        plt.savefig(path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        return path
    
    def _create_summary_chart(
        self,
        df: pd.DataFrame,
        dpi: int,
    ) -> str:
        """Create a comprehensive summary chart."""
        if df is None or df.empty:
            return ""
        
        fig = plt.figure(figsize=(16, 10))
        
        # Create grid
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # 1. Fitness comparison
        ax1 = fig.add_subplot(gs[0, 0])
        if 'fitness' in df.columns:
            colors = [self.COLORS[i] for i in range(len(df))]
            bars = ax1.bar(df['name'], df['fitness'], color=colors)
            ax1.set_title('Fitness')
            ax1.set_ylim(0, 1.1)
            plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
        
        # 2. Precision comparison
        ax2 = fig.add_subplot(gs[0, 1])
        if 'precision' in df.columns:
            colors = [self.COLORS[i] for i in range(len(df))]
            bars = ax2.bar(df['name'], df['precision'], color=colors)
            ax2.set_title('Precision')
            ax2.set_ylim(0, 1.1)
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        
        # 3. F-Score comparison
        ax3 = fig.add_subplot(gs[0, 2])
        if 'f_score' in df.columns:
            colors = [self.COLORS[i] for i in range(len(df))]
            bars = ax3.bar(df['name'], df['f_score'], color=colors)
            ax3.set_title('F-Score')
            ax3.set_ylim(0, 1.1)
            plt.setp(ax3.get_xticklabels(), rotation=45, ha='right')
        
        # 4. Model size (places)
        ax4 = fig.add_subplot(gs[1, 0])
        if 'num_places' in df.columns:
            colors = [self.COLORS[i] for i in range(len(df))]
            bars = ax4.bar(df['name'], df['num_places'], color=colors)
            ax4.set_title('Number of Places')
            plt.setp(ax4.get_xticklabels(), rotation=45, ha='right')
        
        # 5. Model size (arcs)
        ax5 = fig.add_subplot(gs[1, 1])
        if 'num_arcs' in df.columns:
            colors = [self.COLORS[i] for i in range(len(df))]
            bars = ax5.bar(df['name'], df['num_arcs'], color=colors)
            ax5.set_title('Number of Arcs')
            plt.setp(ax5.get_xticklabels(), rotation=45, ha='right')
        
        # 6. Summary table
        ax6 = fig.add_subplot(gs[1, 2])
        ax6.axis('off')
        
        # Create summary text
        summary_text = []
        for _, row in df.iterrows():
            summary_text.append(f"{row['name']}")
            summary_text.append(f"  Fitness: {row.get('fitness', 0):.4f}")
            summary_text.append(f"  Precision: {row.get('precision', 0):.4f}")
            summary_text.append(f"  Places: {row.get('num_places', 0)}")
            summary_text.append("")
        
        ax6.text(0.1, 0.9, '\n'.join(summary_text),
                transform=ax6.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace')
        ax6.set_title('Summary')
        
        plt.suptitle('Process Mining Algorithm Comparison', fontsize=14, fontweight='bold')
        
        path = os.path.join(self._output_dir, "summary_comparison.png")
        plt.savefig(path, dpi=dpi, bbox_inches='tight')
        plt.close()
        
        return path
