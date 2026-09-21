"""
ClipForge AI — Auth & per-user data isolation tests

Covers:
1. decode_bearer_token — rejects missing/malformed/invalid/expired tokens
2. get_current_user — creates a user on first sign-in, reuses it on repeat calls
3. Per-user cache isolation — two users can cache the same video_id without
   colliding, and a user-scoped query never returns another user's row
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("AUTH_SECRET", "test-secret-for-auth-tests-padded-to-32-bytes-min")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

from app.database import Base
from app.config import get_settings
from app.auth import decode_bearer_token, get_current_user, AuthError
from app.models.user import User
from app.models.video import ProcessedVideo

SECRET = get_settings().auth_secret


def make_token(sub="user-123", email="user@example.com", expires_delta=timedelta(hours=1), **extra):
    payload = {
        "sub": sub,
        "email": email,
        "exp": datetime.now(timezone.utc) + expires_delta,
        **extra,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_test_engine = create_async_engine(_TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_test_engine, autoflush=False, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _TestSession() as session:
        yield session
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestDecodeBearerToken:
    def test_missing_header_raises_401(self):
        with pytest.raises(AuthError):
            decode_bearer_token(None)

    def test_non_bearer_header_raises_401(self):
        with pytest.raises(AuthError):
            decode_bearer_token("Basic somecreds")

    def test_garbage_token_raises_401(self):
        with pytest.raises(AuthError):
            decode_bearer_token("Bearer not-a-real-jwt")

    def test_expired_token_raises_401(self):
        expired = make_token(expires_delta=timedelta(hours=-1))
        with pytest.raises(AuthError):
            decode_bearer_token(f"Bearer {expired}")

    def test_wrong_signature_raises_401(self):
        token = jwt.encode(
            {"sub": "user-123", "email": "a@b.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "a-different-secret",
            algorithm="HS256",
        )
        with pytest.raises(AuthError):
            decode_bearer_token(f"Bearer {token}")

    def test_valid_token_decodes(self):
        token = make_token(sub="user-abc", email="abc@example.com")
        claims = decode_bearer_token(f"Bearer {token}")
        assert claims["sub"] == "user-abc"
        assert claims["email"] == "abc@example.com"


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_creates_user_on_first_sign_in(self, db_session):
        token = make_token(sub="google-sub-1", email="new@example.com", name="New User")
        user = await get_current_user(authorization=f"Bearer {token}", db=db_session)

        assert user.id == "google-sub-1"
        assert user.email == "new@example.com"
        assert user.name == "New User"

        result = await db_session.execute(select(User).where(User.id == "google-sub-1"))
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_reuses_existing_user_and_updates_profile(self, db_session):
        token1 = make_token(sub="google-sub-2", email="old@example.com", name="Old Name")
        await get_current_user(authorization=f"Bearer {token1}", db=db_session)

        token2 = make_token(sub="google-sub-2", email="old@example.com", name="Updated Name")
        user = await get_current_user(authorization=f"Bearer {token2}", db=db_session)

        assert user.name == "Updated Name"
        result = await db_session.execute(select(User))
        assert len(result.scalars().all()) == 1  # no duplicate row created

    @pytest.mark.asyncio
    async def test_token_missing_claims_rejected(self, db_session):
        token = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(hours=1)},  # no sub/email
            SECRET,
            algorithm="HS256",
        )
        with pytest.raises(AuthError):
            await get_current_user(authorization=f"Bearer {token}", db=db_session)


class TestPerUserCacheIsolation:
    @pytest.mark.asyncio
    async def test_two_users_can_cache_the_same_video_id(self, db_session):
        row_a = ProcessedVideo(video_id="abc123_0", user_id="user-a", youtube_url="https://youtu.be/abc123")
        row_a.set_payload({"status": "completed", "clips": []})
        row_b = ProcessedVideo(video_id="abc123_0", user_id="user-b", youtube_url="https://youtu.be/abc123")
        row_b.set_payload({"status": "completed", "clips": []})

        db_session.add_all([row_a, row_b])
        await db_session.commit()  # would raise IntegrityError if uniqueness were video_id-only

        result = await db_session.execute(
            select(ProcessedVideo).where(ProcessedVideo.user_id == "user-a")
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].user_id == "user-a"

    @pytest.mark.asyncio
    async def test_user_scoped_query_excludes_other_users_rows(self, db_session):
        for uid in ("user-x", "user-y"):
            row = ProcessedVideo(video_id="shared_video_0", user_id=uid, youtube_url="https://youtu.be/shared")
            row.set_payload({"status": "completed", "clips": []})
            db_session.add(row)
        await db_session.commit()

        result = await db_session.execute(
            select(ProcessedVideo).where(
                ProcessedVideo.video_id == "shared_video_0",
                ProcessedVideo.user_id == "user-x",
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].user_id == "user-x"


class TestPaywall:
    """Free users are blocked from the paid endpoints; the demo stays public."""

    @staticmethod
    @asynccontextmanager
    async def _client():
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.database import get_db

        async def override_get_db():
            async with _TestSession() as session:
                yield session

        previous = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c
        finally:  # don't clobber the override other test modules rely on
            if previous is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = previous

    @pytest.mark.asyncio
    async def test_free_user_gets_402_on_process(self, db_session):
        token = make_token(sub="free-user", email="free@example.com")
        async with self._client() as c:
            res = await c.post(
                "/api/v1/process",
                json={"youtube_url": "https://youtu.be/dQw4w9WgXcQ"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert res.status_code == 402

    @pytest.mark.asyncio
    async def test_demo_is_public_and_has_clips(self, db_session):
        async with self._client() as c:
            res = await c.get("/api/v1/demo")
        assert res.status_code == 200
        assert len(res.json()["clips"]) > 0

    @pytest.mark.asyncio
    async def test_me_reports_free_plan(self, db_session):
        token = make_token(sub="free-user-2", email="free2@example.com")
        async with self._client() as c:
            res = await c.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert res.json()["plan"] == "free"

    @pytest.mark.asyncio
    async def test_is_pro_by_plan_flag(self, db_session):
        from app.auth import is_pro
        assert is_pro(User(id="x", email="x@example.com", plan="pro"))
        assert not is_pro(User(id="y", email="y@example.com", plan="free"))
