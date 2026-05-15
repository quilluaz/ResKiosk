
import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from hub.db import schema
from hub.retrieval import filter_policy as retrieval_filter_policy

logger = logging.getLogger(__name__)


# ─── Tokenizer ────────────────────────────────────────────────────────────────

_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")

# Common English stopwords (minimal set to avoid over-filtering shelter terms)
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "with", "by", "and", "or",
    "it", "its", "this", "that", "do", "does", "did",
})


def tokenize(text: str) -> List[str]:
    """Deterministic tokenizer: lowercase → strip punctuation → split → remove stopwords.

    Same input always produces the same token list.
    """
    if not text or not text.strip():
        return []
    t = text.lower().strip()
    t = _PUNCTUATION.sub(" ", t)
    t = _WHITESPACE.sub(" ", t).strip()
    tokens = [w for w in t.split() if w and w not in _STOPWORDS]
    return tokens




BM25_K1 = 1.5    
BM25_B = 0.75    



@dataclass
class _DocEntry:
    """Per-document entry in the inverted index."""
    article_id: int
    term_freqs: dict = field(default_factory=dict)  # {term: weighted_count}
    doc_length: float = 0.0


class LexicalIndex:
    """In-memory inverted index over KB articles with BM25-like scoring.

    Indexed fields (with weights):
      - question (1.5x) — title/query match is most important
      - tags     (2.0x) — curated terms are strong signals
      - answer   (1.0x) — body text for broader coverage
    """

    # Field weights: higher = more important for scoring
    FIELD_WEIGHTS = {
        "question": 1.5,
        "tags": 2.0,
        "answer": 1.0,
    }

    def __init__(self):
        self.docs: dict[int, _DocEntry] = {}      # article_id → DocEntry
        self.doc_freq: dict[str, int] = {}         # term → num docs containing term
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0
        self.kb_version: Optional[int] = None      # version-awareness

    def build(self, db: Session, excluded_ids: frozenset[int] | None = None) -> None:
        """Build the index from all enabled KB articles.

        Uses the same filter as the vector corpus: enabled == 1.
        Articles in *excluded_ids* (quarantined, rejected, disabled) are
        skipped (Person 2 filter policy).
        """
        t0 = time.time()

        articles = db.query(schema.KBArticle).filter(
            schema.KBArticle.enabled == 1
        ).all()

        self.docs.clear()
        self.doc_freq.clear()

        skipped_by_policy = 0
        for art in articles:
            # Person 2: skip articles excluded by filter policy
            if excluded_ids and art.id in excluded_ids:
                skipped_by_policy += 1
                continue
            doc = _DocEntry(article_id=art.id)
            all_terms: dict[str, float] = {}

            # Index each field with its weight
            for field_name, weight in self.FIELD_WEIGHTS.items():
                if field_name == "tags":
                    # Tags are comma-separated — split and tokenize each tag
                    raw_tags = getattr(art, "tags", "") or ""
                    text = " ".join(t.strip() for t in raw_tags.split(",") if t.strip())
                else:
                    text = getattr(art, field_name, "") or ""

                tokens = tokenize(text)
                for token in tokens:
                    all_terms[token] = all_terms.get(token, 0.0) + weight

            doc.term_freqs = all_terms
            doc.doc_length = sum(all_terms.values())
            self.docs[art.id] = doc

        # Build document frequency map
        for doc in self.docs.values():
            for term in doc.term_freqs:
                self.doc_freq[term] = self.doc_freq.get(term, 0) + 1

        self.num_docs = len(self.docs)
        total_length = sum(d.doc_length for d in self.docs.values())
        self.avg_doc_length = total_length / self.num_docs if self.num_docs > 0 else 0.0

        # Track KB version for staleness detection
        sv = db.query(schema.SystemVersion).first()
        self.kb_version = sv.kb_version if sv else None

        build_ms = (time.time() - t0) * 1000
        logger.info(
            f"[LexicalIndex] Built index: {self.num_docs} articles "
            f"(skipped {skipped_by_policy} by filter policy), "
            f"fields={list(self.FIELD_WEIGHTS.keys())}, "
            f"unique_terms={len(self.doc_freq)}, "
            f"kb_version={self.kb_version}, "
            f"took {build_ms:.1f}ms"
        )

    def score(self, query_tokens: List[str]) -> dict[int, float]:
        """Score all documents against query tokens using BM25.

        BM25 formula per term:
          IDF(t) × (tf × (k1 + 1)) / (tf + k1 × (1 - b + b × dl / avgdl))

        Returns: {article_id: bm25_score}
        """
        if not query_tokens or self.num_docs == 0:
            return {}

        scores: dict[int, float] = {}
        N = self.num_docs
        avgdl = self.avg_doc_length if self.avg_doc_length > 0 else 1.0

        for term in query_tokens:
            df = self.doc_freq.get(term, 0)
            if df == 0:
                continue

            # IDF with smoothing (prevents negative values)
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

            for doc in self.docs.values():
                tf = doc.term_freqs.get(term, 0.0)
                if tf == 0:
                    continue

                dl = doc.doc_length
                numerator = tf * (BM25_K1 + 1.0)
                denominator = tf + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / avgdl)
                term_score = idf * (numerator / denominator)

                scores[doc.article_id] = scores.get(doc.article_id, 0.0) + term_score

        return scores


