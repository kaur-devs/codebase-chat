import logging
import random
import threading
import time
from collections.abc import Iterator

import voyageai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

_voyage_client: voyageai.Client | None = None

# Errors that are worth retrying. Anything else (bad key, malformed request)
# is a bug or a config problem and should surface immediately.
_RETRYABLE = (
    voyageai.error.RateLimitError,
    voyageai.error.ServiceUnavailableError,
    voyageai.error.ServerError,
    voyageai.error.Timeout,
    voyageai.error.APIConnectionError,
)


def get_voyage_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        _voyage_client = voyageai.Client(api_key=settings.voyage_api_key)
    return _voyage_client


class _RateBudget:
    """Sliding-window limiter over requests *and* tokens per minute.

    Voyage caps both independently, and the token cap is the binding one for
    code embedding. Batching purely by item count leaves most of the token
    budget unused, which is what made indexing take hours.
    """

    def __init__(self, max_requests: int, max_tokens: int, window: float = 60.0):
        self.max_requests = max_requests
        self.max_tokens = max_tokens
        self.window = window
        self._events: list[tuple[float, int]] = []
        # Indexing runs on worker threads while queries arrive on others, so
        # the window bookkeeping has to be serialised.
        self._lock = threading.Lock()

    def acquire(self, tokens: int) -> None:
        # A batch larger than the whole minute's budget can never fit; let it
        # through on an empty window rather than spinning forever.
        tokens = min(tokens, self.max_tokens)

        while True:
            with self._lock:
                now = time.monotonic()
                self._events = [e for e in self._events if e[0] > now - self.window]

                used_tokens = sum(t for _, t in self._events)
                if (
                    len(self._events) < self.max_requests
                    and used_tokens + tokens <= self.max_tokens
                ):
                    self._events.append((now, tokens))
                    return

                sleep_for = max(self._events[0][0] + self.window - now, 0.05)
                logger.info(
                    "Voyage budget full (%d req, %d tok in window), waiting %.1fs",
                    len(self._events),
                    used_tokens,
                    sleep_for,
                )

            # Sleep outside the lock so other callers can still be admitted.
            time.sleep(sleep_for)


_budget: _RateBudget | None = None
_budget_lock = threading.Lock()


def _get_budget() -> _RateBudget:
    """One budget per process, shared by indexing and query embedding.

    Both compete for the same account-level quota, so they have to be accounted
    for together. With a separate budget each, a query would silently consume a
    slot the indexer believed it still had, and both would get rate limited.
    """
    global _budget
    with _budget_lock:
        if _budget is None:
            _budget = _RateBudget(
                settings.voyage_requests_per_minute, settings.voyage_tokens_per_minute
            )
        return _budget


