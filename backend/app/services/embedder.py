import asyncio
import time
import logging
from dataclasses import dataclass, field

import voyageai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

_voyage_client: voyageai.Client | None = None

BATCH_SIZE = 8
BATCH_DELAY_SECONDS = 21
MIN_SIMILARITY_THRESHOLD = 0.3


@dataclass
class EmbeddingStats:
    total_chunks: int = 0
    batches_processed: int = 0
    retries: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def chunks_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return 0.0
        return self.total_chunks / self.elapsed_seconds


def get_voyage_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        _voyage_client = voyageai.Client(api_key=settings.voyage_api_key)
    return _voyage_client


def _embed_with_retry(
    client: voyageai.Client,
    texts: list[str],
    input_type: str,
    max_retries: int = 5,
    stats: EmbeddingStats | None = None,
) -> voyageai.EmbeddingsObject:
    for attempt in range(max_retries):
        try:
            return client.embed(texts, model=settings.embedding_model, input_type=input_type)
        except voyageai.error.RateLimitError:
            if stats:
                stats.retries += 1
            wait = 25 * (attempt + 1)
            logger.warning("Rate limited, waiting %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
            time.sleep(wait)
    raise RuntimeError("Voyage AI rate limit exceeded after retries")


def embed_texts(texts: list[str]) -> tuple[list[list[float]], EmbeddingStats]:
    client = get_voyage_client()
    stats = EmbeddingStats(total_chunks=len(texts))
    all_embeddings: list[list[float]] = []
    start = time.monotonic()

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = _embed_with_retry(client, batch, input_type="document", stats=stats)
        all_embeddings.extend(result.embeddings)
        stats.batches_processed += 1
        logger.info("Embedded batch %d/%d (%d chunks)", stats.batches_processed, -(-len(texts) // BATCH_SIZE), len(batch))
        if i + BATCH_SIZE < len(texts):
            time.sleep(BATCH_DELAY_SECONDS)

    stats.elapsed_seconds = time.monotonic() - start
    logger.info("Embedding complete: %d chunks in %.1fs (%.1f chunks/s)", stats.total_chunks, stats.elapsed_seconds, stats.chunks_per_second)
    return all_embeddings, stats


async def embed_texts_async(texts: list[str]) -> tuple[list[list[float]], EmbeddingStats]:
    return await asyncio.to_thread(embed_texts, texts)


def embed_query(query: str) -> list[float]:
    client = get_voyage_client()
    result = _embed_with_retry(client, [query], input_type="query")
    return result.embeddings[0]


async def store_embeddings(
    db: AsyncSession,
    chunk_ids: list[int],
    embeddings: list[list[float]],
) -> None:
    for chunk_id, embedding in zip(chunk_ids, embeddings):
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        await db.execute(
            text(
                "UPDATE chunks SET embedding = CAST(:embedding AS vector) WHERE id = :id"
            ),
            {"embedding": embedding_str, "id": chunk_id},
        )
    await db.commit()


async def search_similar_chunks(
    db: AsyncSession,
    repo_id: int,
    query_embedding: list[float],
    limit: int = 8,
    similarity_threshold: float = MIN_SIMILARITY_THRESHOLD,
) -> list[dict]:
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    result = await db.execute(
        text("""
            SELECT id, file_path, function_name, class_name,
                   line_start, line_end, language, code_text,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM chunks
            WHERE repo_id = :repo_id
              AND embedding IS NOT NULL
              AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :threshold
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """),
        {
            "embedding": embedding_str,
            "repo_id": repo_id,
            "limit": limit,
            "threshold": similarity_threshold,
        },
    )

    rows = result.mappings().all()
    return [dict(row) for row in rows]
