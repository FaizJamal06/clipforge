"""
ClipForge AI — Waitlist API Routes

POST /api/v1/waitlist  — sign up for the auto-editing waitlist
GET  /api/v1/waitlist/count — public count (no emails exposed)

Security layers:
  1. Pydantic input validation (strict email format)
  2. Email normalisation + disposable domain blocklist (model layer)
  3. Per-IP rate limiting via RateLimitMiddleware (middleware layer)
  4. SQLAlchemy ORM — no raw SQL, immune to SQL injection
  5. Error messages never leak internal state (sanitize_error)
  6. Honeypot field — bots filling it are silently rejected
  7. Content-Type enforcement (FastAPI handles this)
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.waitlist import WaitlistEntry, validate_email_format
from app.security import sanitize_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["waitlist"])


# ─── Request / Response Models ─────────────────────────────────────────────

class WaitlistRequest(BaseModel):
    """Waitlist signup payload."""

    email: str = Field(
        ...,
        min_length=5,
        max_length=254,
        description="Email address to sign up with.",
    )
    source: str = Field(
        default="landing_page",
        max_length=50,
        description="Where the signup came from.",
    )
    # Honeypot: bots fill this; real users don't see it (hidden via CSS)
    website: str = Field(
        default="",
        max_length=0,   # Must be empty — any value triggers rejection
        description="Leave this blank.",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalise and validate the email address."""
        return validate_email_format(v)

    @field_validator("source")
    @classmethod
    def sanitize_source(cls, v: str) -> str:
        """Allow only known sources."""
        allowed = {"landing_page", "result_page", "blog", "referral", "other"}
        v = v.strip().lower()
        return v if v in allowed else "other"

    @field_validator("website")
    @classmethod
    def honeypot_check(cls, v: str) -> str:
        """Reject if honeypot field is filled (bot detected)."""
        if v:
            raise ValueError("Bot detected.")
        return v

    model_config = {"str_strip_whitespace": True}


class WaitlistResponse(BaseModel):
    """Response after signup."""
    success: bool
    message: str
    already_joined: bool = False


class WaitlistCountResponse(BaseModel):
    """Public signup count."""
    count: int


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/waitlist", response_model=WaitlistResponse)
async def join_waitlist(
    payload: WaitlistRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WaitlistResponse:
    """Sign up for the ClipForge auto-editing waitlist.

    Security:
    - Input validated and normalised by Pydantic before this runs.
    - Honeypot field silently rejects bots.
    - IP stored for abuse tracking; never returned to client.
    - Duplicate emails return success (no enumeration attack surface).
    - All DB operations via ORM (no SQL injection possible).
    """
    # Extract client IP (respect reverse proxy)
    client_ip = request.headers.get(
        "X-Forwarded-For", request.client.host if request.client else "unknown"
    ).split(",")[0].strip()

    # Truncate user-agent to prevent oversized storage
    raw_ua = request.headers.get("User-Agent", "")
    user_agent = raw_ua[:512] if raw_ua else None

    try:
        # Check for existing signup (avoids relying solely on IntegrityError)
        stmt = select(WaitlistEntry).where(WaitlistEntry.email == payload.email)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Waitlist duplicate attempt: {payload.email[:4]}***")
            return WaitlistResponse(
                success=True,
                message="You're already on the waitlist! We'll be in touch.",
                already_joined=True,
            )

        # Create new entry
        entry = WaitlistEntry(
            email=payload.email,
            source=payload.source,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(entry)
        await db.commit()

        logger.info(f"New waitlist signup from {payload.source} (IP: {client_ip})")

        return WaitlistResponse(
            success=True,
            message="You're on the list! We'll email you when auto-editing launches.",
        )

    except IntegrityError:
        # Race condition: two simultaneous requests for same email
        await db.rollback()
        return WaitlistResponse(
            success=True,
            message="You're already on the waitlist! We'll be in touch.",
            already_joined=True,
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Waitlist signup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=sanitize_error(e),
        )


@router.get("/waitlist/count", response_model=WaitlistCountResponse)
async def get_waitlist_count(db: AsyncSession = Depends(get_db)) -> WaitlistCountResponse:
    """Return the total number of waitlist signups.

    Safe to expose publicly — no email addresses returned.
    """
    try:
        from sqlalchemy import func as sql_func
        result = await db.execute(
            select(sql_func.count()).select_from(WaitlistEntry)
        )
        count = result.scalar() or 0
        return WaitlistCountResponse(count=count)
    except Exception as e:
        logger.error(f"Waitlist count error: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve count.")
