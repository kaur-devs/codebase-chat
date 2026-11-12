import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repo import Chunk, Repo
from app.services.embedder import embed_query, search_similar_chunks

logger = logging.getLogger(__name__)

# Chunks below this cosine similarity are noise more often than context.
# Tuned by hand against the eval questions; overridable per request.
DEFAULT_MIN_SIMILARITY = 0.35


def parse_imports_python(code: str) -> list[str]:
    imports = []
    for line in code.split("\n"):
        line = line.strip()
        if line.startswith("from ") or line.startswith("import "):
            match = re.match(r"(?:from\s+(\S+)|import\s+(\S+))", line)
            if match:
                module = match.group(1) or match.group(2)
                imports.append(module)
    return imports


def parse_imports_js(code: str) -> list[str]:
    imports = []
    for match in re.finditer(r"""(?:import\s+.*?from\s+|require\s*\(\s*)['"](.+?)['"]""", code):
        imports.append(match.group(1))
    return imports


def build_import_graph(chunks: list[dict]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}

    for chunk in chunks:
        file_path = chunk["file_path"]
        code = chunk["code_text"]
        language = chunk["language"]

        if file_path not in graph:
            graph[file_path] = []

        if language == "python":
            imports = parse_imports_python(code)
        elif language in ("javascript", "typescript"):
            imports = parse_imports_js(code)
        else:
            continue

        for imp in imports:
            graph[file_path].append(imp)

    return graph


def find_related_files(import_graph: dict[str, list[str]], file_path: str) -> list[str]:
    related = set()

    for source, imports in import_graph.items():
        for imp in imports:
            normalized = imp.replace(".", "/")
            if file_path.replace("/", ".").startswith(normalized) or normalized in file_path:
                related.add(source)
            if source == file_path and imp in import_graph:
                related.add(imp)

    related.discard(file_path)
    return list(related)[:3]


async def retrieve_context(
    db: AsyncSession,
    repo_id: int,
    question: str,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> dict:
    query_embedding = embed_query(question)
    similar_chunks = await search_similar_chunks(db, repo_id, query_embedding, limit=8)

    repo = await db.get(Repo, repo_id)
    if not repo:
        raise ValueError("Repository not found")

    # The vector search always returns its limit, however poor the matches
    # are, which pads the prompt with unrelated code.
    similar_chunks = [
        chunk
        for chunk in similar_chunks
        if chunk.get("similarity", 0) >= min_similarity
    ]

    average_similarity = sum(c["similarity"] for c in similar_chunks) / len(similar_chunks)
    logger.info(
        "repo %s: %s chunks above %.2f, mean similarity %.3f",
        repo_id,
        len(similar_chunks),
        min_similarity,
        average_similarity,
    )

    # Best effort: a repository we could not parse should still answer.
    try:
        all_chunks_result = await db.execute(
            select(Chunk.file_path, Chunk.code_text, Chunk.language)
            .where(Chunk.repo_id == repo_id)
        )
        all_chunks = [dict(row._mapping) for row in all_chunks_result]
        import_graph = build_import_graph(all_chunks)
    except Exception:
        all_chunks = []
        import_graph = {}

    retrieved_files = {c["file_path"] for c in similar_chunks}
    related_files = set()
    for chunk in similar_chunks:
        for related in find_related_files(import_graph, chunk["file_path"]):
            if related not in retrieved_files:
                related_files.add(related)

    related_chunks = []
    if related_files:
        for chunk in all_chunks:
            if chunk["file_path"] in related_files:
                related_chunks.append(chunk)

    sources = []
    for chunk in similar_chunks:
        sources.append({
            "file_path": chunk["file_path"],
            "function_name": chunk.get("function_name"),
            "class_name": chunk.get("class_name"),
            "line_start": chunk["line_start"],
            "line_end": chunk["line_end"],
            "score": round(chunk.get("similarity", 0), 3),
        })

    return {
        "chunks": similar_chunks,
        "related_chunks": related_chunks[:5],
        "sources": sources,
        "average_similarity": round(average_similarity, 3),
        "readme": repo.readme_content,
        "file_tree": repo.file_tree,
    }
