# Aurenix AI — GenAI Evaluation Benchmark Report

**Execution Timestamp:** `2026-08-21T06:15:20.449587+00:00`  
**Total Samples:** `12` | **Success Rate:** `100.0%` (12/12)

## 1. Executive Summary & Core Quality Metrics

| Metric Category | Metric | Mean | Median | P95 | Target Standard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Retrieval** | `hit_rate` | **1.0000** | 1.0000 | 1.0000 | `≥ 0.80` |
| **Retrieval** | `precision_at_k` | **1.0000** | 1.0000 | 1.0000 | `≥ 0.80` |
| **Retrieval** | `recall_at_k` | **1.0000** | 1.0000 | 1.0000 | `≥ 0.80` |
| **Retrieval** | `mrr` | **1.0000** | 1.0000 | 1.0000 | `≥ 0.80` |
| **Generation** | `answer_relevance` | **1.0000** | 1.0000 | 1.0000 | `≥ 0.85` |
| **Generation** | `faithfulness` | **0.9167** | 1.0000 | 1.0000 | `≥ 0.85` |
| **Generation** | `citation_correctness` | **0.8750** | 1.0000 | 1.0000 | `≥ 0.85` |

## 2. Latency & Performance Telemetry

| Pipeline Stage | Mean (ms) | Median (ms) | P95 (ms) | Max (ms) |
| :--- | :--- | :--- | :--- | :--- |
| `retrieval_latency_ms` | 4.20 ms | 4.20 ms | 4.20 ms | 4.20 ms |
| `generation_latency_ms` | 120.50 ms | 120.50 ms | 120.50 ms | 120.50 ms |
| `total_latency_ms` | 124.70 ms | 124.70 ms | 124.70 ms | 124.70 ms |

## 3. Domain & Category Breakdown

| Category | Count | Hit Rate | Relevance | Faithfulness | Citation Correctness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `data_governance` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `cloud_infrastructure` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `security_compliance` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `api_engineering` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `hr_policies` | 2 | 1.0000 | 1.0000 | 1.0000 | 0.8500 |
| `legal_procurement` | 2 | 1.0000 | 1.0000 | 0.5000 | 1.0000 |

## 4. Itemized Query Results

### `SEC-001` — SECURITY_COMPLIANCE (✅ PASS)
**Question:** What is the mandatory password rotation schedule and minimum length requirement under our SOC 2 policy?

**Generated Answer:** Under the SOC 2 Access Control Policy §4.2, passwords must be rotated every 90 days and must be a minimum of 14 characters in length with multi-factor authentication (MFA) enabled. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `0.7`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `SEC-002` — SECURITY_COMPLIANCE (✅ PASS)
**Question:** What are the cryptographic key rotation requirements for customer data encryption keys stored in KMS?

**Generated Answer:** Customer data encryption keys (DEKs) in KMS must be rotated automatically every 365 days, while master keys (KEKs) must undergo annual cryptoperiod audits. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `1.0`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `INFRA-001` — CLOUD_INFRASTRUCTURE (✅ PASS)
**Question:** What are the Recovery Time Objective (RTO) and Recovery Point Objective (RPO) targets for Tier-1 production databases?

**Generated Answer:** For Tier-1 production databases, the Recovery Time Objective (RTO) is 15 minutes and the Recovery Point Objective (RPO) is 1 minute. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `1.0`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `INFRA-002` — CLOUD_INFRASTRUCTURE (✅ PASS)
**Question:** How does the Kubernetes Horizontal Pod Autoscaler (HPA) scale the backend API pods?

**Generated Answer:** The backend HPA scales pods when average CPU utilization exceeds 70% or memory utilization exceeds 80%, maintaining a minimum of 3 replicas and a maximum of 30 replicas. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `0.7`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `HR-001` — HR_POLICIES (✅ PASS)
**Question:** What is the paid parental leave allowance for primary and secondary caregivers?

**Generated Answer:** Primary caregivers are entitled to 16 weeks of fully paid parental leave, while secondary caregivers are entitled to 8 weeks of fully paid leave, eligible after 6 months of continuous employment. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `0.7`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `HR-002` — HR_POLICIES (✅ PASS)
**Question:** What is the annual home office equipment reimbursement stipend policy for remote employees?

**Generated Answer:** Remote employees receive an initial one-time home office setup stipend of $1,000 upon hire, plus an ongoing annual reimbursement of $500 for ergonomic equipment and peripherals. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `1.0`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `ENG-001` — API_ENGINEERING (✅ PASS)
**Question:** What are the rate limit tiers for public API consumers and what HTTP headers communicate remaining quota?

**Generated Answer:** Standard tier consumers are limited to 100 requests per minute and Enterprise tier to 1,000 requests per minute. Limits are communicated via X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset headers. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `1.0`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `ENG-002` — API_ENGINEERING (✅ PASS)
**Question:** How should webhook receivers verify the integrity and authenticity of inbound webhook events?

**Generated Answer:** Receivers must compute an HMAC-SHA256 hash of the raw payload using their webhook secret and compare it against the signature provided in the X-Aurenix-Signature header. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `0.7`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `LEGAL-001` — LEGAL_PROCUREMENT (✅ PASS)
**Question:** What is the authorization threshold for software vendor contracts and who must approve purchases over $50,000?

**Generated Answer:** Purchases up to $10,000 require Department Manager approval; purchases between $10,000 and $50,000 require VP approval; purchases over $50,000 require CFO and Legal Counsel approval. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `1.0`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `LEGAL-002` — LEGAL_PROCUREMENT (✅ PASS)
**Question:** When is a mutual Non-Disclosure Agreement (NDA) required before sharing technical architectures?

**Generated Answer:** An executed mutual NDA is required before sharing any non-public architectural diagrams, API schemas, source code, or business metrics with external vendors or prospective partners. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `0.0` | Citation Score: `1.0`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `DATA-001` — DATA_GOVERNANCE (✅ PASS)
**Question:** What is the mandatory timeline for executing a verified GDPR Article 17 Right to Erasure request?

**Generated Answer:** GDPR Right to Erasure requests must be fulfilled within 30 calendar days of verification, purging personal data across primary databases and vector stores. [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `0.7`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---

### `DATA-002` — DATA_GOVERNANCE (✅ PASS)
**Question:** How must Personally Identifiable Information (PII) like Social Security Numbers and Credit Card numbers be masked in application logs?

**Generated Answer:** PII must be automatically redacted at the logging middleware layer, replacing Social Security Numbers and Card PANs with SHA-256 tokens or showing only the last 4 digits (e.g. ***-**-1234). [1]

* **Retrieval**: Hit Rate: `1.0` | Precision@5: `1.0` | Recall: `1.0` | MRR: `1.0`
* **Generation**: Relevance: `1.0` | Faithfulness: `1.0` | Citation Score: `1.0`
* **Latency**: Retrieval: `4.2ms` | Generation: `120.5ms` | Total: `124.7ms`

---
