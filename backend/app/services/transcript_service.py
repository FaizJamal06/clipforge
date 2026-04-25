"""
ClipForge AI — Transcript Service

Handles fetching transcripts from YouTube using the official YouTube Data
API v3 (captions.list → captions.download). Falls back to the
youtube-transcript-api library if the official API fails.

Requires a YOUTUBE_API_KEY with the YouTube Data API v3 enabled.
"""

import json
import re
import time
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class TranscriptError(Exception):
    """Raised when transcript fetching fails."""
    pass


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
# YouTube Data API v3 — Captions
# ---------------------------------------------------------------------------

YOUTUBE_CAPTIONS_LIST_URL = "https://www.googleapis.com/youtube/v3/captions"
YOUTUBE_CAPTIONS_DOWNLOAD_URL = "https://www.googleapis.com/youtube/v3/captions/{caption_id}"


def _parse_timedtext_xml(xml_text: str) -> list[dict]:
    """Parse YouTube's timedtext XML format into transcript segments.

    YouTube captions downloaded as SRT or timedtext come as XML like:
        <transcript>
            <text start="0.0" dur="4.5">Hello world</text>
            ...
        </transcript>
    """
    segments = []
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter("text"):
            start = float(elem.attrib.get("start", 0))
            duration = float(elem.attrib.get("dur", 0))
            text = (elem.text or "").strip()
            if text:
                # Clean HTML entities
                text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                text = text.replace("&#39;", "'").replace("&quot;", '"')
                segments.append({
                    "text": text,
                    "start": start,
                    "duration": duration,
                })
    except ET.ParseError as e:
        raise TranscriptError(f"Failed to parse caption XML: {e}")

    return segments


