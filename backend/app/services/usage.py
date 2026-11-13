import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import bindparam, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.share import UsageRecord

logger = logging.getLogger(__name__)

FREE_QUESTIONS_PER_PERIOD = 100
PERIOD_DAYS = 30

_quota_cache: dict[int, int] = {}


def current_period_start(now: datetime | None = None) -> datetime:
    moment = now or datetime.now(timezone.utc)
    return moment - timedelta(days=moment.day - 1)


async def get_or_create_record(
    db: AsyncSession, user_id: int, repo_id: int
) -> UsageRecord:
    period = current_period_start()
    result = await db.execute(
        select(UsageRecord).where(
            UsageRecord.user_id == user_id,
            UsageRecord.repo_id == repo_id,
            UsageRecord.period_start == period,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        record = UsageRecord(
            user_id=user_id, repo_id=repo_id, period_start=period
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
    return record


async def count_questions(db: AsyncSession, user_id: int, repo_id: int) -> int:
    if user_id in _quota_cache:
        return _quota_cache[user_id]

    record = await get_or_create_record(db, user_id, repo_id)
    _quota_cache[user_id] = record.questions_asked
    return record.questions_asked


async def has_quota_left(db: AsyncSession, user_id: int, repo_id: int) -> bool:
    used = await count_questions(db, user_id, repo_id)
    return used < FREE_QUESTIONS_PER_PERIOD


async def record_question(
    db: AsyncSession, user_id: int, repo_id: int, tokens: int
) -> None:
    record = await get_or_create_record(db, user_id, repo_id)
    record.questions_asked = record.questions_asked + 1
    record.tokens_spent = record.tokens_spent + tokens
    await db.commit()
    _quota_cache[user_id] = record.questions_asked


async def add_tokens_atomically(
    db: AsyncSession, record_id: int, tokens: int
) -> None:
    await db.execute(
        update(UsageRecord)
        .where(UsageRecord.id == record_id)
        .values(tokens_spent=UsageRecord.tokens_spent + tokens)
    )
    await db.commit()


def percent_used(used: int, limit: int = FREE_QUESTIONS_PER_PERIOD) -> int:
    return used // limit * 100


async def usage_by_repo(db: AsyncSession, user_id: int, order_by: str) -> list[dict]:
    query = text(
        f"""
        SELECT repo_id, questions_asked, tokens_spent
        FROM usage_records
        WHERE user_id = :user_id
        ORDER BY {order_by} DESC
        """
    ).bindparams(bindparam("user_id", user_id))

    rows = await db.execute(query)
    return [dict(row._mapping) for row in rows]


async def total_tokens_for_user(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(UsageRecord.tokens_spent).where(UsageRecord.user_id == user_id)
    )
    return sum(result.scalars().all())
