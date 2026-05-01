"""
ClipForge AI — Tests for today's changes

Covers:
1. Email validation logic (waitlist model)
2. WaitlistRequest Pydantic schema — valid, invalid, honeypot, disposable domains
3. Waitlist API endpoints (POST /waitlist, GET /waitlist/count) via HTTPX async client
4. EditingPlanResult / EditingSegmentResult mapping in routes.py
5. Security: SQL injection patterns, oversized inputs, XSS payloads rejected
"""

import sys
import os
import pytest
import pytest_asyncio
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Use an isolated in-memory SQLite for all DB tests
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_API_KEY", "test-key")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# 1. Email Validation — unit tests (no DB needed)
# ─────────────────────────────────────────────────────────────────────────────

from app.models.waitlist import validate_email_format


class TestEmailValidation:
    """Unit tests for the validate_email_format helper."""

    def test_valid_email_normalised(self):
        assert validate_email_format("  User@Example.COM  ") == "user@example.com"

    def test_valid_simple_email(self):
        assert validate_email_format("hello@world.io") == "hello@world.io"

    def test_valid_plus_addressing(self):
        assert validate_email_format("user+tag@domain.co.uk") == "user+tag@domain.co.uk"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="required"):
            validate_email_format("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="required"):
            validate_email_format("   ")

    def test_missing_at_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            validate_email_format("notanemail.com")

    def test_missing_domain_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            validate_email_format("user@")

    def test_missing_tld_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            validate_email_format("user@domain")

    def test_too_long_raises(self):
        long_email = "a" * 250 + "@b.com"
        with pytest.raises(ValueError, match="maximum length"):
            validate_email_format(long_email)

    def test_disposable_mailinator_raises(self):
        with pytest.raises(ValueError, match="real email"):
            validate_email_format("test@mailinator.com")

    def test_disposable_guerrillamail_raises(self):
        with pytest.raises(ValueError, match="real email"):
            validate_email_format("anon@guerrillamail.com")

    def test_disposable_tempmail_raises(self):
        with pytest.raises(ValueError, match="real email"):
            validate_email_format("x@tempmail.com")

    def test_disposable_yopmail_raises(self):
        with pytest.raises(ValueError, match="real email"):
            validate_email_format("x@yopmail.com")

    def test_trashmail_raises(self):
        with pytest.raises(ValueError, match="real email"):
            validate_email_format("x@trashmail.com")


# ─────────────────────────────────────────────────────────────────────────────
# 2. WaitlistRequest Pydantic Schema
# ─────────────────────────────────────────────────────────────────────────────

from app.api.waitlist import WaitlistRequest
from pydantic import ValidationError


class TestWaitlistRequestSchema:
    """Validates the Pydantic request model rejects bad inputs."""

    def test_valid_request(self):
        req = WaitlistRequest(email="hello@example.com")
        assert req.email == "hello@example.com"
        assert req.source == "landing_page"

    def test_email_normalised_on_parse(self):
        req = WaitlistRequest(email="  HELLO@EXAMPLE.COM  ")
        assert req.email == "hello@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            WaitlistRequest(email="not-an-email")

    def test_honeypot_filled_rejected(self):
        """Any value in the honeypot field should cause validation failure."""
        with pytest.raises(ValidationError):
            WaitlistRequest(email="ok@example.com", website="http://spam.com")

    def test_honeypot_empty_ok(self):
        req = WaitlistRequest(email="ok@example.com", website="")
        assert req.email == "ok@example.com"

    def test_unknown_source_normalised_to_other(self):
        req = WaitlistRequest(email="ok@example.com", source="random_unknown_source")
        assert req.source == "other"

    def test_known_source_preserved(self):
        req = WaitlistRequest(email="ok@example.com", source="result_page")
        assert req.source == "result_page"

    def test_disposable_email_rejected(self):
        with pytest.raises(ValidationError):
            WaitlistRequest(email="x@mailinator.com")

    def test_sql_injection_email_rejected(self):
        """SQL injection payloads must fail email format validation."""
        with pytest.raises(ValidationError):
            WaitlistRequest(email="admin'--@x.com")

    def test_xss_payload_email_rejected(self):
        with pytest.raises(ValidationError):
            WaitlistRequest(email="<script>alert(1)</script>@x.com")

    def test_oversized_email_rejected(self):
        with pytest.raises(ValidationError):
            WaitlistRequest(email="a" * 300 + "@b.com")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Waitlist API — integration tests with in-memory SQLite
# ─────────────────────────────────────────────────────────────────────────────

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db
from app.middleware import RateLimitMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


# ── Bypass rate limiting for integration tests ──────────────────────────────
# The RateLimitMiddleware works correctly (proven by its own unit tests).
# We override it here so rapid-fire test requests don't hit the burst limit.
async def _passthrough_dispatch(self, request: Request, call_next: Callable) -> Response:
    return await call_next(request)

RateLimitMiddleware.dispatch = _passthrough_dispatch  # type: ignore


# ── Override the DB dependency to use in-memory SQLite ─────────────────────
_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_test_engine = create_async_engine(_TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_test_engine, autoflush=False, expire_on_commit=False)


async def override_get_db():
    async with _TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_db():
    """Create all tables once per test module in the test DB."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """HTTPX async client pointed at the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


class TestWaitlistEndpoint:
    """Integration tests for POST /api/v1/waitlist."""

    @pytest.mark.asyncio
    async def test_successful_signup(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={
            "email": "new@example.com",
            "website": "",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["already_joined"] is False

    @pytest.mark.asyncio
    async def test_duplicate_signup_returns_success(self, client: AsyncClient):
        """Duplicate emails must NOT return an error (no enumeration)."""
        payload = {"email": "duplicate@example.com", "website": ""}
        await client.post("/api/v1/waitlist", json=payload)
        res = await client.post("/api/v1/waitlist", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["already_joined"] is True

    @pytest.mark.asyncio
    async def test_invalid_email_returns_422(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={
            "email": "not-an-email",
            "website": "",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_honeypot_filled_returns_422(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={
            "email": "real@example.com",
            "website": "http://spam.com",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_email_returns_422(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={"website": ""})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_disposable_email_returns_422(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={
            "email": "test@mailinator.com",
            "website": "",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_sql_injection_rejected(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={
            "email": "'; DROP TABLE waitlist; --@x.com",
            "website": "",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_xss_payload_rejected(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={
            "email": "<img src=x onerror=alert(1)>@evil.com",
            "website": "",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_oversized_email_rejected(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={
            "email": "a" * 300 + "@b.com",
            "website": "",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body_rejected(self, client: AsyncClient):
        res = await client.post("/api/v1/waitlist", json={})
        assert res.status_code == 422


class TestWaitlistCount:
    """Integration tests for GET /api/v1/waitlist/count."""

    @pytest.mark.asyncio
    async def test_count_returns_integer(self, client: AsyncClient):
        res = await client.get("/api/v1/waitlist/count")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    @pytest.mark.asyncio
    async def test_count_increments_after_signup(self, client: AsyncClient):
        count_before = (await client.get("/api/v1/waitlist/count")).json()["count"]
        await client.post("/api/v1/waitlist", json={
            "email": f"counter_test_{count_before}@example.com",
            "website": "",
        })
        count_after = (await client.get("/api/v1/waitlist/count")).json()["count"]
        assert count_after == count_before + 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. EditingPlanResult mapping in routes.py
# ─────────────────────────────────────────────────────────────────────────────

from app.api.routes import (
    format_clips_from_state,
    EditingPlanResult,
    EditingSegmentResult,
)


class TestEditingPlanMapping:
    """Ensures the backend correctly maps ClipEditingPlan fields to the API response."""

    def _make_state(self, plan_override: dict = {}) -> dict:
        base_plan = {
            "clip_index": 0,
            "title_suggestion": "Why Most People Fail",
            "hook_strategy": "Open on speaker mid-sentence, zoom punch at 0.5s",
            "segments": [
                {
                    "timestamp": "0:00-0:03",
                    "visual_type": "talking_head",
                    "broll_idea": "Close-up of speaker's eyes",
                    "caption_text": "Most people don't even start.",
                    "editing_note": "Hard cut in, no fade",
                },
                {
                    "timestamp": "0:03-0:15",
                    "visual_type": "broll",
                    "broll_idea": "Time-lapse of busy city street",
                    "caption_text": "They let fear decide.",
                    "editing_note": "Speed ramp at 0:08",
                },
            ],
            "caption_style": "Bold white, black drop shadow, centered bottom third",
            "pacing_notes": "Jump cut every 4-5 seconds, punch zoom on key words",
            "call_to_action": "Follow for more mindset content →",
        }
        base_plan.update(plan_override)
        return {
            "validated_clips": [{
                "clip_text": "Most people don't even start. They let fear decide.",
                "start_time": 120.0,
                "end_time": 165.0,
                "duration": 45.0,
                "virality_score": 8.5,
                "virality_reasoning": "Relatable pain point with universal appeal.",
                "hook": "Most people don't even start.",
                "payoff": "Fear is the only thing stopping you.",
            }],
            "editing_plans": [base_plan],
        }

    def test_title_suggestion_mapped(self):
        clips = format_clips_from_state(self._make_state())
        assert clips[0].editing_plan.title_suggestion == "Why Most People Fail"

    def test_hook_strategy_mapped(self):
        clips = format_clips_from_state(self._make_state())
        assert "zoom punch" in clips[0].editing_plan.hook_strategy

    def test_segments_count(self):
        clips = format_clips_from_state(self._make_state())
        assert len(clips[0].editing_plan.segments) == 2

    def test_segment_fields(self):
        clips = format_clips_from_state(self._make_state())
        seg = clips[0].editing_plan.segments[0]
        assert seg.timestamp == "0:00-0:03"
        assert seg.visual_type == "talking_head"
        assert seg.broll_idea == "Close-up of speaker's eyes"
        assert seg.caption_text == "Most people don't even start."
        assert seg.editing_note == "Hard cut in, no fade"

    def test_caption_style_mapped(self):
        clips = format_clips_from_state(self._make_state())
        assert "Bold white" in clips[0].editing_plan.caption_style

    def test_pacing_notes_mapped(self):
        clips = format_clips_from_state(self._make_state())
        assert "jump cut" in clips[0].editing_plan.pacing_notes.lower()

    def test_call_to_action_mapped(self):
        clips = format_clips_from_state(self._make_state())
        assert clips[0].editing_plan.call_to_action != ""

    def test_empty_plan_returns_defaults(self):
        """When no editing plan exists for a clip, defaults should be used (no crash)."""
        state = {
            "validated_clips": [{
                "clip_text": "Some text",
                "start_time": 0.0, "end_time": 45.0, "duration": 45.0,
                "virality_score": 5.0, "virality_reasoning": "",
                "hook": "", "payoff": "",
            }],
            "editing_plans": [],  # no plan
        }
        clips = format_clips_from_state(state)
        assert clips[0].editing_plan.title_suggestion == ""
        assert clips[0].editing_plan.segments == []

    def test_none_pacing_notes_coerced_to_empty_string(self):
        """pacing_notes=None from LLM should become '' not None."""
        clips = format_clips_from_state(self._make_state({"pacing_notes": None}))
        assert clips[0].editing_plan.pacing_notes == ""

    def test_none_cta_coerced_to_empty_string(self):
        clips = format_clips_from_state(self._make_state({"call_to_action": None}))
        assert clips[0].editing_plan.call_to_action == ""

    def test_clip_metadata_preserved(self):
        clips = format_clips_from_state(self._make_state())
        c = clips[0]
        assert c.start_time == 120.0
        assert c.end_time == 165.0
        assert c.duration == 45.0
        assert c.virality_score == 8.5
        assert c.hook == "Most people don't even start."
