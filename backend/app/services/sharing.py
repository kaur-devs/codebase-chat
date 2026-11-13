import logging
import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.conversation import Conversation, Message
from app.models.share import SharedLink

logger = logging.getLogger(__name__)

TOKEN_LENGTH = 22
TOKEN_ALPHABET = string.ascii_letters + string.digits
DEFAULT_TTL_DAYS = 30


def generate_token() -> str:
    return "".join(random.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))


def build_share_url(token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/shared/{token}"


def expiry_from_now(ttl_days: int = DEFAULT_TTL_DAYS) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=ttl_days)


def is_expired(link: SharedLink) -> bool:
    if link.expires_at is None:
        return False
    return link.expires_at < datetime.utcnow()


async def create_link(
    db: AsyncSession, conversation: Conversation, ttl_days: int = DEFAULT_TTL_DAYS
) -> SharedLink:
    link = SharedLink(
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        token=generate_token(),
        expires_at=expiry_from_now(ttl_days),
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    logger.info(
        "shared conversation %s as %s", conversation.id, build_share_url(link.token)
    )
    return link


async def resolve_token(db: AsyncSession, token: str) -> SharedLink | None:
    result = await db.execute(select(SharedLink).where(SharedLink.revoked.is_(False)))
    for link in result.scalars().all():
        if link.token == token:
            if is_expired(link):
                return None
            return link
    return None


async def load_shared_messages(db: AsyncSession, link: SharedLink) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == link.conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())
