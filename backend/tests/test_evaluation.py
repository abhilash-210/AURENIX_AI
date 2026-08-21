"""
Unit & Integration tests for the Generative AI Evaluation Framework.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure root workspace is on sys.path for evaluation package imports
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from evaluation.metrics.citation import calculate_citation_correctness, extract_citation_indices
from evaluation.metrics.faithfulness import calculate_faithfulness, is_claim_supported
from evaluation.metrics.performance import compute_metric_summary
from evaluation.metrics.relevance import calculate_answer_relevance
from evaluation.metrics.retrieval import (
    calculate_hit_rate,
    calculate_mrr,
    calculate_precision_at_k,
    calculate_recall_at_k,
)
from evaluation.models import BenchmarkItem
from evaluation.pipeline import EvaluationPipeline
from evaluation.reporter import ReportGenerator


# ──────────────────────────────────────────────────────────────────────────────
# Retrieval Metrics Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_retrieval_hit_rate():
    ref_contexts = [
        "SOC 2 policy mandates 90-day password rotation and 14-character minimum length.",
    ]
    matching_chunks = [
        "SOC 2 policy requires rotating passwords every 90 days with 14 characters minimum.",
    ]
    unrelated_chunks = [
        "The cafeteria lunch menu is updated weekly on Mondays.",
    ]

    assert calculate_hit_rate(matching_chunks, ref_contexts) == 1.0
    assert calculate_hit_rate(unrelated_chunks, ref_contexts) == 0.0
    assert calculate_hit_rate([], ref_contexts) == 0.0


def test_retrieval_precision_and_recall():
    ref_contexts = [
        "Primary caregivers receive 16 weeks of paid parental leave.",
        "Secondary caregivers receive 8 weeks of paid parental leave.",
    ]
    retrieved = [
        "Primary caregivers receive 16 weeks of paid parental leave.",  # relevant
        "The weather in Seattle is rainy in the winter.",               # irrelevant
        "Secondary caregivers receive 8 weeks of paid parental leave.",# relevant
        "Office parking is available on levels B1 and B2.",            # irrelevant
    ]

    precision = calculate_precision_at_k(retrieved, ref_contexts, k=4)
    recall = calculate_recall_at_k(retrieved, ref_contexts, k=4)

    assert precision == 0.50  # 2 out of 4 chunks are relevant
    assert recall == 1.0     # both reference contexts were captured


def test_retrieval_mrr():
    ref_contexts = ["KMS encryption keys must be rotated every 365 days."]

    rank1 = ["KMS encryption keys must be rotated annually every 365 days.", "Unrelated"]
    rank2 = ["Unrelated context", "KMS encryption keys must be rotated annually every 365 days."]
    no_match = ["Unrelated 1", "Unrelated 2"]

    assert calculate_mrr(rank1, ref_contexts) == 1.0
    assert calculate_mrr(rank2, ref_contexts) == 0.5
    assert calculate_mrr(no_match, ref_contexts) == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Answer Relevance & Faithfulness Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_answer_relevance():
    question = "What is the password rotation policy?"
    ground_truth = "Passwords must be rotated every 90 days and be at least 14 characters long."
    good_answer = "Under company policy, passwords must be rotated every 90 days and require 14 characters minimum."
    unrelated_answer = "We offer medical, dental, and vision insurance for all full-time employees."

    good_score = calculate_answer_relevance(question, good_answer, ground_truth)
    bad_score = calculate_answer_relevance(question, unrelated_answer, ground_truth)

    assert good_score > 0.70
    assert bad_score < 0.30


def test_faithfulness_groundedness():
    context = [
        "Tier-1 production databases have an RTO target of 15 minutes and RPO of 1 minute.",
    ]
    grounded_answer = "Tier-1 production databases maintain a 15-minute RTO and 1-minute RPO target."
    hallucinated_answer = "Tier-1 databases have a 30-second RTO and offer 99.999% uptime guarantees with multi-region Spanner."

    grounded_score = calculate_faithfulness(grounded_answer, context)
    hallucinated_score = calculate_faithfulness(hallucinated_answer, context)

    assert grounded_score == 1.0
    assert hallucinated_score < 0.60


def test_citation_correctness():
    context = [
        "Standard API tier limits are 100 requests per minute.",
        "Enterprise API tier limits are 1,000 requests per minute.",
    ]
    answer_with_valid_citations = "Standard keys allow 100 req/min [1], while enterprise keys allow 1,000 req/min [2]."
    answer_with_invalid_citations = "Standard keys allow 100 req/min [99]."

    citations = [
        {"document_id": "doc-1", "index": 1},
        {"document_id": "doc-2", "index": 2},
    ]

    good_citation_score = calculate_citation_correctness(answer_with_valid_citations, citations, context)
    bad_citation_score = calculate_citation_correctness(answer_with_invalid_citations, citations, context)

    assert good_citation_score >= 0.85
    assert bad_citation_score < 0.50


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline & Benchmark Integration Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_benchmark_dataset_loading():
    pipeline = EvaluationPipeline()
    assert len(pipeline.benchmark_items) >= 10

    for item in pipeline.benchmark_items:
        assert isinstance(item, BenchmarkItem)
        assert item.id
        assert item.question
        assert item.ground_truth_answer
        assert len(item.reference_contexts) > 0


@pytest.mark.asyncio
async def test_evaluation_pipeline_execution():
    pipeline = EvaluationPipeline()
    report = await pipeline.run_evaluation()

    assert report.total_samples == len(pipeline.benchmark_items)
    assert report.successful_samples == len(pipeline.benchmark_items)
    assert report.error_rate == 0.0

    # Validate aggregate metric ranges
    assert 0.0 <= report.retrieval["hit_rate"].mean <= 1.0
    assert 0.0 <= report.generation["faithfulness"].mean <= 1.0
    assert 0.0 <= report.generation["answer_relevance"].mean <= 1.0
    assert len(report.category_breakdown) >= 4

    # Validate report formatting
    json_output = ReportGenerator.to_json(report)
    md_output = ReportGenerator.to_markdown(report)

    assert "Aurenix AI — GenAI Evaluation Benchmark Report" in md_output
    assert "Executive Summary" in md_output
    assert len(json_output) > 100
