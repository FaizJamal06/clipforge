"""
ClipForge AI — User Authentication

Verifies the HS256 JWT minted by the frontend's Auth.js `session` callback
after a Google sign-in (see frontend/src/auth.ts). This backend has no
OAuth flow of its own — it only ever trusts a token signed with the shared
`AUTH_SECRET`, and upserts a local User row from its claims.
"""

import logging
from datetime import datetime, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import get_settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthError(HTTPException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_bearer_token(authorization: str | None) -> dict:
    """Extracts and verifies the JWT from an `Authorization: Bearer <token>` header."""
    settings = get_settings()
    if not settings.auth_secret:
        logger.error("AUTH_SECRET is not configured — cannot verify user tokens.")
        raise AuthError("Server auth is not configured")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        return jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise AuthError(f"Invalid or expired token: {e}")


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: verifies the caller's token and returns their User row,
    creating it on first sign-in and refreshing profile fields on subsequent calls.
    """
    claims = decode_bearer_token(authorization)

    user_id = claims.get("sub")
    email = claims.get("email")
    if not user_id or not email:
        raise AuthError("Token missing required claims")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=user_id,
            email=email,
            name=claims.get("name"),
            picture=claims.get("picture"),
        )
        db.add(user)
    else:
        user.email = email
        user.name = claims.get("name") or user.name
        user.picture = claims.get("picture") or user.picture

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


def is_pro(user: User) -> bool:
    return user.plan == "pro" or user.email in get_settings().pro_emails


async def require_pro(user: User = Depends(get_current_user)) -> User:
    """Dependency for the paid product: signed in AND on the Pro plan."""
    if not is_pro(user):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Upgrade to Pro to analyze your own videos. Try the demo for free.",
        )
    return user
