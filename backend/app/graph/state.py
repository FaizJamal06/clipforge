"""
ClipForge AI — LangGraph State Schema

Defines the shared state object that flows through the LangGraph pipeline.
Each node reads from and writes to this state.
"""

from typing import TypedDict


class ClipForgeState(TypedDict):
    """Shared state for the ClipForge LangGraph pipeline.

    This state object is passed through all nodes in the workflow.
    Each node reads relevant fields and returns updates.

    Attributes:
        youtube_url: The input YouTube URL from the user.
        video_id: Extracted YouTube video ID.
        transcript: Raw transcript segments with timestamps.
        transcript_chunks: Processed and chunked transcript text.
        candidate_clips: Top clip candidates identified by the discovery agent.
        validated_clips: Clips that passed all validation checks.
        failed_clips: Clips that failed validation (tracked for retry context).
        editing_plans: Generated editing plans for each validated clip.
        retry_count: Current validation retry attempt number.
        errors: Error log for debugging and observability.
        status: Current pipeline status (e.g., "processing", "completed", "failed").
    """

    youtube_url: str
    video_id: str
    transcript: list[dict]
    transcript_chunks: list[str]
    candidate_clips: list[dict]
    validated_clips: list[dict]
    failed_clips: list[dict]
    editing_plans: list[dict]
    retry_count: int
    errors: list[str]
    status: str
