"""
Post-hoc metric enrichment for comparison results.

This module only reads algorithm outputs. It does not modify or import the
miner implementations, which keeps the comparison layer independent.
"""

from pathlib import Path
from typing import Dict, Optional

from ..config import CompareConfig
from ..parser.json_parser import AlgorithmMetrics
from ..parser.pnml_parser import PetriNetStructure
from ..utils.logging_utils import print_info, print_warning


class PostHocMetricEnricher:
    """Compute missing metrics from JSON/PNML outputs before comparison."""

    def __init__(self, config: CompareConfig, base_dir: str = "."):
        self.config = config
        self.base_dir = Path(base_dir)
        self._event_log = None

    def enrich(
        self,
        metrics: AlgorithmMetrics,
        structure: Optional[PetriNetStructure],
        pnml_path: str,
    ) -> AlgorithmMetrics:
        """Fill missing metric values where Compare has enough data."""
        if structure:
            self._fill_structure_stats(metrics, structure)
            if metrics.simplicity <= 0:
                metrics.simplicity = self._compute_simplicity(metrics.raw_data, structure)

        if metrics.precision <= 0 and pnml_path:
            precision = self._compute_precision_from_pnml(pnml_path)
            if precision is not None:
                metrics.precision = precision

        self._recompute_derived_scores(metrics)
        return metrics

    def _fill_structure_stats(
        self,
        metrics: AlgorithmMetrics,
        structure: PetriNetStructure,
    ) -> None:
        """Use parsed PNML structure when the JSON did not provide counts."""
        if metrics.num_places <= 0:
            metrics.num_places = structure.num_places
        if metrics.num_transitions <= 0:
            metrics.num_transitions = structure.num_transitions
        if metrics.num_arcs <= 0:
            metrics.num_arcs = structure.num_arcs

    def _compute_simplicity(
        self,
        raw_data: Dict,
        structure: PetriNetStructure,
    ) -> float:
        """
        Compute a simple normalized structural simplicity score.

        Prefer binding counts when present because Genetic/Alpha result JSONs
        already use that definition. Otherwise fall back to PNML arc count.
        """
        input_bindings = raw_data.get("input_bindings", {})
        output_bindings = raw_data.get("output_bindings", {})
        binding_arc_count = self._count_binding_arcs(input_bindings)
        binding_arc_count += self._count_binding_arcs(output_bindings)

        if binding_arc_count > 0:
            return 1.0 / (1.0 + binding_arc_count)

        if structure.num_arcs > 0:
            return 1.0 / (1.0 + structure.num_arcs)

        return 0.0

    def _count_binding_arcs(self, bindings: Dict) -> int:
        """Count arcs represented by nested input/output binding lists."""
        total = 0
        for binding_sets in bindings.values():
            if not isinstance(binding_sets, list):
                continue
            for binding in binding_sets:
                if isinstance(binding, list):
                    total += len(binding)
        return total

    def _compute_precision_from_pnml(self, pnml_path: str) -> Optional[float]:
        """Compute token-based precision using pm4py, PNML, and the event log."""
        try:
            import pm4py
        except ImportError:
            print_warning("Cannot compute missing precision: pm4py is not installed")
            return None

        try:
            event_log = self._load_event_log(pm4py)
            net, initial_marking, final_marking = pm4py.read_pnml(pnml_path)
            precision = pm4py.precision_token_based_replay(
                event_log,
                net,
                initial_marking,
                final_marking,
            )
            if isinstance(precision, tuple):
                precision = precision[0]
            print_info("Computed missing precision", f"{precision:.4f}")
            return float(precision)
        except Exception as e:
            print_warning(f"Could not compute precision for {pnml_path}: {e}")
            return None

    def _load_event_log(self, pm4py):
        """Load the configured event log once and reuse it."""
        if self._event_log is not None:
            return self._event_log

        log_path = self.base_dir / self.config.event_log_path
        self._event_log = pm4py.read_xes(str(log_path))
        return self._event_log

    def _recompute_derived_scores(self, metrics: AlgorithmMetrics) -> None:
        """Keep F-score and overall score consistent after enrichment."""
        if metrics.fitness > 0 and metrics.precision > 0:
            metrics.f_score = (
                2 * (metrics.fitness * metrics.precision)
                / (metrics.fitness + metrics.precision)
            )

        if not self.config.recompute_overall_score:
            return

        metrics.overall_score = (
            metrics.fitness * self.config.overall_fitness_weight
            + metrics.precision * self.config.overall_precision_weight
            + metrics.simplicity * self.config.overall_simplicity_weight
        )
