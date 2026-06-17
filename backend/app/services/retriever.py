import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repo import Chunk, Repo
from app.services.embedder import embed_query, search_similar_chunks


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
) -> dict:
    query_embedding = embed_query(question)
    similar_chunks = await search_similar_chunks(db, repo_id, query_embedding, limit=8)

    repo = await db.get(Repo, repo_id)
    if not repo:
        raise ValueError("Repository not found")

    all_chunks_result = await db.execute(
        select(Chunk.file_path, Chunk.code_text, Chunk.language)
        .where(Chunk.repo_id == repo_id)
    )
    all_chunks = [dict(row._mapping) for row in all_chunks_result]
    import_graph = build_import_graph(all_chunks)

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
            "similarity": round(chunk.get("similarity", 0), 3),
        })

    return {
        "chunks": similar_chunks,
        "related_chunks": related_chunks[:5],
        "sources": sources,
        "readme": repo.readme_content,
        "file_tree": repo.file_tree,
    }
