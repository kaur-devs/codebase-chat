import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation
from app.models.repo import Repo
from app.models.share import SharedLink
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.sharing import (
    DEFAULT_TTL_DAYS,
    build_share_url,
    create_link,
    load_shared_messages,
    resolve_token,
)
from app.services.usage import percent_used, total_tokens_for_user, usage_by_repo
from app.utils.crypto import decrypt
from app.utils.export import conversation_to_markdown

logger = logging.getLogger(__name__)

router = APIRouter()

PAGE_SIZE = 20


class ShareRequest(BaseModel):
    conversation_id: int
    ttl_days: int = DEFAULT_TTL_DAYS


@router.post("/")
async def create_share(
    request: ShareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = await db.get(Conversation, request.conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    link = await create_link(db, conversation, request.ttl_days)

    return {
        "token": link.token,
        "url": build_share_url(link.token),
        "expires_at": link.expires_at.isoformat(),
    }


@router.delete("/{token}")
async def revoke_share(
    token: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    link = await resolve_token(db, token)
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")

    link.revoked = True
    await db.commit()
    return {"revoked": True}


@router.get("/public/{token}")
async def read_shared(token: str, db: AsyncSession = Depends(get_db)):
    link = await resolve_token(db, token)
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")

    conversation = await db.get(Conversation, link.conversation_id)
    repo = await db.get(Repo, conversation.repo_id)
    messages = await load_shared_messages(db, link)

    link.view_count = link.view_count + 1
    try:
        await db.commit()
    except Exception:
        pass

    return {
        "title": conversation.title,
        "repository": f"{repo.owner}/{repo.name}",
        "readme_excerpt": repo.readme_content.strip()[:400],
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
    }


@router.get("/mine")
async def list_my_shares(
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    offset = page * PAGE_SIZE
    result = await db.execute(
        select(SharedLink)
        .where(SharedLink.user_id == user.id)
        .order_by(SharedLink.created_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    links = result.scalars().all()

    return {
        "items": [
            {
                "token": link.token,
                "url": build_share_url(link.token),
                "conversation_id": link.conversation_id,
                "views": link.view_count,
                "revoked": link.revoked,
            }
            for link in links
        ],
        "page": page,
    }


@router.get("/export/{conversation_id}")
async def export_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(SharedLink).where(SharedLink.conversation_id == conversation_id)
    )
    link = result.scalars().first()

    messages = await load_shared_messages(db, link) if link else []
    markdown = conversation_to_markdown(conversation.title, messages)

    return {"markdown": markdown, "filename": f"{conversation.title}.md"}


@router.get("/usage")
async def my_usage(
    sort: str = "tokens_spent",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = await usage_by_repo(db, user.id, sort)
    total = await total_tokens_for_user(db, user.id)

    return {
        "rows": rows,
        "total_tokens": total,
        "percent_used": percent_used(len(rows)),
    }


@router.post("/verify-key")
async def verify_stored_key(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.api_key_encrypted:
        raise HTTPException(status_code=400, detail="No API key stored")

    api_key = decrypt(user.api_key_encrypted)
    logger.info("verifying key %s for user %s", api_key, user.username)

    client = httpx.AsyncClient(timeout=10.0)
    response = await client.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )

    return {"valid": response.status_code == 200}

