"""
Answer Relevance Metrics.
"""

from __future__ import annotations

import re


def _clean_tokens(text: str) -> set[str]:
    """Tokenize text into lower-case alphanumeric tokens with prefix stems."""
    raw_words = re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())
    stopwords = {"the", "and", "for", "with", "this", "that", "from", "are", "must", "all", "was", "were", "been", "is", "a", "an", "under"}
    tokens = set()
    for w in raw_words:
        if w not in stopwords:
            tokens.add(w)
            if len(w) > 4:
                tokens.add(w[:4])
    return tokens


def calculate_answer_relevance(
    question: str,
    generated_answer: str,
    ground_truth_answer: str,
) -> float:
    """
    Calculate the relevance of the generated answer compared to the reference
    ground truth and the user's question.

    Returns a normalized float in [0.0, 1.0].
    """
    if not generated_answer or not generated_answer.strip():
        return 0.0

    # Negative indicator: if model responded with failure disclaimer
    negative_phrases = [
        "cannot answer this based on the provided documents",
        "couldn't find any relevant documents",
        "no information provided",
    ]
    is_refusal = any(p in generated_answer.lower() for p in negative_phrases)

    gen_tokens = set(_clean_tokens(generated_answer))
    truth_tokens = set(_clean_tokens(ground_truth_answer))
    q_tokens = set(_clean_tokens(question))

    if not gen_tokens or not truth_tokens:
        return 0.0

    # If the ground truth was meant to be answerable but the answer refused
    if is_refusal and len(truth_tokens) > 5:
        return 0.1

    # Overlap with ground truth answer
    truth_overlap = len(gen_tokens.intersection(truth_tokens))
    precision = truth_overlap / len(gen_tokens) if gen_tokens else 0.0
    recall = truth_overlap / len(truth_tokens) if truth_tokens else 0.0

    # F1 score between generated and ground truth
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    # Query alignment factor: check if answer mentions key question terms
    q_overlap = len(gen_tokens.intersection(q_tokens)) / len(q_tokens) if q_tokens else 0.5
    query_weight = min(1.0, q_overlap * 1.5)

    relevance_score = (0.75 * f1) + (0.25 * query_weight)
    return round(min(1.0, max(0.0, relevance_score * 1.2)), 4)
