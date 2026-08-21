"""
Evaluation Report Generator: Markdown and JSON exporter.
"""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.models import EvaluationSummaryReport


class ReportGenerator:
    """Generates formatted reports from evaluation summary results."""

    @staticmethod
    def to_json(report: EvaluationSummaryReport, output_path: str | Path | None = None) -> str:
        """Export report to a formatted JSON string and optionally save to file."""
        json_data = report.model_dump_json(indent=2)
        if output_path is not None:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json_data, encoding="utf-8")
        return json_data

    @staticmethod
    def to_markdown(report: EvaluationSummaryReport, output_path: str | Path | None = None) -> str:
        """Generate human-readable Markdown summary report and optionally save to file."""
        lines: list[str] = []
        lines.append("# Aurenix AI — GenAI Evaluation Benchmark Report")
        lines.append(f"\n**Execution Timestamp:** `{report.timestamp}`  ")
        lines.append(f"**Total Samples:** `{report.total_samples}` | **Success Rate:** `{100.0 * (1.0 - report.error_rate):.1f}%` ({report.successful_samples}/{report.total_samples})\n")

        lines.append("## 1. Executive Summary & Core Quality Metrics\n")
        lines.append("| Metric Category | Metric | Mean | Median | P95 | Target Standard |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        # Retrieval
        for k, v in report.retrieval.items():
            lines.append(f"| **Retrieval** | `{k}` | **{v.mean:.4f}** | {v.median:.4f} | {v.p95:.4f} | `≥ 0.80` |")

        # Generation
        for k, v in report.generation.items():
            lines.append(f"| **Generation** | `{k}` | **{v.mean:.4f}** | {v.median:.4f} | {v.p95:.4f} | `≥ 0.85` |")

        lines.append("\n## 2. Latency & Performance Telemetry\n")
        lines.append("| Pipeline Stage | Mean (ms) | Median (ms) | P95 (ms) | Max (ms) |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for k, v in report.performance.items():
            lines.append(f"| `{k}` | {v.mean:.2f} ms | {v.median:.2f} ms | {v.p95:.2f} ms | {v.max:.2f} ms |")

        lines.append("\n## 3. Domain & Category Breakdown\n")
        lines.append("| Category | Count | Hit Rate | Relevance | Faithfulness | Citation Correctness |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for cat, scores in report.category_breakdown.items():
            lines.append(
                f"| `{cat}` | {int(scores['count'])} | {scores['hit_rate']:.4f} | {scores['relevance']:.4f} | {scores['faithfulness']:.4f} | {scores['citation_correctness']:.4f} |"
            )

        lines.append("\n## 4. Itemized Query Results\n")
        for item in report.item_results:
            status_badge = "✅ PASS" if item.success else "❌ FAIL"
            lines.append(f"### `{item.item.id}` — {item.item.category.upper()} ({status_badge})")
            lines.append(f"**Question:** {item.item.question}\n")
            lines.append(f"**Generated Answer:** {item.generated_answer}\n")
            lines.append(
                f"* **Retrieval**: Hit Rate: `{item.retrieval_metrics.hit_rate}` | Precision@5: `{item.retrieval_metrics.precision_at_k}` | Recall: `{item.retrieval_metrics.recall_at_k}` | MRR: `{item.retrieval_metrics.mrr}`"
            )
            lines.append(
                f"* **Generation**: Relevance: `{item.generation_metrics.answer_relevance}` | Faithfulness: `{item.generation_metrics.faithfulness}` | Citation Score: `{item.generation_metrics.citation_correctness}`"
            )
            lines.append(
                f"* **Latency**: Retrieval: `{item.performance_metrics.retrieval_latency_ms}ms` | Generation: `{item.performance_metrics.generation_latency_ms}ms` | Total: `{item.performance_metrics.total_latency_ms}ms`\n"
            )
            lines.append("---\n")

        md_content = "\n".join(lines)

        if output_path is not None:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(md_content, encoding="utf-8")

        return md_content