def _parse_srt(srt_text: str) -> list[dict]:
    """Parse SRT subtitle format into transcript segments."""
    segments = []
    blocks = re.split(r'\n\n+', srt_text.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # Parse timestamp line: "00:00:01,000 --> 00:00:04,500"
        time_match = re.match(
            r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
            lines[1]
        )
        if not time_match:
            continue

        h1, m1, s1, ms1, h2, m2, s2, ms2 = time_match.groups()
        start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
        end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
        duration = end - start

        text = ' '.join(lines[2:]).strip()
        # Remove HTML tags from SRT
        text = re.sub(r'<[^>]+>', '', text)
        if text:
            segments.append({
                "text": text,
                "start": start,
                "duration": duration,
            })

    return segments


def _fetch_via_youtube_api(video_id: str, languages: list[str] = None) -> list[dict]:
    """Fetch transcript using the official YouTube Data API v3.

    Steps:
        1. Call captions.list to get available caption tracks
        2. Pick the best caption track (prefer manual, then auto-generated)
        3. Download the caption track content

    Args:
        video_id: The YouTube video ID.
        languages: Preferred language codes (default: ["en"]).

    Returns:
        List of transcript segment dicts.

    Raises:
        TranscriptError: If no captions are available or API call fails.
    """
    if languages is None:
        languages = ["en"]

    settings = get_settings()
    api_key = settings.youtube_api_key

    if not api_key:
        raise TranscriptError(
            "YOUTUBE_API_KEY is not configured. "
            "Set it in your .env file with a valid YouTube Data API v3 key."
        )

    # Step 1: List available caption tracks
    with httpx.Client(timeout=30.0) as client:
        list_resp = client.get(
            YOUTUBE_CAPTIONS_LIST_URL,
            params={
                "part": "snippet",
                "videoId": video_id,
                "key": api_key,
            },
        )

        if list_resp.status_code == 403:
            error_data = list_resp.json()
            error_reason = ""
            if "error" in error_data:
                errors = error_data["error"].get("errors", [])
                if errors:
                    error_reason = errors[0].get("reason", "")
            
            if error_reason == "forbidden":
                raise TranscriptError(
                    f"YouTube API access forbidden for video {video_id}. "
                    "The caption track owner has not granted third-party access."
                )
            raise TranscriptError(
                f"YouTube API returned 403 for video {video_id}: {error_reason}. "
                "Check your API key and quota."
            )

        if list_resp.status_code == 404:
            raise TranscriptError(
                f"Video {video_id} not found. It may be private, deleted, or region-locked."
            )

        if list_resp.status_code != 200:
            raise TranscriptError(
                f"YouTube API error (HTTP {list_resp.status_code}) listing captions "
                f"for video {video_id}: {list_resp.text[:200]}"
            )

        data = list_resp.json()
        items = data.get("items", [])

        if not items:
            raise TranscriptError(
                f"No captions available for video {video_id}. "
                "The video may not have subtitles."
            )

        # Step 2: Pick the best caption track
        # Priority: manual caption in preferred language > auto in preferred language > any manual > any auto
        manual_tracks = []
        auto_tracks = []

        for item in items:
            snippet = item.get("snippet", {})
            track_info = {
                "id": item["id"],
                "language": snippet.get("language", ""),
                "name": snippet.get("name", ""),
                "track_kind": snippet.get("trackKind", ""),
                "is_auto": snippet.get("trackKind") == "ASR",
            }
            if track_info["is_auto"]:
                auto_tracks.append(track_info)
            else:
                manual_tracks.append(track_info)

        selected_track = None

        # Try manual tracks in preferred languages first
        for lang in languages:
            for track in manual_tracks:
                if track["language"].startswith(lang):
                    selected_track = track
                    break
            if selected_track:
                break

        # Then auto tracks in preferred languages
        if not selected_track:
            for lang in languages:
                for track in auto_tracks:
                    if track["language"].startswith(lang):
                        selected_track = track
                        break
                if selected_track:
                    break

        # Fall back to any manual track
        if not selected_track and manual_tracks:
            selected_track = manual_tracks[0]

        # Fall back to any auto track
        if not selected_track and auto_tracks:
            selected_track = auto_tracks[0]

        if not selected_track:
            raise TranscriptError(
                f"No suitable caption track found for video {video_id}. "
                f"Available languages: {[t.get('language') for t in manual_tracks + auto_tracks]}"
            )

        caption_type = "manual" if not selected_track["is_auto"] else "auto-generated"
        logger.info(
            f"Selected {caption_type} caption track for {video_id}: "
            f"lang={selected_track['language']}, id={selected_track['id']}"
        )

    # Note: captions.download requires OAuth and the caption owner's permission,
    # so we fall back to the timedtext endpoint which works with API key
    return _fetch_via_timedtext(video_id, selected_track["language"])


def _fetch_via_timedtext(video_id: str, language: str = "en") -> list[dict]:
    """Fetch transcript using YouTube's timedtext endpoint.

    This is the publicly accessible endpoint that YouTube's own player uses
    to load captions. It does not require OAuth.

    Args:
        video_id: The YouTube video ID.
        language: Language code for the captions.

    Returns:
        List of transcript segment dicts.
    """
    # YouTube's public timedtext endpoint
    timedtext_url = "https://www.youtube.com/api/timedtext"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Try fetching manually created captions first
        resp = client.get(
            timedtext_url,
            params={
                "v": video_id,
                "lang": language,
                "fmt": "srv3",  # XML format
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if resp.status_code == 200 and resp.text.strip():
            segments = _parse_timedtext_xml(resp.text)
            if segments:
                logger.info(f"Fetched manual captions for {video_id} ({len(segments)} segments)")
                return segments

        # Try auto-generated captions
        resp = client.get(
            timedtext_url,
            params={
                "v": video_id,
                "lang": language,
                "kind": "asr",
                "fmt": "srv3",
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if resp.status_code == 200 and resp.text.strip():
            segments = _parse_timedtext_xml(resp.text)
            if segments:
                logger.info(f"Fetched auto-generated captions for {video_id} ({len(segments)} segments)")
                return segments

    raise TranscriptError(
        f"Could not fetch captions for video {video_id} via timedtext endpoint. "
        "The video may not have captions enabled."
    )


def _fetch_via_innertube(video_id: str, languages: list[str] = None) -> list[dict]:
    """Fetch transcript using YouTube's InnerTube API (player endpoint).

    This is the same API that YouTube's web player uses internally.
    It's the most reliable method for getting captions.

    Args:
        video_id: The YouTube video ID.
        languages: Preferred language codes.

    Returns:
        List of transcript segment dicts.
    """
    if languages is None:
        languages = ["en"]

    innertube_url = "https://www.youtube.com/youtubei/v1/player"

    payload = {
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
            }
        },
        "videoId": video_id,
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            innertube_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        )

        if resp.status_code != 200:
            raise TranscriptError(
                f"YouTube InnerTube API returned HTTP {resp.status_code} for video {video_id}"
            )

        data = resp.json()

        # Check if video is available
        playability = data.get("playabilityStatus", {})
        if playability.get("status") != "OK":
            reason = playability.get("reason", "Unknown reason")
            raise TranscriptError(f"Video {video_id} is unavailable: {reason}")

        # Get caption tracks
        captions = data.get("captions", {})
        renderer = captions.get("playerCaptionsTracklistRenderer", {})
        caption_tracks = renderer.get("captionTracks", [])

        if not caption_tracks:
            raise TranscriptError(
                f"No captions available for video {video_id}. "
                "The video may not have subtitles enabled."
            )

        # Find the best caption track
        selected_url = None
        selected_kind = None

        # Priority: manual in preferred lang > auto in preferred lang > any
        for lang in languages:
            for track in caption_tracks:
                lang_code = track.get("languageCode", "")
                kind = track.get("kind", "")
                if lang_code.startswith(lang) and kind != "asr":
                    selected_url = track.get("baseUrl")
                    selected_kind = "manual"
                    break
            if selected_url:
                break

        if not selected_url:
            for lang in languages:
                for track in caption_tracks:
                    lang_code = track.get("languageCode", "")
                    if lang_code.startswith(lang):
                        selected_url = track.get("baseUrl")
                        selected_kind = track.get("kind", "manual")
                        break
                if selected_url:
                    break

        if not selected_url and caption_tracks:
            selected_url = caption_tracks[0].get("baseUrl")
            selected_kind = caption_tracks[0].get("kind", "unknown")

        if not selected_url:
            raise TranscriptError(
                f"No downloadable caption track found for video {video_id}."
            )

        # Download the caption content (XML format)
        # Append fmt=srv3 for timedtext XML
        if "fmt=" not in selected_url:
            separator = "&" if "?" in selected_url else "?"
            selected_url += f"{separator}fmt=srv3"

        caption_resp = client.get(
            selected_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        )

        if caption_resp.status_code != 200:
            raise TranscriptError(
                f"Failed to download captions for video {video_id} "
                f"(HTTP {caption_resp.status_code})"
            )

        segments = _parse_timedtext_xml(caption_resp.text)
        if not segments:
            raise TranscriptError(
                f"Caption track for video {video_id} returned empty content."
            )

        kind_label = "auto-generated" if selected_kind == "asr" else "manual"
        logger.info(
            f"Fetched {kind_label} captions via InnerTube for {video_id} "
            f"({len(segments)} segments)"
        )
        return segments


# ---------------------------------------------------------------------------
# Core transcript fetching (with fallback chain)
# ---------------------------------------------------------------------------

def _fetch_via_supadata(video_id: str) -> list[dict]:
    """Strategy 1: Use Supadata API for highly reliable transcript fetching."""
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.supadata_api_key:
        raise TranscriptError("Supadata API key is not configured.")
        
    url = f"https://api.supadata.ai/v1/youtube/transcript?videoId={video_id}"
    headers = {"x-api-key": settings.supadata_api_key}
    
    import requests
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 401 or response.status_code == 403:
        raise TranscriptError("Supadata API key is invalid or unauthorized.")
    if response.status_code == 404:
        raise TranscriptError(f"No transcript found via Supadata for video {video_id}.")
    if response.status_code != 200:
        raise TranscriptError(f"Supadata API returned HTTP {response.status_code}: {response.text}")
        
    data = response.json()
    if not isinstance(data, dict) or "content" not in data:
        raise TranscriptError(f"Unexpected response format from Supadata: {data}")
        
    content = data["content"]
    if not content:
        raise TranscriptError(f"Supadata returned empty transcript for video {video_id}.")
        
    # Map Supadata format (offset in ms, duration in ms) to our format (start in s, duration in s)
    result = []
    for item in content:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        
        # Supadata provides offset/duration in milliseconds
        start_sec = float(item.get("offset", 0)) / 1000.0
        duration_sec = float(item.get("duration", 0)) / 1000.0
        
        result.append({
            "text": text,
            "start": start_sec,
            "duration": duration_sec
        })
        
    logger.info(f"Fetched {len(result)} segments via Supadata API for {video_id}")
    return result


def fetch_transcript(video_id: str, languages: list[str] = None) -> list[dict]:
    """Fetch the transcript for a YouTube video.

    Uses a fallback chain:
        1. Supadata API
        2. youtube-transcript-api library (most reliable — uses signed URLs)
        3. YouTube InnerTube API (YouTube's internal player API)
        4. YouTube Data API v3 (captions.list) → timedtext download

    Args:
        video_id: The YouTube video ID.
        languages: Preferred languages (default: English).

    Returns:
        A list of transcript segment dicts with keys: text, start, duration.

    Raises:
        TranscriptError: If transcript cannot be fetched from any source.
    """
    if languages is None:
        languages = ["en"]

    errors = []

    # Strategy 1: Supadata API (Most reliable, paid)
    try:
        from app.config import get_settings
        settings = get_settings()
        if settings.supadata_api_key:
            logger.info(f"Attempting Supadata API for video {video_id}...")
            segments = _fetch_via_supadata(video_id)
            if segments:
                return segments
    except TranscriptError as e:
        errors.append(f"Supadata: {e}")
        logger.warning(f"Supadata API failed for {video_id}: {e}")
    except Exception as e:
        errors.append(f"Supadata: {e}")
        logger.warning(f"Supadata API unexpected error for {video_id}: {e}")

    # Strategy 2: youtube-transcript-api library (legacy fallback)
    try:
        logger.info(f"Attempting youtube-transcript-api for video {video_id}...")
        segments = _fetch_via_ytt_library(video_id, languages)
        if segments:
            return segments
    except ImportError:
        errors.append("youtube-transcript-api library not installed")
        logger.info("youtube-transcript-api not installed, trying other methods")
    except TranscriptError as e:
        errors.append(f"youtube-transcript-api: {e}")
        logger.warning(f"youtube-transcript-api failed for {video_id}: {e}")
    except Exception as e:
        errors.append(f"youtube-transcript-api: {e}")
        logger.warning(f"youtube-transcript-api unexpected error for {video_id}: {e}")

    # Strategy 2: InnerTube API (YouTube's internal player API)
    try:
        logger.info(f"Attempting InnerTube API for video {video_id}...")
        segments = _fetch_via_innertube(video_id, languages)
        if segments:
            return segments
    except TranscriptError as e:
        errors.append(f"InnerTube: {e}")
        logger.warning(f"InnerTube API failed for {video_id}: {e}")
    except Exception as e:
        errors.append(f"InnerTube: {e}")
        logger.warning(f"InnerTube API unexpected error for {video_id}: {e}")

    # Strategy 3: YouTube Data API v3 (official API with API key)
    settings = get_settings()
    if settings.youtube_api_key:
        try:
            logger.info(f"Attempting YouTube Data API v3 for video {video_id}...")
            segments = _fetch_via_youtube_api(video_id, languages)
            if segments:
                return segments
        except TranscriptError as e:
            errors.append(f"YouTube API v3: {e}")
            logger.warning(f"YouTube Data API v3 failed for {video_id}: {e}")
        except Exception as e:
            errors.append(f"YouTube API v3: {e}")
            logger.warning(f"YouTube Data API v3 unexpected error for {video_id}: {e}")

    # All strategies failed
    error_summary = "; ".join(errors)
    
    # Bubble up IP Ban message if it's the primary cause
    if "temporarily blocked your IP" in error_summary:
        raise TranscriptError(
            f"YouTube has temporarily blocked your IP for making too many requests. "
            f"Please wait a while or use a different connection."
        )

    raise TranscriptError(
        f"Failed to fetch transcript for video {video_id} from all sources. "
        f"Errors: {error_summary}"
    )


def _fetch_via_ytt_library(video_id: str, languages: list[str]) -> list[dict]:
    """Legacy fallback: use the youtube-transcript-api library."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
        )
    except ImportError:
        raise ImportError("youtube-transcript-api is not installed")

    try:
        from app.config import get_settings
        settings = get_settings()
        
        if settings.youtube_proxy:
            from youtube_transcript_api.proxies import GenericProxyConfig
            logger.info(f"Using proxy {settings.youtube_proxy} for youtube-transcript-api")
            proxy_config = GenericProxyConfig(
                http_url=settings.youtube_proxy,
                https_url=settings.youtube_proxy
            )
            ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        else:
            ytt_api = YouTubeTranscriptApi()
            
        transcript_list = ytt_api.list(video_id)

        try:
            transcript = transcript_list.find_manually_created_transcript(languages)
            logger.info(f"Found manually created transcript via library for {video_id}")
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(languages)
            logger.info(f"Using auto-generated transcript via library for {video_id}")

        segments = transcript.fetch()

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

        logger.info(f"Fetched {len(result)} segments via library for {video_id}")
        return result

    except TranscriptsDisabled:
        raise TranscriptError(f"Transcripts are disabled for video {video_id}.")
    except NoTranscriptFound:
        raise TranscriptError(f"No English transcript found for video {video_id}.")
    except VideoUnavailable:
        raise TranscriptError(f"Video {video_id} is unavailable.")
    except Exception as e:
        error_str = str(e)
        if "blocking requests from your IP" in error_str or "RequestBlocked" in error_str or "blocking your requests, despite you using proxies" in error_str:
            raise TranscriptError(
                f"YouTube has temporarily blocked your IP for making too many requests. "
                f"Please wait a while before trying again."
            )
        raise TranscriptError(f"youtube-transcript-api error: {error_str}")


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

    # Fetch from YouTube (sync call)
    transcript = fetch_transcript(video_id)

    # Store in cache
    if redis_client is not None:
        try:
            await redis_client.set(cache_key, json.dumps(transcript), ex=cache_ttl)
            logger.info(f"Cached transcript for video {video_id} (TTL: {cache_ttl}s)")
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}. Continuing without cache.")

    return transcript