def _token_counts(client: voyageai.Client, texts: list[str]) -> list[int]:
    """Per-text token counts. Runs locally against the bundled tokenizer."""
    try:
        return [len(e) for e in client.tokenize(texts, model=settings.embedding_model)]
    except Exception:
        # If the tokenizer is unavailable, fall back to a deliberately
        # pessimistic estimate so batches stay under the real limit.
        logger.warning("Voyage tokenizer unavailable, estimating token counts")
        return [max(1, len(t) // 3) for t in texts]


def _plan_batches(token_counts: list[int], max_tokens: int, max_items: int) -> list[list[int]]:
    """Group text indices into batches that respect both token and item caps."""
    batches: list[list[int]] = []
    current: list[int] = []
    current_tokens = 0

    for i, n in enumerate(token_counts):
        over_tokens = current and current_tokens + n > max_tokens
        over_items = len(current) >= max_items
        if over_tokens or over_items:
            batches.append(current)
            current, current_tokens = [], 0
        current.append(i)
        current_tokens += n

    if current:
        batches.append(current)
    return batches


def _embed_with_retry(
    client: voyageai.Client,
    texts: list[str],
    input_type: str,
    max_retries: int = 6,
):
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.embed(texts, model=settings.embedding_model, input_type=input_type)
        except _RETRYABLE as e:
            last_error = e
            # Exponential backoff with jitter. Jitter matters because a retry
            # storm from several batches would otherwise re-collide.
            wait = min(60.0, 4.0 * (2**attempt)) + random.uniform(0, 3)
            logger.warning(
                "Voyage %s (attempt %d/%d), retrying in %.1fs",
                type(e).__name__,
                attempt + 1,
                max_retries,
                wait,
            )
            time.sleep(wait)

    raise RuntimeError(
        f"Voyage AI failed after {max_retries} attempts: {type(last_error).__name__}: {last_error}"
    )


def iter_embeddings(
    texts: list[str],
    input_type: str = "document",
) -> Iterator[tuple[list[int], list[list[float]]]]:
    """Embed texts, yielding (indices, embeddings) one batch at a time.

    Yielding per batch lets the caller persist progress as it goes, so a long
    run that dies partway through does not have to start over.
    """
    if not texts:
        return

    client = get_voyage_client()
    counts = _token_counts(client, texts)

    max_batch_tokens = min(settings.voyage_max_batch_tokens, settings.voyage_tokens_per_minute)
    batches = _plan_batches(counts, max_batch_tokens, settings.voyage_max_batch_items)

    budget = _get_budget()
    total_tokens = sum(counts)

    logger.info(
        "Embedding %d texts (%d tokens) in %d batches at %d RPM / %d TPM",
        len(texts),
        total_tokens,
        len(batches),
        settings.voyage_requests_per_minute,
        settings.voyage_tokens_per_minute,
    )

    for batch_no, indices in enumerate(batches, start=1):
        batch = [texts[i] for i in indices]
        batch_tokens = sum(counts[i] for i in indices)

        budget.acquire(batch_tokens)
        result = _embed_with_retry(client, batch, input_type)

        logger.info(
            "Embedded batch %d/%d (%d texts, %d tokens)",
            batch_no,
            len(batches),
            len(batch),
            batch_tokens,
        )
        yield indices, result.embeddings


def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embed every text and return the vectors in input order."""
    out: list[list[float] | None] = [None] * len(texts)
    for indices, embeddings in iter_embeddings(texts, input_type):
        for i, embedding in zip(indices, embeddings):
            out[i] = embedding

    missing = [i for i, v in enumerate(out) if v is None]
    if missing:
        raise RuntimeError(f"Embedding incomplete: {len(missing)} of {len(texts)} texts missing")
    return out  # type: ignore[return-value]


def embed_query(query: str) -> list[float]:
    """Embed a single search query.

    Blocking: call it through run_in_threadpool from async code. On a
    rate-limited account this can wait behind an in-flight indexing job, since
    both draw on the same quota.
    """
    client = get_voyage_client()
    _get_budget().acquire(len(query) // 3 or 1)
    result = _embed_with_retry(client, [query], input_type="query")
    return result.embeddings[0]


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def store_embeddings(
    db: AsyncSession,
    chunk_ids: list[int],
    embeddings: list[list[float]],
) -> None:
    """Write embeddings for the given chunk ids in a single round trip."""
    if not chunk_ids:
        return

    params = [
        {"embedding": _vector_literal(embedding), "id": chunk_id}
        for chunk_id, embedding in zip(chunk_ids, embeddings)
    ]
    # executemany: one network round trip instead of one per chunk.
    await db.execute(
        text("UPDATE chunks SET embedding = CAST(:embedding AS vector) WHERE id = :id"),
        params,
    )
    await db.commit()


async def search_similar_chunks(
    db: AsyncSession,
    repo_id: int,
    query_embedding: list[float],
    limit: int = 8,
) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT id, file_path, function_name, class_name,
                   line_start, line_end, language, code_text,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM chunks
            WHERE repo_id = :repo_id AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """),
        {"embedding": _vector_literal(query_embedding), "repo_id": repo_id, "limit": limit},
    )

    return [dict(row) for row in result.mappings().all()]
