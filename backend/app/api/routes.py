"""
ClipForge AI — API Routes

REST endpoints for the ClipForge pipeline.
The frontend communicates with these endpoints to submit URLs
and retrieve processing results.
"""

import logging
import urllib.parse
import json
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.video import ProcessedVideo
from app.graph.workflow import graph
from app.services.transcript_service import TranscriptError
from app.security import InputSanitizer, sanitize_error

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
    chunk_offset: int = Field(default=0, description="Chunk offset to process.")


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
    editing_plan: str = Field(default="", description="Editing blueprint for this clip in raw text.")


class ProcessResponse(BaseModel):
    """Response body for the /process endpoint."""
    status: str = Field(description="Processing status.")
    youtube_url: str = Field(description="Original input URL.")
    video_id: str = Field(description="Extracted YouTube video ID.")
    clips: list[ClipResult] = Field(default_factory=list, description="Validated clips with editing plans.")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered.")


# ----- Helpers ----- #

def extract_video_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/")
    if "youtube.com" in parsed.netloc:
        query = urllib.parse.parse_qs(parsed.query)
        return query.get("v", [""])[0]
    return ""


def format_clips_from_state(final_state: dict) -> list[ClipResult]:
    clips = []
    validated_clips = final_state.get("validated_clips", [])
    editing_plans = final_state.get("editing_plans", [])

    for i, clip in enumerate(validated_clips):
        matching_plan_dict = next(
            (p for p in editing_plans if p.get("clip_index") == i),
            {}
        )
        raw_plan_text = matching_plan_dict.get("raw_plan", "")

        clips.append(ClipResult(
            clip_text=clip.get("clip_text", ""),
            start_time=clip.get("start_time", 0.0),
            end_time=clip.get("end_time", 0.0),
            duration=clip.get("duration", 0.0),
            virality_score=clip.get("virality_score", 0.0),
            virality_reasoning=clip.get("virality_reasoning", ""),
            hook=clip.get("hook", ""),
            payoff=clip.get("payoff", ""),
            editing_plan=raw_plan_text,
        ))
    return clips


# ----- Endpoints ----- #

@router.get("/process/stream")
async def stream_process_video(youtube_url: str, chunk_offset: int = 0, db: AsyncSession = Depends(get_db)):
    """Server-Sent Events (SSE) endpoint for processing a video in real-time."""
    # Sanitize input
    try:
        youtube_url = InputSanitizer.sanitize_url(youtube_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def event_generator():
        vid_id = extract_video_id(youtube_url)
        cache_key = f"{vid_id}_{chunk_offset}" if vid_id else f"unknown_{chunk_offset}"

        # 1. Check Database Cache First
        try:
            stmt = select(ProcessedVideo).where(ProcessedVideo.video_id == cache_key)
            result = await db.execute(stmt)
            cached_entry = result.scalar_one_or_none()
            
            if cached_entry:
                cached_payload = cached_entry.get_payload()
                if not cached_payload.get("errors"):
                    logger.info(f"SSE Cache Hit: {cache_key}")
                    # Yield instant completion
                    yield f"data: {json.dumps({'type': 'complete', 'data': cached_payload})}\n\n"
                    return
                else:
                    logger.info(f"SSE Cache Ignore (Poisoned): {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to read from cache: {e}")

        # 2. Build initial state
        initial_state = {
            "youtube_url": youtube_url,
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
            "chunk_offset": chunk_offset,
        }

        final_state = initial_state
        try:
            # 3. Stream LangGraph execution
            async for state in graph.astream(initial_state, stream_mode="values"):
                final_state = state
                status = state.get("status", "processing")
                # Yield progress update
                yield f"data: {json.dumps({'type': 'update', 'status': status})}\n\n"
                # Small sleep to ensure flush
                await asyncio.sleep(0.01)

            # 4. Format completion payload
            clips = format_clips_from_state(final_state)
            response = ProcessResponse(
                status=final_state.get("status", "completed"),
                youtube_url=youtube_url,
                video_id=final_state.get("video_id", ""),
                clips=clips,
                errors=final_state.get("errors", []),
            )
            
            # Save to Cache
            if response.status not in ["failed", "completed_no_clips"] and not response.errors and response.video_id:
                try:
                    new_cache = ProcessedVideo(
                        video_id=cache_key,
                        youtube_url=youtube_url
                    )
                    new_cache.set_payload(response.model_dump())
                    db.add(new_cache)
                    await db.commit()
                except Exception as e:
                    logger.warning(f"Failed to write to cache during SSE: {e}")
                    await db.rollback()

            # Yield final completion event
            yield f"data: {json.dumps({'type': 'complete', 'data': response.model_dump()})}\n\n"

        except Exception as e:
            logger.error(f"SSE Pipeline execution failed: {e}")
            error_response = ProcessResponse(
                status="failed",
                youtube_url=youtube_url,
                video_id="",
                clips=[],
                errors=[sanitize_error(e)]
            )
            yield f"data: {json.dumps({'type': 'error', 'data': error_response.model_dump()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/process", response_model=ProcessResponse)
async def process_video(request: ProcessRequest, db: AsyncSession = Depends(get_db)):
    """Legacy blocking endpoint - Submit a YouTube URL for clip discovery."""
    # Sanitize input
    try:
        request.youtube_url = InputSanitizer.sanitize_url(request.youtube_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(f"Processing request for URL: {request.youtube_url} | Offset: {request.chunk_offset}")

    vid_id = extract_video_id(request.youtube_url)
    cache_key = f"{vid_id}_{request.chunk_offset}" if vid_id else f"unknown_{request.chunk_offset}"

    # Check Database Cache First
    try:
        stmt = select(ProcessedVideo).where(ProcessedVideo.video_id == cache_key)
        result = await db.execute(stmt)
        cached_entry = result.scalar_one_or_none()
        
        if cached_entry:
            cached_payload = cached_entry.get_payload()
            if not cached_payload.get("errors"):
                logger.info(f"Serve from Cache Hit: {cache_key}")
                return ProcessResponse(**cached_payload)
            else:
                logger.info(f"Serve from Cache Ignore (Poisoned): {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to read from cache: {e}")

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
        "chunk_offset": request.chunk_offset,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        clips = format_clips_from_state(final_state)

        response = ProcessResponse(
            status=final_state.get("status", "completed"),
            youtube_url=request.youtube_url,
            video_id=final_state.get("video_id", ""),
            clips=clips,
            errors=final_state.get("errors", []),
        )

        # Save to Database Cache
        try:
            if response.status not in ["failed", "completed_no_clips"] and not response.errors and response.video_id:
                new_cache = ProcessedVideo(
                    video_id=cache_key,
                    youtube_url=request.youtube_url
                )
                new_cache.set_payload(response.model_dump())
                db.add(new_cache)
                await db.commit()
                logger.info(f"Saved to cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to write to cache: {e}")
            await db.rollback()
            
        return response

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=sanitize_error(e),
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
