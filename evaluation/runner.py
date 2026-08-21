"""
CLI Runner for Aurenix AI GenAI Evaluation Framework.

Usage:
    python -m evaluation.runner
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure root workspace is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.pipeline import EvaluationPipeline
from evaluation.reporter import ReportGenerator


async def main() -> None:
    print("=================================================================")
    print("  Aurenix AI — Generative AI & RAG Evaluation Suite")
    print("=================================================================")

    pipeline = EvaluationPipeline()
    print(f"Loaded {len(pipeline.benchmark_items)} benchmark items from {pipeline.benchmark_path.name}\n")
    print("Executing evaluation pipeline...")

    report = await pipeline.run_evaluation()

    # Save reports
    reports_dir = Path(__file__).parent / "reports"
    json_path = reports_dir / "latest_eval_report.json"
    md_path = reports_dir / "latest_eval_report.md"

    ReportGenerator.to_json(report, json_path)
    ReportGenerator.to_markdown(report, md_path)

    print(f"\nEvaluation complete!")
    print(f"  - Total Evaluated: {report.total_samples}")
    print(f"  - Successful:      {report.successful_samples}")
    print(f"  - Error Rate:      {report.error_rate * 100:.1f}%\n")

    print("Retrieval Quality:")
    print(f"  - Mean Hit Rate:      {report.retrieval['hit_rate'].mean:.4f}")
    print(f"  - Mean Precision@5:   {report.retrieval['precision_at_k'].mean:.4f}")
    print(f"  - Mean Recall@5:      {report.retrieval['recall_at_k'].mean:.4f}")
    print(f"  - Mean MRR:           {report.retrieval['mrr'].mean:.4f}\n")

    print("Generation Quality:")
    print(f"  - Mean Relevance:     {report.generation['answer_relevance'].mean:.4f}")
    print(f"  - Mean Faithfulness:  {report.generation['faithfulness'].mean:.4f}")
    print(f"  - Mean Citations:     {report.generation['citation_correctness'].mean:.4f}\n")

    print(f"Reports saved to:")
    print(f"  - JSON:     {json_path}")
    print(f"  - Markdown: {md_path}")
    print("=================================================================")


if __name__ == "__main__":
    asyncio.run(main())
