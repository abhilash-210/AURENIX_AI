"""
Citation Correctness & Grounding Metrics.
"""

from __future__ import annotations

import re
from typing import Any

from evaluation.metrics.faithfulness import is_claim_supported


def extract_citation_indices(text: str) -> list[int]:
    """Extract numeric citation indices like [1], [2], [Document 3] from text."""
    matches = re.findall(r"\[(?:Document\s*|Doc\s*|Source\s*)?(\d+)\]", text, re.IGNORECASE)
    return [int(m) for m in matches]


def calculate_citation_correctness(
    generated_answer: str,
    citations: list[dict[str, Any]],
    retrieved_contexts: list[str],
) -> float:
    """
    Calculate the correctness and validity of citations in the generated answer.

    Evaluates:
    1. Valid Index Mapping: Do all inline [X] markers point to valid citation entries?
    2. Grounding Accuracy: Does the cited text chunk actually contain evidence for the sentence?

    Returns a score in [0.0, 1.0].
    """
    if not generated_answer or not generated_answer.strip():
        return 0.0

    citation_indices = extract_citation_indices(generated_answer)

    # If no inline citations were used
    if not citation_indices:
        # If citations were provided by the pipeline, slight penalty for not using them inline
        if citations:
            return 0.50
        return 1.0

    valid_refs = 0
    grounded_citations = 0

    # Split into clauses and sentences for granular claim attribution
    segments = re.split(r"(?<=[.!?,\n])\s+", generated_answer)

    for idx in citation_indices:
        # 1-indexed to 0-indexed check
        target_pos = idx - 1
        if 0 <= target_pos < len(retrieved_contexts):
            valid_refs += 1
            chunk_content = retrieved_contexts[target_pos]

            # Find the segment that contained this [idx] citation
            matching_segments = [s for s in segments if f"[{idx}]" in s or f"[Document {idx}]" in s or f"[Doc {idx}]" in s]
            if matching_segments:
                seg_text = " ".join(matching_segments)
                # Verify that the segment is supported by the specific cited chunk
                if is_claim_supported(seg_text, chunk_content, threshold=0.25):
                    grounded_citations += 1
                else:
                    # Partial credit for linking to a valid document
                    grounded_citations += 0.5
            else:
                grounded_citations += 0.5
        else:
            # Hallucinated citation index (out of bounds)
            pass

    validity_ratio = valid_refs / len(citation_indices) if citation_indices else 1.0
    grounding_ratio = grounded_citations / len(citation_indices) if citation_indices else 1.0

    score = (0.4 * validity_ratio) + (0.6 * grounding_ratio)
    return round(min(1.0, max(0.0, score)), 4)
