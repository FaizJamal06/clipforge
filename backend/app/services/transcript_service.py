"""
ClipForge AI — Transcript Service

Handles fetching transcripts from YouTube using the youtube-transcript-api.
Includes URL validation, video ID extraction, proxy support for bypassing
IP bans/rate limits, exponential backoff retries, and caching.
"""

import json
import re
import time
import logging
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    RequestBlocked,
)
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

from app.config import get_settings

logger = logging.getLogger(__name__)


class TranscriptError(Exception):
    """Raised when transcript fetching fails."""
    pass


# ---------------------------------------------------------------------------
# YouTube Transcript API client (singleton with proxy support)
# ---------------------------------------------------------------------------

_ytt_api_instance: Optional[YouTubeTranscriptApi] = None


def _build_ytt_api() -> YouTubeTranscriptApi:
    """Build a YouTubeTranscriptApi instance with proxy config from settings.

    Supports three modes:
        - "webshare"  → WebshareProxyConfig (rotating residential proxies)
        - "generic"   → GenericProxyConfig (any HTTP/HTTPS/SOCKS proxy URL)
        - ""          → No proxy (direct connection)
    """
    global _ytt_api_instance
    if _ytt_api_instance is not None:
        return _ytt_api_instance

    settings = get_settings()
    provider = settings.yt_proxy_provider.lower().strip()

    proxy_config = None

    if provider == "webshare":
        if not settings.yt_proxy_username or not settings.yt_proxy_password:
            logger.warning(
                "yt_proxy_provider is 'webshare' but username/password not set. "
                "Falling back to direct connection."
            )
        else:
            proxy_config = WebshareProxyConfig(
                proxy_username=settings.yt_proxy_username,
                proxy_password=settings.yt_proxy_password,
            )
            logger.info("YouTube transcript API configured with Webshare rotating proxy")

    elif provider == "generic":
        if not settings.yt_proxy_url:
            logger.warning(
                "yt_proxy_provider is 'generic' but yt_proxy_url not set. "
                "Falling back to direct connection."
            )
        else:
            proxy_config = GenericProxyConfig(
                http_url=settings.yt_proxy_url,
                https_url=settings.yt_proxy_url,
            )
            logger.info(f"YouTube transcript API configured with generic proxy")

    elif provider:
        logger.warning(f"Unknown yt_proxy_provider '{provider}'. Using direct connection.")

    kwargs = {}
    if proxy_config:
        kwargs["proxy_config"] = proxy_config

    _ytt_api_instance = YouTubeTranscriptApi(**kwargs)
    return _ytt_api_instance


