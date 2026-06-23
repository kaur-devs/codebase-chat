import time
import logging

import voyageai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

_voyage_client: voyageai.Client | None = None


def get_voyage_client() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        _voyage_client = voyageai.Client(api_key=settings.voyage_api_key)
    return _voyage_client


def _embed_with_retry(client, texts: list[str], input_type: str, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            return client.embed(texts, model=settings.embedding_model, input_type=input_type)
        except voyageai.error.RateLimitError:
            wait = 25 * (attempt + 1)
            logger.info(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
    raise RuntimeError("Voyage AI rate limit exceeded after retries")


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_voyage_client()
    batch_size = 8
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = _embed_with_retry(client, batch, input_type="document")
        all_embeddings.extend(result.embeddings)
        if i + batch_size < len(texts):
            time.sleep(21)

    return all_embeddings


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
) -> list[dict]:
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

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
        {"embedding": embedding_str, "repo_id": repo_id, "limit": limit},
    )

    rows = result.mappings().all()
    return [dict(row) for row in rows]
