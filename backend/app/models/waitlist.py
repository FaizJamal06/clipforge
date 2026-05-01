"""
ClipForge AI — Waitlist Database Model

Stores email signups for the auto-editing / automated-planning waitlist.
- Emails are normalised (lowercased, stripped) before storage.
- Duplicate emails are handled gracefully (unique constraint).
- IP address stored for abuse monitoring, not exposed via API.
"""

import re
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


# Basic email regex (RFC 5321 simplified)
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

MAX_EMAIL_LENGTH = 254  # RFC 5321


def validate_email_format(email: str) -> str:
    """Normalise and validate an email address.

    Returns the cleaned email or raises ValueError.
    """
    if not email or not email.strip():
        raise ValueError("Email address is required.")

    email = email.strip().lower()

    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError(f"Email exceeds maximum length of {MAX_EMAIL_LENGTH} characters.")

    if not _EMAIL_RE.match(email):
        raise ValueError("Invalid email address format.")

    # Block obviously disposable / test domains
    disposable_domains = {
        "mailinator.com", "guerrillamail.com", "tempmail.com",
        "throwaway.email", "yopmail.com", "sharklasers.com",
        "guerrillamailblock.com", "grr.la", "guerrillamail.info",
        "spam4.me", "trashmail.com", "dispostable.com",
    }
    domain = email.split("@")[1]
    if domain in disposable_domains:
        raise ValueError("Please use a real email address.")

    return email


class WaitlistEntry(Base):
    """Waitlist signup record."""

    __tablename__ = "waitlist"

    email = Column(String(254), primary_key=True, index=True)
    source = Column(String(50), nullable=False, default="landing_page")
    ip_address = Column(String(45), nullable=True)   # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    is_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
