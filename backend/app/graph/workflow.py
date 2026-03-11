"""
ClipForge AI — LangGraph Workflow Definition

Constructs the directed graph that orchestrates the clip discovery pipeline.
Nodes are connected in sequence with a conditional validation retry loop.

Graph structure:
    input_handler → transcript_retrieval → transcript_processing →
    clip_discovery → clip_validation →(conditional)→ editing_plan → output_formatter
                          ↑                    |
                          └── retry (if fail) ─┘
"""

from langgraph.graph import StateGraph, END

from app.graph.state import ClipForgeState
from app.graph.nodes import (
    input_handler,
    transcript_retrieval,
    transcript_processing,
    clip_discovery,
    clip_validation,
    editing_plan,
    output_formatter,
)
from app.config import get_settings


def should_retry_validation(state: ClipForgeState) -> str:
    """Conditional edge: decides whether to retry clip discovery or proceed.

    Returns:
        "retry" — if validation failed and retries remain.
        "continue" — if validation passed or max retries reached.
    """
    settings = get_settings()
    max_retries = settings.max_validation_retries

    failed_clips = state.get("failed_clips", [])
    validated_clips = state.get("validated_clips", [])
    retry_count = state.get("retry_count", 0)

    # Proceed if we have validated clips or exhausted retries
    if validated_clips or retry_count >= max_retries:
        return "continue"

    # Retry if all clips failed and we haven't hit the limit
    if failed_clips and retry_count < max_retries:
        return "retry"

    return "continue"


def build_workflow() -> StateGraph:
    """Constructs and returns the compiled LangGraph workflow.

    Returns:
        A compiled StateGraph ready for invocation.
    """
    workflow = StateGraph(ClipForgeState)

    # Register all nodes
    workflow.add_node("input_handler", input_handler)
    workflow.add_node("transcript_retrieval", transcript_retrieval)
    workflow.add_node("transcript_processing", transcript_processing)
    workflow.add_node("clip_discovery", clip_discovery)
    workflow.add_node("clip_validation", clip_validation)
    workflow.add_node("editing_plan", editing_plan)
    workflow.add_node("output_formatter", output_formatter)

    # Set entry point
    workflow.set_entry_point("input_handler")

    # Wire sequential edges
    workflow.add_edge("input_handler", "transcript_retrieval")
    workflow.add_edge("transcript_retrieval", "transcript_processing")
    workflow.add_edge("transcript_processing", "clip_discovery")
    workflow.add_edge("clip_discovery", "clip_validation")

    # Conditional edge: validation retry loop
    workflow.add_conditional_edges(
        "clip_validation",
        should_retry_validation,
        {
            "retry": "clip_discovery",
            "continue": "editing_plan",
        },
    )

    # Continue to output
    workflow.add_edge("editing_plan", "output_formatter")
    workflow.add_edge("output_formatter", END)

    return workflow.compile()


# Compiled graph — import this to invoke the pipeline
graph = build_workflow()
