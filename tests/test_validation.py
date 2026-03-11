"""
ClipForge AI — Tests for Clip Validation Agent
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agents.clip_validation_agent import (
    _normalize_text,
    _check_transcript_containment,
    _check_duration,
    validate,
)


def test_normalize_text():
    assert _normalize_text("  Hello   World  ") == "hello world"


def test_containment_exact_match():
    is_contained, score = _check_transcript_containment(
        "this is a test clip",
        "some intro text this is a test clip and more text"
    )
    assert is_contained is True
    assert score == 1.0


def test_containment_not_found():
    is_contained, score = _check_transcript_containment(
        "completely different text here",
        "the actual transcript content is about something else entirely"
    )
    assert is_contained is False


def test_duration_valid():
    clip = {"duration": 45.0, "start_time": 0, "end_time": 45}
    valid, reasons = _check_duration(clip)
    assert valid is True
    assert len(reasons) == 0


def test_duration_too_short():
    clip = {"duration": 20.0, "start_time": 0, "end_time": 20}
    valid, reasons = _check_duration(clip)
    assert valid is False
    assert any("short" in r.lower() for r in reasons)


def test_duration_too_long():
    clip = {"duration": 90.0, "start_time": 0, "end_time": 90}
    valid, reasons = _check_duration(clip)
    assert valid is False
    assert any("long" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_validate_passing_clip():
    """Test validation with a clip that exists in the transcript."""
    transcript = [{"text": "This is a great story about life and everything in it"}]
    clips = [{
        "clip_text": "This is a great story about life and everything in it",
        "start_time": 0,
        "end_time": 45,
        "duration": 45.0,
    }]
    result = await validate(clips, transcript)
    assert result.results[0].is_valid is True


@pytest.mark.asyncio
async def test_validate_hallucinated_clip():
    """Test validation with a clip that doesn't exist in the transcript."""
    transcript = [{"text": "The actual transcript content here"}]
    clips = [{
        "clip_text": "Something completely made up by the LLM",
        "start_time": 0,
        "end_time": 45,
        "duration": 45.0,
    }]
    result = await validate(clips, transcript)
    assert result.results[0].transcript_match is False
