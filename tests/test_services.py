"""
ClipForge AI — Tests for Services
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.transcript_service import extract_video_id, validate_youtube_url, TranscriptError
from app.services.chunking_service import (
    clean_transcript_text,
    merge_segments,
    chunk_transcript,
    process_transcript,
    get_full_transcript_text,
)
import pytest


# ----- Transcript Service Tests ----- #

def test_extract_video_id_standard_url():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_short_url():
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_embed_url():
    url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_shorts_url():
    url = "https://youtube.com/shorts/dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_with_params():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_url():
    assert extract_video_id("https://example.com") is None
    assert extract_video_id("not a url") is None


def test_validate_youtube_url_valid():
    video_id = validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert video_id == "dQw4w9WgXcQ"


def test_validate_youtube_url_empty():
    with pytest.raises(TranscriptError, match="empty"):
        validate_youtube_url("")


def test_validate_youtube_url_invalid():
    with pytest.raises(TranscriptError, match="Invalid"):
        validate_youtube_url("https://example.com")


# ----- Chunking Service Tests ----- #

def test_clean_transcript_text_whitespace():
    assert clean_transcript_text("  hello   world  ") == "hello world"


def test_clean_transcript_text_fillers():
    assert "um" not in clean_transcript_text("so um I was um thinking").lower()
    assert "uh" not in clean_transcript_text("uh well uh yeah").lower()


def test_clean_transcript_text_empty():
    assert clean_transcript_text("") == ""


def test_merge_segments_empty():
    assert merge_segments([]) == []


def test_merge_segments_merges_close():
    segments = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "world", "start": 1.0, "duration": 1.0},
    ]
    merged = merge_segments(segments, max_gap=1.5)
    assert len(merged) == 1
    assert "Hello" in merged[0]["text"]
    assert "world" in merged[0]["text"]


def test_merge_segments_keeps_distant():
    segments = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "world", "start": 10.0, "duration": 1.0},
    ]
    merged = merge_segments(segments, max_gap=1.5)
    assert len(merged) == 2


def test_chunk_transcript_empty():
    assert chunk_transcript([]) == []


def test_chunk_transcript_single_chunk():
    segments = [
        {"text": "Hello world", "start": 0.0, "end": 5.0, "duration": 5.0}
    ]
    chunks = chunk_transcript(segments, chunk_duration=300)
    assert len(chunks) == 1
    assert "Hello world" in chunks[0]


def test_process_transcript_empty():
    assert process_transcript([]) == []


def test_process_transcript_basic():
    segments = [
        {"text": "Hello world", "start": 0.0, "duration": 5.0},
        {"text": "This is a test", "start": 5.0, "duration": 5.0},
    ]
    chunks = process_transcript(segments)
    assert isinstance(chunks, list)
    assert len(chunks) > 0


def test_get_full_transcript_text():
    segments = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "world", "start": 1.0, "duration": 1.0},
    ]
    full = get_full_transcript_text(segments)
    assert full == "Hello world"
