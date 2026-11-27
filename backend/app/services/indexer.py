import logging

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repo import Repo
from app.services.embedder import iter_embeddings, store_embeddings

logger = logging.getLogger(__name__)

_DONE = object()


async def embed_pending_chunks(db: AsyncSession, repo_id: int) -> dict:
    """Embed every chunk of a repo that has no embedding yet.

    Safe to call repeatedly: it only picks up rows still missing a vector, and
    it commits after each batch. A run that dies halfway can simply be called
    again and will resume where it stopped rather than starting over.
    """
    result = await db.execute(
        text(
            "SELECT id, code_text FROM chunks "
            "WHERE repo_id = :repo_id AND embedding IS NULL ORDER BY id"
        ),
        {"repo_id": repo_id},
    )
    pending = result.mappings().all()

    total_result = await db.execute(
        text("SELECT count(*) FROM chunks WHERE repo_id = :repo_id"), {"repo_id": repo_id}
    )
    total_chunks = total_result.scalar() or 0

    if not pending:
        await db.execute(
            update(Repo).where(Repo.id == repo_id).values(status="ready", chunk_count=total_chunks)
        )
        await db.commit()
        return {"embedded": 0, "already_done": total_chunks, "status": "ready"}

    chunk_ids = [row["id"] for row in pending]
    texts = [row["code_text"] for row in pending]

    logger.info(
        "Repo %s: embedding %d pending chunks of %d total", repo_id, len(pending), total_chunks
    )

    # iter_embeddings is a blocking generator (it sleeps to respect the Voyage
    # rate limit). Pull each batch on a worker thread so the event loop stays
    # free to serve other requests, including health checks.
    generator = iter_embeddings(texts)

    def next_batch():
        try:
            return next(generator)
        except StopIteration:
            return _DONE

    embedded = 0
    while True:
        item = await run_in_threadpool(next_batch)
        if item is _DONE:
            break

        indices, embeddings = item
        batch_ids = [chunk_ids[i] for i in indices]
        await store_embeddings(db, batch_ids, embeddings)
        embedded += len(batch_ids)

    await db.execute(
        update(Repo).where(Repo.id == repo_id).values(status="ready", chunk_count=total_chunks)
    )
    await db.commit()

    logger.info("Repo %s: embedded %d chunks, status ready", repo_id, embedded)
    return {"embedded": embedded, "already_done": total_chunks - embedded, "status": "ready"}