def reset_ytt_api():
    """Reset the cached API instance (useful for testing or config changes)."""
    global _ytt_api_instance
    _ytt_api_instance = None


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def extract_video_id(youtube_url: str) -> Optional[str]:
    """Extract the video ID from a YouTube URL.

    Supports formats:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/watch?v=VIDEO_ID&t=123
        - https://youtube.com/shorts/VIDEO_ID

    Args:
        youtube_url: The YouTube URL to parse.

    Returns:
        The video ID string, or None if the URL is invalid.
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)

    return None


def validate_youtube_url(youtube_url: str) -> str:
    """Validate a YouTube URL and return the video ID.

    Args:
        youtube_url: The URL to validate.

    Returns:
        The extracted video ID.

    Raises:
        TranscriptError: If the URL is invalid.
    """
    if not youtube_url or not youtube_url.strip():
        raise TranscriptError("YouTube URL is empty.")

    video_id = extract_video_id(youtube_url.strip())
    if not video_id:
        raise TranscriptError(
            f"Invalid YouTube URL: '{youtube_url}'. "
            "Supported formats: youtube.com/watch?v=..., youtu.be/..., youtube.com/embed/..."
        )

    return video_id


# ---------------------------------------------------------------------------
# Core transcript fetching (with retry on rate-limit / IP ban)
# ---------------------------------------------------------------------------

def fetch_transcript(video_id: str, languages: list[str] = None) -> list[dict]:
    """Fetch the transcript for a YouTube video with automatic retry.

    Uses exponential backoff on RequestBlocked / IP ban errors.
    Prefers manually-uploaded captions over auto-generated ones.

    Args:
        video_id: The YouTube video ID.
        languages: Preferred languages (default: English).

    Returns:
        A list of transcript segment dicts with keys: text, start, duration.

    Raises:
        TranscriptError: If transcript cannot be fetched after all retries.
    """
    if languages is None:
        languages = ["en"]

    settings = get_settings()
    max_retries = settings.yt_max_retries
    base_delay = settings.yt_retry_base_delay

    last_exception: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            return _fetch_transcript_once(video_id, languages)
        except (RequestBlocked,) as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))  # exponential backoff
                logger.warning(
                    f"YouTube blocked request for {video_id} (attempt {attempt}/{max_retries}). "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"YouTube blocked all {max_retries} attempts for {video_id}. "
                    "Consider configuring a proxy (YT_PROXY_PROVIDER)."
                )

    raise TranscriptError(
        f"YouTube blocked transcript requests for video {video_id} after {max_retries} attempts. "
        "Your IP is likely rate-limited. Configure a proxy via YT_PROXY_PROVIDER env var "
        "(see docs for Webshare or generic proxy setup)."
    )


def _fetch_transcript_once(video_id: str, languages: list[str]) -> list[dict]:
    """Single attempt to fetch a transcript (no retry)."""
    try:
        ytt_api = _build_ytt_api()
        transcript_list = ytt_api.list(video_id)

        try:
            # Prefer manually created transcripts
            transcript = transcript_list.find_manually_created_transcript(languages)
            logger.info(f"Found manually created transcript for video {video_id}")
        except NoTranscriptFound:
            # Fall back to auto-generated
            transcript = transcript_list.find_generated_transcript(languages)
            logger.info(f"Using auto-generated transcript for video {video_id}")

        segments = transcript.fetch()

        # Normalize to list of dicts
        result = [
            {
                "text": str(segment.get("text", segment.text if hasattr(segment, "text") else "")),
                "start": float(segment.get("start", segment.start if hasattr(segment, "start") else 0)),
                "duration": float(segment.get("duration", segment.duration if hasattr(segment, "duration") else 0)),
            }
            if isinstance(segment, dict)
            else {
                "text": str(segment.text),
                "start": float(segment.start),
                "duration": float(segment.duration),
            }
            for segment in segments
        ]

        if not result:
            raise TranscriptError(f"Transcript is empty for video {video_id}.")

        logger.info(f"Fetched {len(result)} transcript segments for video {video_id}")
        return result

    except TranscriptsDisabled:
        raise TranscriptError(
            f"Transcripts are disabled for video {video_id}. "
            "The video owner has turned off captions."
        )
    except NoTranscriptFound:
        raise TranscriptError(
            f"No English transcript found for video {video_id}. "
            "The video may not have captions in English."
        )
    except VideoUnavailable:
        raise TranscriptError(
            f"Video {video_id} is unavailable. "
            "It may be private, deleted, or region-locked."
        )
    except RequestBlocked:
        # Let this bubble up so the retry wrapper can catch it
        raise
    except TranscriptError:
        raise
    except Exception as e:
        raise TranscriptError(f"Failed to fetch transcript for video {video_id}: {str(e)}")


# ---------------------------------------------------------------------------
# Cached variant (Redis)
# ---------------------------------------------------------------------------

async def fetch_transcript_cached(
    video_id: str,
    redis_client=None,
    cache_ttl: int = 86400,
) -> list[dict]:
    """Fetch transcript with optional Redis caching.

    Checks Redis cache first. If miss, fetches from YouTube and stores.
    Gracefully falls back to direct fetch if Redis is unavailable.

    Args:
        video_id: The YouTube video ID.
        redis_client: Optional Redis client for caching.
        cache_ttl: Cache time-to-live in seconds (default: 24 hours).

    Returns:
        Transcript segment list.
    """
    cache_key = f"transcript:{video_id}"

    # Try cache first
    if redis_client is not None:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache HIT for transcript:{video_id}")
                return json.loads(cached)
            logger.info(f"Cache MISS for transcript:{video_id}")
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}. Fetching directly.")

    # Fetch from YouTube (sync call — youtube-transcript-api is synchronous)
    transcript = fetch_transcript(video_id)

    # Store in cache
    if redis_client is not None:
        try:
            await redis_client.set(cache_key, json.dumps(transcript), ex=cache_ttl)
            logger.info(f"Cached transcript for video {video_id} (TTL: {cache_ttl}s)")
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}. Continuing without cache.")

    return transcript
