"""
ClipForge AI — Tests for LangGraph Workflow Nodes
"""

import sys
import os
import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.graph.nodes import (
    input_handler,
    transcript_retrieval,
    transcript_processing,
    clip_discovery,
    clip_validation,
    editing_plan,
    output_formatter,
)
from app.graph.state import ClipForgeState


def _make_initial_state() -> ClipForgeState:
    """Create a minimal initial state for testing."""
    return {
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_id": "",
        "transcript": [],
        "transcript_chunks": [],
        "candidate_clips": [],
        "validated_clips": [],
        "failed_clips": [],
        "editing_plans": [],
        "retry_count": 0,
        "errors": [],
        "status": "initialized",
    }


def test_input_handler_valid_url():
    """Test input_handler with a valid YouTube URL."""
    state = _make_initial_state()
    result = input_handler(state)

    assert result["video_id"] == "dQw4w9WgXcQ"
    assert result["status"] == "input_validated"
    assert result["errors"] == []


def test_input_handler_invalid_url():
    """Test input_handler with an invalid URL."""
    state = _make_initial_state()
    state["youtube_url"] = "https://example.com"
    result = input_handler(state)

    assert result["status"] == "failed"
    assert len(result["errors"]) > 0


def test_transcript_retrieval_no_video_id():
    """Test transcript_retrieval when video ID is missing."""
    state = _make_initial_state()
    state["video_id"] = ""
    result = transcript_retrieval(state)

    assert result["transcript"] == []
    assert result["status"] == "failed"


def test_transcript_processing_with_data():
    """Test transcript_processing with real segment data."""
    state = _make_initial_state()
    state["transcript"] = [
        {"text": "Hello world", "start": 0.0, "duration": 5.0},
        {"text": "This is great", "start": 5.0, "duration": 5.0},
    ]
    result = transcript_processing(state)

    assert "transcript_chunks" in result
    assert isinstance(result["transcript_chunks"], list)
    assert len(result["transcript_chunks"]) > 0
    assert result["status"] == "transcript_processed"


def test_transcript_processing_empty():
    """Test transcript_processing with no transcript."""
    state = _make_initial_state()
    result = transcript_processing(state)

    assert result["transcript_chunks"] == []
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_clip_discovery_no_chunks():
    """Test clip_discovery when no chunks are available."""
    state = _make_initial_state()
    result = await clip_discovery(state)

    assert result["candidate_clips"] == []
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_clip_validation_empty():
    """Test clip_validation with no clips."""
    state = _make_initial_state()
    result = await clip_validation(state)

    assert result["validated_clips"] == []
    assert result["status"] == "clips_validated"


@pytest.mark.asyncio
async def test_editing_plan_empty():
    """Test editing_plan with no validated clips."""
    state = _make_initial_state()
    result = await editing_plan(state)

    assert result["editing_plans"] == []
    assert result["status"] == "editing_plans_generated"


def test_output_formatter_no_clips():
    """Test output_formatter with no validated clips."""
    state = _make_initial_state()
    result = output_formatter(state)
    assert result["status"] == "completed_no_clips"


def test_output_formatter_with_clips():
    """Test output_formatter with validated clips."""
    state = _make_initial_state()
    state["validated_clips"] = [
        {"clip_text": "Test clip", "start_time": 0, "end_time": 45}
    ]
    state["editing_plans"] = [{"clip_index": 0, "title": "Test"}]
    result = output_formatter(state)
    assert result["status"] == "completed"
