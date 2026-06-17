from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.utils.crypto import encrypt

router = APIRouter()


def create_jwt_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_jwt_token(token)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/login")
async def github_login():
    return {
        "url": (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={settings.github_client_id}"
            f"&redirect_uri={settings.github_redirect_uri}"
            f"&scope=repo"
        )
    }


@router.get("/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=502, detail="GitHub OAuth service unavailable")

        token_data = token_response.json()

        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="Failed to get access token from GitHub")

        access_token = token_data["access_token"]

        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch GitHub user profile")

        github_user = user_response.json()

    result = await db.execute(
        select(User).where(User.github_id == github_user["id"])
    )
    user = result.scalar_one_or_none()

    if user:
        user.access_token_encrypted = encrypt(access_token)
        user.avatar_url = github_user.get("avatar_url", "")
        user.username = github_user.get("login", "")
    else:
        user = User(
            github_id=github_user["id"],
            username=github_user.get("login", ""),
            avatar_url=github_user.get("avatar_url", ""),
            access_token_encrypted=encrypt(access_token),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    jwt_token = create_jwt_token(user.id)

    return {
        "token": jwt_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "avatar_url": user.avatar_url,
        },
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "preferred_model": user.preferred_model,
    }
