"""
Metric modules for retrieval, generation, and performance evaluation.
"""

from evaluation.metrics.citation import calculate_citation_correctness
from evaluation.metrics.faithfulness import calculate_faithfulness
from evaluation.metrics.performance import compute_metric_summary
from evaluation.metrics.relevance import calculate_answer_relevance
from evaluation.metrics.retrieval import (
    calculate_hit_rate,
    calculate_mrr,
    calculate_precision_at_k,
    calculate_recall_at_k,
)

__all__ = [
    "calculate_answer_relevance",
    "calculate_citation_correctness",
    "calculate_faithfulness",
    "calculate_hit_rate",
    "calculate_mrr",
    "calculate_precision_at_k",
    "calculate_recall_at_k",
    "compute_metric_summary",
]
