"""
ClipForge AI — Tests for Services
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.transcript_service import extract_video_id
from app.services.chunking_service import clean_transcript_text, process_transcript


def test_extract_video_id_standard_url():
    """Test video ID extraction from standard YouTube URL."""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_short_url():
    """Test video ID extraction from youtu.be URL."""
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_embed_url():
    """Test video ID extraction from embed URL."""
    url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_url():
    """Test that invalid URLs return None."""
    assert extract_video_id("https://example.com") is None
    assert extract_video_id("not a url") is None


def test_clean_transcript_text():
    """Test basic text cleaning."""
    assert clean_transcript_text("  hello   world  ") == "hello world"
    assert clean_transcript_text("single") == "single"


def test_process_transcript_empty():
    """Test processing an empty transcript."""
    assert process_transcript([]) == []


def test_process_transcript_basic():
    """Test processing a basic transcript."""
    segments = [
        {"text": "Hello world", "start": 0.0, "duration": 5.0},
        {"text": "This is a test", "start": 5.0, "duration": 5.0},
    ]
    chunks = process_transcript(segments)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
