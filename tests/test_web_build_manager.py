#!/usr/bin/env python3
"""Regression tests for mode-specific web build manager logging."""

from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas import BuildMode, BuildStage, BuildStatus
from app.services.web_build_manager import BuildRunState, WebBuildManager


def make_run(mode: BuildMode) -> BuildRunState:
    """Create one mutable build run state for direct workflow testing."""
    return BuildRunState(
        id="run-1",
        mode=mode,
        status=BuildStatus.RUNNING,
        stage=BuildStage.COLLECTING_DOCS,
        started_at=datetime.now(),
        updated_at=datetime.now(),
        can_pause=True,
        can_resume=False,
    )


def test_incremental_workflow_emits_incremental_mode_log(monkeypatch: pytest.MonkeyPatch):
    """Incremental-only workflows should emit a log that explicitly skips repository sync."""
    manager = WebBuildManager()
    run = make_run(BuildMode.INCREMENTAL)
    manager._runs[run.id] = run
    manager._active_run_id = run.id
    observed: dict[str, bool] = {}

    def fake_run_index_build(run_state: BuildRunState, full_rebuild: bool) -> None:
        """Record the requested build mode without invoking the real index builder."""
        observed["full_rebuild"] = full_rebuild
        manager._clear_active_run(run_state.id)

    monkeypatch.setattr(manager, "_run_index_build", fake_run_index_build)

    manager._run_workflow(run.id, BuildMode.INCREMENTAL, False)

    messages = [event["data"]["message"] for event in run.events]
    assert "进入增量构建，跳过仓库同步" in messages
    assert observed["full_rebuild"] is False


def test_full_rebuild_workflow_emits_reset_logs(monkeypatch: pytest.MonkeyPatch):
    """Full rebuild workflows should emit reset-specific logs before indexing begins."""
    manager = WebBuildManager()
    run = make_run(BuildMode.FULL_REBUILD)
    manager._runs[run.id] = run
    manager._active_run_id = run.id
    observed: dict[str, bool] = {}

    def fake_run_index_build(run_state: BuildRunState, full_rebuild: bool) -> None:
        """Record the requested full rebuild flag without invoking the real index builder."""
        observed["full_rebuild"] = full_rebuild
        manager._clear_active_run(run_state.id)

    monkeypatch.setattr(manager, "_run_index_build", fake_run_index_build)

    manager._run_workflow(run.id, BuildMode.FULL_REBUILD, False)

    messages = [event["data"]["message"] for event in run.events]
    assert "开始全量重建，准备清空 SQLite 和 Qdrant 现有索引" in messages
    assert "已清空 SQLite 和 Qdrant，开始重新建库" in messages
    assert observed["full_rebuild"] is True
