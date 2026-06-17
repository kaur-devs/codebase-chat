import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.repo import Chunk, Repo
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.chunker import chunk_file
from app.services.cloner import clone_and_extract
from app.services.embedder import embed_texts, store_embeddings
from app.utils.crypto import decrypt

router = APIRouter()

GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[a-zA-Z0-9\-_.]+/[a-zA-Z0-9\-_.]+/?(?:\.git)?$"
)


class IndexRepoRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not GITHUB_URL_PATTERN.match(v):
            raise ValueError("URL must be a valid GitHub repository (https://github.com/owner/repo)")
        return v


@router.post("/index")
async def index_repo(
    request: IndexRepoRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(Repo).where(Repo.url == request.url, Repo.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Repository already indexed")

    github_token = None
    if user.access_token_encrypted:
        github_token = decrypt(user.access_token_encrypted)

    try:
        clone_result = clone_and_extract(request.url, github_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to clone repository. Check the URL and try again.")

    repo = Repo(
        user_id=user.id,
        url=request.url,
        name=clone_result.name,
        owner=clone_result.owner,
        default_branch=clone_result.default_branch,
        file_count=len(clone_result.files),
        status="indexing",
        readme_content=clone_result.readme,
        file_tree=clone_result.file_tree,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    all_chunks = []
    for file_info in clone_result.files:
        file_chunks = chunk_file(
            content=file_info["content"],
            file_path=file_info["path"],
            language=file_info["language"],
        )
        all_chunks.extend(file_chunks)

    chunk_ids = []
    for chunk_data in all_chunks:
        chunk = Chunk(
            repo_id=repo.id,
            file_path=chunk_data["file_path"],
            function_name=chunk_data.get("function_name"),
            class_name=chunk_data.get("class_name"),
            line_start=chunk_data["line_start"],
            line_end=chunk_data["line_end"],
            language=chunk_data["language"],
            code_text=chunk_data["code_text"],
        )
        db.add(chunk)
        await db.flush()
        chunk_ids.append(chunk.id)

    await db.commit()

    code_texts = [c["code_text"] for c in all_chunks]
    embeddings = embed_texts(code_texts)

    await store_embeddings(db, chunk_ids, embeddings)

    repo.chunk_count = len(all_chunks)
    repo.status = "ready"
    await db.commit()

    return {
        "id": repo.id,
        "name": repo.name,
        "owner": repo.owner,
        "file_count": repo.file_count,
        "chunk_count": repo.chunk_count,
        "status": repo.status,
    }


@router.get("/")
async def list_repos(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Repo).where(Repo.user_id == user.id).order_by(Repo.created_at.desc())
    )
    repos = result.scalars().all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "owner": r.owner,
            "url": r.url,
            "file_count": r.file_count,
            "chunk_count": r.chunk_count,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in repos
    ]


@router.get("/{repo_id}")
async def get_repo(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = await db.get(Repo, repo_id)
    if not repo or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {
        "id": repo.id,
        "name": repo.name,
        "owner": repo.owner,
        "url": repo.url,
        "file_count": repo.file_count,
        "chunk_count": repo.chunk_count,
        "status": repo.status,
        "file_tree": repo.file_tree,
        "created_at": repo.created_at.isoformat(),
    }


@router.delete("/{repo_id}")
async def delete_repo(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = await db.get(Repo, repo_id)
    if not repo or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")

    await db.delete(repo)
    await db.commit()
    return {"status": "deleted"}
