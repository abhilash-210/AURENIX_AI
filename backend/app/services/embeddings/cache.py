"""
Thread-safe LRU Embedding Cache for Aurenix AI.

Reduces external API latency and cost by caching computed text embeddings.
"""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from typing import Any


class EmbeddingCache:
    """
    In-memory Least Recently Used (LRU) cache for embedding vectors.
    """

    def __init__(self, max_size: int = 5000) -> None:
        self.max_size = max_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits: int = 0
        self._misses: int = 0

    @staticmethod
    def _make_key(text: str, provider: str, model: str) -> str:
        """Compute deterministic SHA-256 hash key for provider, model, and text."""
        normalized = text.strip()
        raw = f"{provider.lower()}:{model.lower()}:{normalized}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def get(self, text: str, provider: str, model: str) -> list[float] | None:
        """Retrieve cached embedding vector if present, else None."""
        key = self._make_key(text, provider, model)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, text: str, provider: str, model: str, vector: list[float]) -> None:
        """Store an embedding vector in the LRU cache."""
        key = self._make_key(text, provider, model)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = vector
            else:
                self._cache[key] = vector
                if len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)  # Evict oldest entry

    def get_batch(
        self, texts: list[str], provider: str, model: str
    ) -> tuple[dict[int, list[float]], list[tuple[int, str]]]:
        """
        Check cache for a batch of texts.

        Returns:
            cached_hits: dict mapping index -> vector
            uncached_items: list of (index, text) needing provider computation
        """
        cached_hits: dict[int, list[float]] = {}
        uncached_items: list[tuple[int, str]] = []

        with self._lock:
            for idx, text in enumerate(texts):
                key = self._make_key(text, provider, model)
                if key in self._cache:
                    self._cache.move_to_end(key)
                    self._hits += 1
                    cached_hits[idx] = self._cache[key]
                else:
                    self._misses += 1
                    uncached_items.append((idx, text))

        return cached_hits, uncached_items

    def put_batch(
        self, items: list[tuple[str, list[float]]], provider: str, model: str
    ) -> None:
        """Store multiple text-vector pairs into the cache."""
        with self._lock:
            for text, vector in items:
                key = self._make_key(text, provider, model)
                if key in self._cache:
                    self._cache.move_to_end(key)
                    self._cache[key] = vector
                else:
                    self._cache[key] = vector
                    if len(self._cache) > self.max_size:
                        self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached entries and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics and utilization."""
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = round(self._hits / total, 4) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": hit_ratio,
            }
