"""
ClipForge AI — Transcript Service

Handles fetching transcripts from YouTube using the youtube-transcript-api.
Includes URL validation, video ID extraction, caching, and error handling.
"""

import json
import re
import logging
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)


class TranscriptError(Exception):
    """Raised when transcript fetching fails."""
    pass


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


def fetch_transcript(video_id: str, languages: list[str] = None) -> list[dict]:
    """Fetch the transcript for a YouTube video.

    Prefers manually-uploaded captions over auto-generated ones.

    Args:
        video_id: The YouTube video ID.
        languages: Preferred languages (default: English).

    Returns:
        A list of transcript segment dicts with keys: text, start, duration.

    Raises:
        TranscriptError: If transcript cannot be fetched.
    """
    if languages is None:
        languages = ["en"]

    try:
        # Try to get manually created transcript first
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

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
    except TranscriptError:
        raise
    except Exception as e:
        raise TranscriptError(f"Failed to fetch transcript for video {video_id}: {str(e)}")


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
