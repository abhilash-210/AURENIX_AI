"""
Evaluation Framework Data Models & Schemas.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class BenchmarkItem(BaseModel):
    """A single benchmark evaluation item."""
    id: str = Field(description="Unique identifier for the benchmark question")
    category: str = Field(description="Enterprise domain/topic category")
    question: str = Field(description="The user question to be evaluated")
    ground_truth_answer: str = Field(description="Reference ground truth answer")
    reference_contexts: list[str] = Field(
        default_factory=list,
        description="Ground-truth reference document snippets or chunks",
    )
    key_facts: list[str] = Field(
        default_factory=list,
        description="Atomic factual statements that must be present in the answer",
    )


class RetrievalMetrics(BaseModel):
    """Metrics assessing the quality of context retrieval."""
    hit_rate: float = Field(description="1.0 if any relevant context was retrieved, else 0.0")
    precision_at_k: float = Field(description="Ratio of relevant retrieved chunks to total retrieved")
    recall_at_k: float = Field(description="Ratio of relevant retrieved chunks to total reference contexts")
    mrr: float = Field(description="Mean Reciprocal Rank of the first relevant retrieved chunk")


class GenerationMetrics(BaseModel):
    """Metrics assessing the quality, faithfulness, and citation accuracy of the generated answer."""
    answer_relevance: float = Field(description="Semantic and lexical relevance of answer to query [0, 1]")
    faithfulness: float = Field(description="Ratio of answer claims supported by retrieved context [0, 1]")
    citation_correctness: float = Field(description="Ratio of valid and context-grounded citations [0, 1]")


class PerformanceMetrics(BaseModel):
    """System performance, timing, and token telemetry."""
    retrieval_latency_ms: float = Field(description="Duration of retrieval stage in milliseconds")
    generation_latency_ms: float = Field(description="Duration of LLM generation stage in milliseconds")
    total_latency_ms: float = Field(description="End-to-end response duration in milliseconds")
    prompt_tokens: int | None = Field(default=None, description="Prompt token count if available")
    completion_tokens: int | None = Field(default=None, description="Completion token count if available")
    total_tokens: int | None = Field(default=None, description="Total token consumption")


class EvaluationItemResult(BaseModel):
    """Detailed evaluation result for a single benchmark query."""
    item: BenchmarkItem
    retrieved_contexts: list[str] = Field(default_factory=list)
    generated_answer: str = Field(default="")
    citations: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_metrics: RetrievalMetrics
    generation_metrics: GenerationMetrics
    performance_metrics: PerformanceMetrics
    success: bool = True
    error_message: str | None = None


class AggregateMetricSummary(BaseModel):
    """Aggregate statistics (mean, median, p95) for a numeric metric."""
    mean: float
    median: float
    p95: float
    min: float
    max: float


class EvaluationSummaryReport(BaseModel):
    """Full aggregate evaluation report across the entire benchmark suite."""
    timestamp: str
    total_samples: int
    successful_samples: int
    failed_samples: int
    error_rate: float
    retrieval: dict[str, AggregateMetricSummary]
    generation: dict[str, AggregateMetricSummary]
    performance: dict[str, AggregateMetricSummary]
    category_breakdown: dict[str, dict[str, float]]
    item_results: list[EvaluationItemResult]
