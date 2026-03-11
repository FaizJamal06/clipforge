"""
ClipForge AI — Tests for LangGraph State Schema
"""

from app.graph.state import ClipForgeState


def test_clipforge_state_creation():
    """Test that ClipForgeState can be instantiated with all required fields."""
    state: ClipForgeState = {
        "youtube_url": "https://www.youtube.com/watch?v=test123",
        "video_id": "test123",
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

    assert state["youtube_url"] == "https://www.youtube.com/watch?v=test123"
    assert state["video_id"] == "test123"
    assert state["retry_count"] == 0
    assert state["status"] == "initialized"
    assert isinstance(state["transcript"], list)
    assert isinstance(state["candidate_clips"], list)
    assert isinstance(state["errors"], list)


def test_clipforge_state_update():
    """Test that state fields can be updated (simulating node behavior)."""
    state: ClipForgeState = {
        "youtube_url": "",
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

    # Simulate input handler update
    updates = {"video_id": "abc123", "status": "input_validated"}
    state = {**state, **updates}

    assert state["video_id"] == "abc123"
    assert state["status"] == "input_validated"