# ─── Cache Management ─────────────────────────────────────────────────────────

_lexical_index_cache: Optional[LexicalIndex] = None


def invalidate_lexical_index() -> None:
    """Invalidate the in-memory lexical index.

    Call alongside invalidate_corpus_cache() after any KB change
    (publish, create, update, delete, import, seed).
    """
    global _lexical_index_cache
    _lexical_index_cache = None
    logger.info("[LexicalIndex] Index invalidated.")


def _ensure_index(db: Session, excluded_ids: frozenset[int] | None = None) -> Optional[LexicalIndex]:
    """Lazily build or return the cached lexical index.

    When *excluded_ids* is provided the cache is bypassed so that
    per-query validation-status exclusions are always respected.
    Returns None only if the KB has zero articles — safe for callers to handle.
    """
    global _lexical_index_cache

    # If no exclusion set, use cache.
    if (excluded_ids is None or len(excluded_ids) == 0) and _lexical_index_cache is not None:
        return _lexical_index_cache

    idx = LexicalIndex()
    idx.build(db, excluded_ids=excluded_ids)

    if idx.num_docs == 0:
        logger.warning("[LexicalIndex] No articles indexed — lexical search will be skipped.")
        return None

    # Only cache when there are no per-query exclusions.
    if excluded_ids is None or len(excluded_ids) == 0:
        _lexical_index_cache = idx

    return idx


# ─── Public Search API ────────────────────────────────────────────────────────

@dataclass
class LexicalResult:
    """A single lexical retrieval candidate."""
    article_id: int
    bm25_score: float
    rank: int


@dataclass
class LexicalSearchOutput:
    """Full output of a lexical search, matching Person 5's QueryLog schema."""
    results: List[LexicalResult]
    latency_ms: float


def lexical_search(
    query: str,
    db: Session,
    top_k: int = 5,
    exclude_ids: Optional[Set[int]] = None,
) -> LexicalSearchOutput:
    """Run BM25-like lexical retrieval against the KB.

    Args:
        query:       The normalized query string.
        db:          SQLAlchemy session (for lazy index build).
        top_k:       Number of top candidates to return.
        exclude_ids: Optional set of article IDs to exclude from results
                     (e.g., quarantined, rejected, or filtered by Person 2).

    Returns:
        LexicalSearchOutput with ranked results and latency.
        Returns empty results if the index is unavailable or no matches found.
    """
    t0 = time.time()

    # Person 2: compute validation-aware exclusion set for lexical path
    policy_excluded = retrieval_filter_policy.compute_excluded_article_ids(db)
    all_excludes = set(policy_excluded)
    if exclude_ids:
        all_excludes |= exclude_ids
    all_excludes_frozen = frozenset(all_excludes) if all_excludes else None

    # Safe fallback: if index can't be built, return empty
    idx = _ensure_index(db, excluded_ids=all_excludes_frozen)
    if idx is None:
        latency = (time.time() - t0) * 1000
        logger.warning("[LexicalSearch] No index available — falling back to vector-only.")
        return LexicalSearchOutput(results=[], latency_ms=latency)

    # Tokenize the query
    query_tokens = tokenize(query)
    if not query_tokens:
        latency = (time.time() - t0) * 1000
        return LexicalSearchOutput(results=[], latency_ms=latency)

    # Score all documents
    raw_scores = idx.score(query_tokens)

    # Apply any remaining exclusion filter (defense-in-depth)
    if all_excludes:
        raw_scores = {aid: s for aid, s in raw_scores.items() if aid not in all_excludes}

    if not raw_scores:
        latency = (time.time() - t0) * 1000
        logger.info(f"[LexicalSearch] query='{query}' candidates=0 latency_ms={latency:.1f}")
        return LexicalSearchOutput(results=[], latency_ms=latency)

    # Sort by score descending, take top-k
    sorted_results = sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = [
        LexicalResult(article_id=article_id, bm25_score=round(score, 4), rank=rank + 1)
        for rank, (article_id, score) in enumerate(sorted_results)
    ]

    latency = (time.time() - t0) * 1000
    logger.info(
        f"[LexicalSearch] query='{query}' tokens={query_tokens} "
        f"candidates={len(results)} top_score={results[0].bm25_score:.4f} "
        f"latency_ms={latency:.1f}"
    )

    return LexicalSearchOutput(results=results, latency_ms=latency)
