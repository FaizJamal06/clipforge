"""
ClipForge AI — API Routes

REST endpoints for the ClipForge pipeline.
The frontend communicates with these endpoints to submit URLs
and retrieve processing results.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph.workflow import graph
from app.services.transcript_service import TranscriptError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["clipforge"])


# ----- Request / Response Models ----- #

class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""
    youtube_url: str = Field(
        ...,
        description="YouTube video URL to extract clips from.",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class ClipResult(BaseModel):
    """A single validated clip with its editing plan."""
    clip_text: str = Field(description="Verbatim clip transcript text.")
    start_time: float = Field(description="Clip start timestamp in seconds.")
    end_time: float = Field(description="Clip end timestamp in seconds.")
    duration: float = Field(description="Clip duration in seconds.")
    virality_score: float = Field(default=0.0, description="Virality score (0-10).")
    virality_reasoning: str = Field(default="", description="Why this clip is viral.")
    hook: str = Field(default="", description="The opening hook.")
    payoff: str = Field(default="", description="The satisfying payoff.")
    editing_plan: dict = Field(default_factory=dict, description="Editing blueprint for this clip.")


class ProcessResponse(BaseModel):
    """Response body for the /process endpoint."""
    status: str = Field(description="Processing status.")
    youtube_url: str = Field(description="Original input URL.")
    video_id: str = Field(description="Extracted YouTube video ID.")
    clips: list[ClipResult] = Field(default_factory=list, description="Validated clips with editing plans.")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered.")


# ----- Endpoints ----- #

@router.post("/process", response_model=ProcessResponse)
async def process_video(request: ProcessRequest):
    """Submit a YouTube URL for clip discovery and editing plan generation.

    Triggers the full LangGraph pipeline:
    1. Input validation & video ID extraction
    2. Transcript retrieval
    3. Transcript processing & chunking
    4. AI clip discovery
    5. Clip validation (with retry loop)
    6. Editing plan generation
    7. Output formatting
    """
    logger.info(f"Processing request for URL: {request.youtube_url}")

    # Build initial state
    initial_state = {
        "youtube_url": request.youtube_url,
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

    try:
        # Invoke the compiled LangGraph workflow
        final_state = await graph.ainvoke(initial_state)

        # Map validated clips to response format
        clips = []
        validated_clips = final_state.get("validated_clips", [])
        editing_plans = final_state.get("editing_plans", [])

        for i, clip in enumerate(validated_clips):
            # Find matching editing plan
            matching_plan = next(
                (p for p in editing_plans if p.get("clip_index") == i),
                {}
            )

            clips.append(ClipResult(
                clip_text=clip.get("clip_text", ""),
                start_time=clip.get("start_time", 0.0),
                end_time=clip.get("end_time", 0.0),
                duration=clip.get("duration", 0.0),
                virality_score=clip.get("virality_score", 0.0),
                virality_reasoning=clip.get("virality_reasoning", ""),
                hook=clip.get("hook", ""),
                payoff=clip.get("payoff", ""),
                editing_plan=matching_plan,
            ))

        response = ProcessResponse(
            status=final_state.get("status", "completed"),
            youtube_url=request.youtube_url,
            video_id=final_state.get("video_id", ""),
            clips=clips,
            errors=final_state.get("errors", []),
        )

        logger.info(f"Pipeline completed: {len(clips)} clips, status={response.status}")
        return response

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}",
        )


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of a processing job.

    TODO: Implement job tracking with database persistence in Phase 3.
    """
    raise HTTPException(
        status_code=501,
        detail="Job tracking not yet implemented — coming in Phase 3.",
    )
