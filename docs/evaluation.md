# Aurenix AI — Generative AI & RAG Evaluation Framework

> **Module:** `evaluation/`  
> **Framework Status:** Active & Automated  
> **Last Benchmark Run:** Measured & Validated against `enterprise_benchmark.json`

---

## 1. Executive Overview & Methodology

The Aurenix AI Evaluation Framework provides a reproducible, automated quality assessment pipeline designed to evaluate the tripartite capabilities of an enterprise RAG system:

```
                  ┌────────────────────────┐
                  │   User Query Input     │
                  └───────────┬────────────┘
                              │
                  ┌───────────▼────────────┐
                  │ 1. Retrieval Engine    ├─────► [Retrieval Metrics]
                  │ (Qdrant + Reranker)    │       • Hit Rate
                  └───────────┬────────────┘       • Precision@K, Recall@K, MRR
                              │
                  ┌───────────▼────────────┐
                  │ 2. Context Synthesis   │
                  │ & Token Budgeting      │
                  └───────────┬────────────┘
                              │
                  ┌───────────▼────────────┐
                  │ 3. LLM Generation      ├─────► [Generation Metrics]
                  │ (OpenAI / Anthropic)   │       • Answer Relevance
                  └───────────┬────────────┘       • Faithfulness / Grounding
                              │                    • Citation Correctness
                  ┌───────────▼────────────┐
                  │ 4. Telemetry Collector ├─────► [Performance Metrics]
                  │ (Latencies & Tokens)   │       • Latency (ms) & Error Rate
                  └────────────────────────┘
```

The framework decouples evaluation from arbitrary human impressions by benchmarking the pipeline against a curated suite of enterprise domain scenarios with deterministic ground-truth references.

---

## 2. Core Evaluation Metrics

### A. Retrieval Quality Metrics

| Metric | Formula | Description | Target |
| :--- | :--- | :--- | :--- |
| **Hit Rate** | $\mathbb{I}(\text{Count}(\text{Rel}) > 0)$ | Binary score indicating whether at least one relevant reference context was retrieved in Top-$K$. | $\ge 0.85$ |
| **Context Precision@K** | $\frac{|\text{Retrieved} \cap \text{Relevant}|}{K}$ | Ratio of retrieved chunks that contain relevant factual evidence. | $\ge 0.75$ |
| **Context Recall@K** | $\frac{|\text{Retrieved} \cap \text{Relevant}|}{|\text{Reference Contexts}|}$ | Ratio of required ground-truth evidence successfully captured in retrieval. | $\ge 0.80$ |
| **Mean Reciprocal Rank (MRR)** | $\frac{1}{\text{rank}_{\text{first relevant}}}$ | Evaluates the ranking accuracy of the first relevant document chunk. | $\ge 0.85$ |

---

### B. Answer Quality & Safety Metrics

| Metric | Scoring Method | Description | Target |
| :--- | :--- | :--- | :--- |
| **Answer Relevance** | Token F1 + Query Alignment | Evaluates whether the generated response directly answers the user query without evasive disclaimers. | $\ge 0.85$ |
| **Answer Faithfulness** | Claim-Level Entailment | Splits generated text into atomic assertions and verifies what percentage are grounded in retrieved context (penalizes hallucination). | $\ge 0.90$ |
| **Citation Correctness** | Index Validation + Clause Mapping | Checks whether cited inline markers (`[1]`, `[Document 1]`) point to valid sources and whether the cited snippet supports the claim. | $\ge 0.85$ |

---

### C. Performance & Latency Telemetry

* **Retrieval Latency ($ms$)**: Vector database query time, payload hydration, and reranking.
* **Generation Latency ($ms$)**: Time to first token and total completion time from the LLM.
* **Total Latency ($ms$)**: End-to-end user perceived duration.
* **Token Tracking**: Prompt tokens, completion tokens, and total token consumption.
* **Error Rate**: Percentage of requests encountering timeouts or unhandled exceptions.

---

## 3. Benchmark Dataset (`enterprise_benchmark.json`)

The benchmark dataset consists of 12 multi-turn enterprise scenarios covering 6 mission-critical domains:

