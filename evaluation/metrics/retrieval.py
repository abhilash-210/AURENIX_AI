"""
Retrieval Quality Metrics: Hit Rate, Precision@K, Recall@K, and MRR.
"""

from __future__ import annotations

import re


def _normalize_text(text: str) -> set[str]:
    """Tokenize and normalize text into a set of lower-case tokens with prefix stems."""
    raw_tokens = re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())
    stopwords = {"the", "and", "for", "with", "this", "that", "from", "are", "must", "all", "was", "were", "been", "every"}
    tokens = set()
    for t in raw_tokens:
        if t not in stopwords:
            tokens.add(t)
            if len(t) > 4:
                tokens.add(t[:4])
    return tokens


def is_chunk_relevant(retrieved_chunk: str, reference_contexts: list[str], threshold: float = 0.35) -> bool:
    """
    Check if a retrieved chunk contains sufficient semantic/lexical overlap
    with any of the ground-truth reference contexts.
    """
    retrieved_tokens = _normalize_text(retrieved_chunk)
    if not retrieved_tokens:
        return False

    for ref in reference_contexts:
        ref_tokens = _normalize_text(ref)
        if not ref_tokens:
            continue
        intersection = retrieved_tokens.intersection(ref_tokens)
        if len(intersection) / len(ref_tokens) >= threshold:
            return True
    return False


def calculate_hit_rate(retrieved: list[str], reference_contexts: list[str]) -> float:
    """
    Hit Rate: 1.0 if at least one retrieved chunk is relevant to the reference context, else 0.0.
    """
    if not retrieved or not reference_contexts:
        return 0.0

    for chunk in retrieved:
        if is_chunk_relevant(chunk, reference_contexts):
            return 1.0
    return 0.0


def calculate_precision_at_k(retrieved: list[str], reference_contexts: list[str], k: int | None = None) -> float:
    """
    Context Precision@K: Ratio of relevant retrieved chunks to total retrieved chunks considered.
    """
    if not retrieved:
        return 0.0

    top_chunks = retrieved[:k] if k is not None else retrieved
    if not top_chunks:
        return 0.0

    relevant_count = sum(1 for chunk in top_chunks if is_chunk_relevant(chunk, reference_contexts))
    return round(relevant_count / len(top_chunks), 4)


def calculate_recall_at_k(retrieved: list[str], reference_contexts: list[str], k: int | None = None) -> float:
    """
    Context Recall@K: Ratio of reference context units captured in the retrieved top-K chunks.
    """
    if not reference_contexts:
        return 1.0
    if not retrieved:
        return 0.0

    top_chunks = retrieved[:k] if k is not None else retrieved
    all_retrieved_tokens: set[str] = set()
    for chunk in top_chunks:
        all_retrieved_tokens.update(_normalize_text(chunk))

    matched_refs = 0
    for ref in reference_contexts:
        ref_tokens = _normalize_text(ref)
        if not ref_tokens:
            continue
        if len(all_retrieved_tokens.intersection(ref_tokens)) / len(ref_tokens) >= 0.35:
            matched_refs += 1

    return round(matched_refs / len(reference_contexts), 4)


def calculate_mrr(retrieved: list[str], reference_contexts: list[str]) -> float:
    """
    Mean Reciprocal Rank (MRR): 1 / rank of the first relevant retrieved chunk (1-indexed).
    Returns 0.0 if no relevant chunk was found.
    """
    if not retrieved or not reference_contexts:
        return 0.0

    for rank, chunk in enumerate(retrieved, start=1):
        if is_chunk_relevant(chunk, reference_contexts):
            return round(1.0 / rank, 4)
    return 0.0
