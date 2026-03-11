"""
ClipForge AI — Tests for LangGraph Workflow
"""

import sys
import os

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
        "youtube_url": "https://www.youtube.com/watch?v=test123",
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


def test_input_handler_node():
    """Test that input_handler returns expected state updates."""
    state = _make_initial_state()
    result = input_handler(state)

    assert "video_id" in result
    assert "status" in result
    assert result["status"] == "input_validated"


def test_transcript_retrieval_node():
    """Test that transcript_retrieval returns transcript data."""
    state = _make_initial_state()
    state["video_id"] = "test123"
    result = transcript_retrieval(state)

    assert "transcript" in result
    assert isinstance(result["transcript"], list)
    assert result["status"] == "transcript_retrieved"


def test_transcript_processing_node():
    """Test that transcript_processing returns chunks."""
    state = _make_initial_state()
    state["transcript"] = [{"text": "Hello world", "start": 0.0, "duration": 5.0}]
    result = transcript_processing(state)

    assert "transcript_chunks" in result
    assert isinstance(result["transcript_chunks"], list)
    assert result["status"] == "transcript_processed"


def test_clip_discovery_node():
    """Test that clip_discovery returns candidate clips."""
    state = _make_initial_state()
    state["transcript_chunks"] = ["Test chunk content"]
    result = clip_discovery(state)

    assert "candidate_clips" in result
    assert isinstance(result["candidate_clips"], list)
    assert result["status"] == "clips_discovered"


def test_clip_validation_node():
    """Test that clip_validation returns validation results."""
    state = _make_initial_state()
    state["candidate_clips"] = [{"clip_text": "test", "start_time": 0, "end_time": 45}]
    result = clip_validation(state)

    assert "validated_clips" in result
    assert "failed_clips" in result
    assert result["status"] == "clips_validated"


def test_editing_plan_node():
    """Test that editing_plan returns editing plans."""
    state = _make_initial_state()
    state["validated_clips"] = [{"clip_text": "test", "start_time": 0, "end_time": 45}]
    result = editing_plan(state)

    assert "editing_plans" in result
    assert isinstance(result["editing_plans"], list)
    assert result["status"] == "editing_plans_generated"


def test_output_formatter_node():
    """Test that output_formatter sets completed status."""
    state = _make_initial_state()
    result = output_formatter(state)

    assert result["status"] == "completed"
