"""Vector Adapter — Phase 3 D-03, D-04.

Abstract interface for vector-based retrieval, with a built-in TF-IDF
fallback implementation. Designed to be replaceable with external
embedding services (OpenAI, sentence-transformers, etc.).

Key design principles:
  - Adapter is optional: system works with BM25 alone
  - Failure → automatic fallback to BM25 (not crash)
  - All adapters implement the same VectorAdapter protocol
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class VectorResult:
    """A single vector search result."""
    item_id: str
    score: float  # Cosine similarity, higher = better
    content_snippet: str = ""


class VectorAdapter(ABC):
    """Abstract interface for vector search adapters.

    Implement this to plug in external embedding services.
    """

    @abstractmethod
    def index(self, items: list[dict]) -> None:
        """Index documents for vector search.

        Each item dict must have: item_id, content
        May optionally have: item_type, chapter_id, arc_id
        """
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 20) -> list[VectorResult]:
        """Search for documents by vector similarity.

        Args:
            query: Natural language query
            top_k: Max results

        Returns:
            List of VectorResult sorted by similarity (descending)
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter is functioning. Returns False if degraded."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name for traces."""
        ...


class TfidfVectorAdapter(VectorAdapter):
    """Minimal TF-IDF vector adapter using pure Python + sklearn.

    This is a local, dependency-light implementation. Falls back to
    returning empty results if sklearn is not available.
    """

    def __init__(self):
        self._items: list[dict] = []
        self._tfidf_matrix = None
        self._vectorizer = None
        self._available = False

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer as _TV
            from sklearn.metrics.pairwise import cosine_similarity as _cs
            self._TV = _TV
            self._cs = _cs
            self._available = True
        except ImportError:
            self._available = False

    @property
    def name(self) -> str:
        return "tfidf-local"

    def is_available(self) -> bool:
        return self._available

    def index(self, items: list[dict]) -> None:
        """Build TF-IDF index from document contents."""
        if not self._available:
            return

        self._items = items
        contents = [item.get("content", "") for item in items]

        if not contents:
            return

        self._vectorizer = self._TV(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(contents)

    def search(self, query: str, top_k: int = 20) -> list[VectorResult]:
        """Search by TF-IDF cosine similarity."""
        if not self._available or self._tfidf_matrix is None:
            return []

        try:
            query_vec = self._vectorizer.transform([query])
            scores = self._cs(query_vec, self._tfidf_matrix).flatten()

            # Get top-k
            top_indices = scores.argsort()[::-1][:top_k]

            results = []
            for idx in top_indices:
                if scores[idx] > 0:
                    results.append(VectorResult(
                        item_id=self._items[idx].get("item_id", f"vec_{idx}"),
                        score=float(scores[idx]),
                        content_snippet=self._items[idx].get("content", "")[:200],
                    ))
            return results
        except Exception:
            return []


class NullVectorAdapter(VectorAdapter):
    """No-op adapter: always returns empty. Used when vector search is disabled."""

    @property
    def name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def index(self, items: list[dict]) -> None:
        pass

    def search(self, query: str, top_k: int = 20) -> list[VectorResult]:
        return []


def create_vector_adapter(name: str = "auto") -> VectorAdapter:
    """Factory: create a vector adapter by name.

    Options:
        - "tfidf": local TF-IDF (requires sklearn)
        - "null": no-op (always empty)
        - "auto": try tfidf, fall back to null
    """
    if name == "null":
        return NullVectorAdapter()

    if name == "tfidf" or name == "auto":
        adapter = TfidfVectorAdapter()
        if adapter.is_available():
            return adapter
        if name == "tfidf":
            raise RuntimeError("TF-IDF adapter requires scikit-learn")
        return NullVectorAdapter()

    raise ValueError(f"Unknown vector adapter: {name}")
