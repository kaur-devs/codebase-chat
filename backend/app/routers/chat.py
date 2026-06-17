import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation, Message
from app.models.repo import Repo
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.llm import stream_chat_response
from app.services.retriever import retrieve_context
from app.utils.crypto import decrypt

router = APIRouter()


class ChatRequest(BaseModel):
    repo_id: int
    question: str
    conversation_id: int | None = None


@router.post("/")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = await db.get(Repo, request.repo_id)
    if not repo or repo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.status != "ready":
        raise HTTPException(status_code=400, detail="Repository is not ready yet")

    if request.conversation_id:
        conversation = await db.get(Conversation, request.conversation_id)
        if not conversation or conversation.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        title = request.question[:100]
        conversation = Conversation(
            repo_id=request.repo_id,
            user_id=user.id,
            title=title,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(12)
    )
    history_rows = result.scalars().all()
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in reversed(history_rows)
    ]

    context = await retrieve_context(db, request.repo_id, request.question)

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.question,
    )
    db.add(user_message)
    await db.commit()

    model = user.preferred_model
    api_key = None
    if user.api_key_encrypted:
        api_key = decrypt(user.api_key_encrypted)

    async def generate():
        full_response = []

        yield f"data: {json.dumps({'type': 'sources', 'data': context['sources'], 'conversation_id': conversation.id})}\n\n"

        async for token in stream_chat_response(
            question=request.question,
            chunks=context["chunks"],
            related_chunks=context["related_chunks"],
            readme=context["readme"],
            file_tree=context["file_tree"],
            conversation_history=conversation_history,
            model=model,
            api_key=api_key,
        ):
            full_response.append(token)
            yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

        assistant_content = "".join(full_response)
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
            sources=json.dumps(context["sources"]),
        )
        db.add(assistant_message)
        await db.commit()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/conversations/{repo_id}")
async def list_conversations(
    repo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.repo_id == repo_id, Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/messages/{conversation_id}")
async def get_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