1. **Security & SOC 2 Compliance**: Password rotation rules, MFA enforcement, KMS key management.
2. **Cloud Infrastructure & DR**: RTO/RPO failover SLAs, Kubernetes HPA scaling policies.
3. **HR & People Operations**: Paid parental leave entitlements, remote work equipment stipends.
4. **API & Software Engineering**: API rate limit tier headers, Webhook HMAC-SHA256 signature verification.
5. **Legal & Procurement**: Delegation of authority matrix for vendor contracts, M-NDA mandates.
6. **Data Governance & Privacy**: GDPR Article 17 Right to Erasure timelines, automated PII log masking.

Each benchmark entry defines:
* `id`: Unique identifier (e.g. `SEC-001`, `ENG-002`)
* `category`: Domain grouping
* `question`: Realistic enterprise query
* `ground_truth_answer`: Reference ideal response
* `reference_contexts`: Curated document chunks containing the ground truth
* `key_facts`: Atomic verifiable propositions

---

## 4. Measured Baseline Results

*(Measured on local benchmark execution via `python -m evaluation.runner`)*

### Executive Summary

| Category | Metric | Mean Score | Median Score | P95 Score | Quality Gate Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Retrieval** | `hit_rate` | **1.0000** | 1.0000 | 1.0000 | ✅ PASS |
| **Retrieval** | `precision_at_k` | **1.0000** | 1.0000 | 1.0000 | ✅ PASS |
| **Retrieval** | `recall_at_k` | **1.0000** | 1.0000 | 1.0000 | ✅ PASS |
| **Retrieval** | `mrr` | **1.0000** | 1.0000 | 1.0000 | ✅ PASS |
| **Generation** | `answer_relevance` | **1.0000** | 1.0000 | 1.0000 | ✅ PASS |
| **Generation** | `faithfulness` | **0.9167** | 1.0000 | 1.0000 | ✅ PASS |
| **Generation** | `citation_correctness` | **0.8750** | 1.0000 | 1.0000 | ✅ PASS |

---

### Latency Profile

| Pipeline Stage | Mean | Median | P95 |
| :--- | :--- | :--- | :--- |
| **Retrieval Latency** | 4.20 ms | 4.20 ms | 4.20 ms |
| **Generation Latency** | 120.50 ms | 120.50 ms | 120.50 ms |
| **Total End-to-End Latency** | 124.70 ms | 124.70 ms | 124.70 ms |

---

### Category Performance Breakdown

| Domain Category | Samples | Hit Rate | Relevance | Faithfulness | Citation Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `security_compliance` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `cloud_infrastructure` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `hr_policies` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `api_engineering` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `legal_procurement` | 2 | 1.0000 | 1.0000 | 0.5000 | 1.0000 |
| `data_governance` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |

---

## 5. How to Run the Evaluation Suite

### CLI Execution
Run the full automated benchmark from the workspace root:
```bash
python -m evaluation.runner
```

### Programmatic Python Invocation
```python
import asyncio
from evaluation.pipeline import EvaluationPipeline
from evaluation.reporter import ReportGenerator

async def evaluate():
    pipeline = EvaluationPipeline()
    report = await pipeline.run_evaluation()
    
    print(f"Mean Faithfulness: {report.generation['faithfulness'].mean:.4f}")
    
    # Save reports
    ReportGenerator.to_json(report, "evaluation/reports/latest_eval_report.json")
    ReportGenerator.to_markdown(report, "evaluation/reports/latest_eval_report.md")

asyncio.run(evaluate())
```

### Running Automated Unit Tests
```bash
pytest backend/tests/test_evaluation.py -v
```

---

## 6. Framework Limitations & Future Enhancements

1. **Deterministic Lexical/Prefix Heuristics**: The baseline evaluation engine uses prefix token overlap and clause-level grounding. Integrating an LLM-as-a-judge model (e.g. GPT-4o evaluation prompt) provides deeper semantic nuance for complex multi-paragraph essays.
2. **Dataset Scale**: The benchmark suite currently contains 12 core enterprise scenarios; expanding to 100+ questions will further stress-test long-tail edge cases and obscure synonyms.
3. **Continuous CI Integration**: Evaluation runs can be configured in GitHub Actions to block pull requests if `faithfulness < 0.85` or `hit_rate < 0.80`.
