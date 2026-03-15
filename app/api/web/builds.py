"""Build-task endpoints for the local web console."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import BuildRequest, BuildRunSummary
from app.services.web_build_manager import WebBuildManager

router = APIRouter()
build_manager = WebBuildManager()


@router.get("/builds", response_model=list[BuildRunSummary])
def list_build_runs():
    """Return recent build runs."""
    return build_manager.list_runs()


@router.post("/builds", response_model=BuildRunSummary)
def start_build(request: BuildRequest):
    """Start one build run."""
    try:
        return build_manager.start_run(request.mode)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/builds/{run_id}", response_model=BuildRunSummary)
def get_build_run(run_id: str):
    """Return one build run."""
    run = build_manager.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="构建任务不存在")
    return run


@router.post("/builds/{run_id}/pause", response_model=BuildRunSummary)
def pause_build(run_id: str):
    """Request safe pause for one build run."""
    try:
        return build_manager.request_pause(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="构建任务不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/builds/{run_id}/resume", response_model=BuildRunSummary)
def resume_build(run_id: str):
    """Resume one paused build run as incremental update."""
    try:
        return build_manager.resume_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="构建任务不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/builds/{run_id}/events")
async def stream_build_events(run_id: str):
    """Stream build events as SSE."""
    if build_manager.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="构建任务不存在")

    async def event_stream():
        async for event in build_manager.stream_events(run_id):
            yield (
                f"event: {event['event']}\n"
                f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
