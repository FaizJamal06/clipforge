"""
ClipForge AI — Full Pipeline Benchmark

Runs the entire pipeline end-to-end with detailed timing for every stage.
Outputs a structured performance report.
"""

import asyncio
import time
import logging
import json
import sys

# Capture all logs
log_lines = []

class LogCapture(logging.Handler):
    def emit(self, record):
        log_lines.append({
            "time": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(LogCapture())
# Also print to stderr for live progress
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
root_logger.addHandler(handler)


TEST_VIDEO = "https://youtu.be/FlibCSZ93gM"
VIDEO_ID = "FlibCSZ93gM"


async def benchmark():
    from app.graph.workflow import graph

    timings = {}
    t_total_start = time.time()

    # ── Stage 1: Transcript Fetch ──
    print("\n" + "=" * 60, file=sys.stderr)
    print("STAGE 1: Transcript Fetch", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    t0 = time.time()
    from app.services.transcript_service import fetch_transcript, validate_youtube_url
    vid = validate_youtube_url(TEST_VIDEO)
    transcript = fetch_transcript(vid)
    t1 = time.time()
    timings["transcript_fetch"] = {
        "duration_s": round(t1 - t0, 2),
        "segments": len(transcript),
        "total_words": sum(len(s.get("text", "").split()) for s in transcript),
        "video_duration_s": round(transcript[-1]["start"] + transcript[-1]["duration"], 1) if transcript else 0,
    }

    # ── Stage 2: Transcript Processing ──
    print("\n" + "=" * 60, file=sys.stderr)
    print("STAGE 2: Transcript Processing (clean + merge + chunk)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    t0 = time.time()
    from app.services.chunking_service import process_transcript
    chunks = process_transcript(transcript)
    t1 = time.time()
    timings["transcript_processing"] = {
        "duration_s": round(t1 - t0, 2),
        "input_segments": len(transcript),
        "output_chunks": len(chunks),
        "avg_chunk_chars": round(sum(len(c) for c in chunks) / max(len(chunks), 1)),
    }

    # ── Stage 3: Full Pipeline (graph.ainvoke) ──
    print("\n" + "=" * 60, file=sys.stderr)
    print("STAGE 3: Full LangGraph Pipeline", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    t0 = time.time()
    state = {"youtube_url": TEST_VIDEO, "chunk_offset": 0}
    result = await graph.ainvoke(state)
    t1 = time.time()
    timings["full_pipeline"] = {
        "duration_s": round(t1 - t0, 2),
    }

    # ── Extract stage-level timings from logs ──
    stage_markers = {
        "input_validation": ("Input validated", None),
        "transcript_retrieval": ("Attempting youtube-transcript-api", "Retrieved"),
        "transcript_chunking": ("Processed transcript into", None),
        "clip_discovery": ("Clip discovery:", "Discovered"),
        "clip_validation": ("Clip 0 validation", "Validation complete"),
        "editing_plan": ("Generating editing plans", "Generated"),
    }

    for stage, (start_marker, end_marker) in stage_markers.items():
        start_t = None
        end_t = None
        for log in log_lines:
            if start_marker and start_marker in log["message"] and start_t is None:
                start_t = log["time"]
            if end_marker and end_marker in log["message"]:
                end_t = log["time"]
        if start_t and end_t:
            timings[f"stage_{stage}"] = round(end_t - start_t, 2)

    # ── Count LLM calls ──
    llm_calls = sum(1 for l in log_lines if "AFC is enabled" in l["message"])
    rate_limit_waits = [l for l in log_lines if "window full" in l["message"] or "back-off" in l["message"]]
    errors_429 = [l for l in log_lines if "429" in l["message"] and l["level"] == "ERROR"]
    errors_any = [l for l in log_lines if l["level"] == "ERROR"]

    # ── Result summary ──
    clips = result.get("validated_clips", [])
    plans = result.get("editing_plans", [])
    errors = result.get("errors", [])

    t_total_end = time.time()
    timings["total_wall_time"] = round(t_total_end - t_total_start, 2)

    # ── Build report ──
    report = {
        "video": {
            "url": TEST_VIDEO,
            "id": VIDEO_ID,
            "duration_s": timings["transcript_fetch"]["video_duration_s"],
            "duration_human": f"{int(timings['transcript_fetch']['video_duration_s'] // 60)}m {int(timings['transcript_fetch']['video_duration_s'] % 60)}s",
        },
        "transcript": {
            "segments_raw": timings["transcript_fetch"]["segments"],
            "total_words": timings["transcript_fetch"]["total_words"],
            "chunks_after_processing": timings["transcript_processing"]["output_chunks"],
            "avg_chunk_chars": timings["transcript_processing"]["avg_chunk_chars"],
        },
        "timings": {
            "total_wall_time_s": timings["total_wall_time"],
            "transcript_fetch_s": timings["transcript_fetch"]["duration_s"],
            "transcript_processing_s": timings["transcript_processing"]["duration_s"],
            "full_pipeline_s": timings["full_pipeline"]["duration_s"],
            "stage_clip_discovery_s": timings.get("stage_clip_discovery", "N/A"),
            "stage_clip_validation_s": timings.get("stage_clip_validation", "N/A"),
            "stage_editing_plan_s": timings.get("stage_editing_plan", "N/A"),
        },
        "llm": {
            "total_llm_calls": llm_calls,
            "rate_limit_waits": len(rate_limit_waits),
            "errors_429": len(errors_429),
            "errors_total": len(errors_any),
        },
        "output": {
            "status": result.get("status"),
            "clips_validated": len(clips),
            "editing_plans": len(plans),
            "pipeline_errors": errors,
        },
        "clips_detail": [],
    }

    for i, clip in enumerate(clips):
        clip_info = {
            "index": i,
            "virality_score": clip.get("virality_score"),
            "duration_s": clip.get("duration"),
            "start_time": clip.get("start_time"),
            "end_time": clip.get("end_time"),
            "match_score": clip.get("match_score"),
            "hook_preview": str(clip.get("hook", ""))[:80],
            "clip_text_preview": str(clip.get("clip_text", ""))[:120] + "...",
        }
        report["clips_detail"].append(clip_info)

    for i, plan in enumerate(plans):
        if isinstance(plan, dict):
            report[f"plan_{i}_keys"] = list(plan.keys())
            report[f"plan_{i}_title"] = plan.get("title_suggestion", "N/A")
            report[f"plan_{i}_segments_count"] = len(plan.get("segments", []))

    return report


if __name__ == "__main__":
    report = asyncio.run(benchmark())
    print("\n\n")
    print("=" * 60)
    print("  CLIPFORGE PIPELINE BENCHMARK REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2, default=str))
