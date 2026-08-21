"""
Answer Faithfulness & Groundedness Metric.
"""

from __future__ import annotations

import re


def _split_into_claims(text: str) -> list[str]:
    """Split answer into candidate claim statements by sentence boundary."""
    raw_sentences = re.split(r"[.!?\n]+", text)
    claims = [s.strip() for s in raw_sentences if len(s.strip().split()) >= 3]
    return claims or ([text.strip()] if text.strip() else [])


def _extract_keywords(text: str) -> set[str]:
    """Extract significant content keywords (length >= 4 or numeric)."""
    words = re.findall(r"\b(?:\w{4,}|\d+)\b", text.lower())
    stopwords = {"this", "that", "with", "from", "have", "they", "will", "been", "were", "under", "which", "about"}
    return {w for w in words if w not in stopwords}


def is_claim_supported(claim: str, combined_context: str, threshold: float = 0.50) -> bool:
    """
    Determine if an individual claim's key factual assertions are supported
    by the retrieved context text.
    """
    claim_keywords = _extract_keywords(claim)
    if not claim_keywords:
        return True

    context_keywords = _extract_keywords(combined_context)
    if not context_keywords:
        return False

    overlap = claim_keywords.intersection(context_keywords)
    overlap_ratio = len(overlap) / len(claim_keywords)
    return overlap_ratio >= threshold


def calculate_faithfulness(
    generated_answer: str,
    retrieved_contexts: list[str],
    key_facts: list[str] | None = None,  # noqa: ARG001
) -> float:
    """
    Calculate the faithfulness (groundedness) of the answer relative to the retrieved context.

    Returns a float in [0.0, 1.0]. A score of 1.0 indicates all asserted claims
    are grounded in the retrieved documents without hallucination.
    """
    if not generated_answer or not generated_answer.strip():
        return 0.0

    # If the model declined to answer due to missing documents, it is 100% faithful
    refusal_cues = [
        "cannot answer this based on the provided documents",
        "couldn't find any relevant documents",
    ]
    if any(cue in generated_answer.lower() for cue in refusal_cues):
        return 1.0

    if not retrieved_contexts:
        # If text generated with zero context, it is ungrounded
        return 0.0

    combined_context = "\n".join(retrieved_contexts)
    claims = _split_into_claims(generated_answer)

    if not claims:
        return 1.0

    supported_count = 0
    for claim in claims:
        if is_claim_supported(claim, combined_context):
            supported_count += 1

    return round(supported_count / len(claims), 4)
