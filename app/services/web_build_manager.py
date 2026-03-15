"""In-memory build task manager for the local web console."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import subprocess
import threading
from typing import Any, Dict, Iterable
import uuid

from app.schemas import BuildMode, BuildRunSummary, BuildStage, BuildStatus
from app.settings import Settings, get_settings
from scripts.build_index import IndexBuilder


@dataclass
class BuildRunState:
    """Mutable state for one build run."""

    id: str
    mode: BuildMode
    status: BuildStatus
    stage: BuildStage
    started_at: datetime
    updated_at: datetime
    processed_docs: int = 0
    total_docs: int = 0
    indexed_docs: int = 0
    reindexed_docs: int = 0
    skipped_docs: int = 0
    failed_docs: int = 0
    current_path: str = ""
    can_pause: bool = False
    can_resume: bool = False
    pause_requested: bool = False
    settings_snapshot: Settings | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    worker: threading.Thread | None = None

    def to_summary(self) -> BuildRunSummary:
        """Convert mutable state into response schema."""
        return BuildRunSummary(
            id=self.id,
            mode=self.mode,
            status=self.status,
            stage=self.stage,
            started_at=self.started_at,
            updated_at=self.updated_at,
            processed_docs=self.processed_docs,
            total_docs=self.total_docs,
            indexed_docs=self.indexed_docs,
            reindexed_docs=self.reindexed_docs,
            skipped_docs=self.skipped_docs,
            failed_docs=self.failed_docs,
            current_path=self.current_path,
            can_pause=self.can_pause,
            can_resume=self.can_resume,
        )


class WebBuildManager:
    """Coordinate one long-running build task at a time."""

    def __init__(self):
        self._runs: dict[str, BuildRunState] = {}
        self._active_run_id: str | None = None
        self._manager_lock = threading.Lock()

    def list_runs(self) -> list[BuildRunSummary]:
        """Return all known runs, newest first."""
        runs = sorted(
            self._runs.values(),
            key=lambda run: run.updated_at,
            reverse=True,
        )
        return [run.to_summary() for run in runs]

    def get_run(self, run_id: str) -> BuildRunSummary | None:
        """Return one run summary if present."""
        run = self._runs.get(run_id)
        return run.to_summary() if run else None

    def start_run(self, mode: BuildMode) -> BuildRunSummary:
        """Create and start a new build run."""
        with self._manager_lock:
            self._ensure_no_active_run()
            settings_snapshot = get_settings()
            run = BuildRunState(
                id=f"build-{uuid.uuid4().hex[:8]}",
                mode=mode,
                status=BuildStatus.RUNNING,
                stage=BuildStage.SYNCING_REPO
                if mode == BuildMode.SYNC_INCREMENTAL
                else BuildStage.COLLECTING_DOCS,
                started_at=datetime.now(),
                updated_at=datetime.now(),
                can_pause=True,
                can_resume=False,
                settings_snapshot=settings_snapshot,
            )
            self._runs[run.id] = run
            self._active_run_id = run.id
            self._append_event(
                run,
                "status",
                {
                    "message": "构建任务已启动",
                    "stage": run.stage.value,
                    "status": run.status.value,
                },
            )
            run.worker = threading.Thread(
                target=self._run_workflow,
                args=(run.id, mode, False),
                daemon=True,
            )
            run.worker.start()
            return run.to_summary()

    def request_pause(self, run_id: str) -> BuildRunSummary:
        """Ask the active run to stop after the current safe point."""
        run = self._require_run_state(run_id)
        with run.lock:
            run.pause_requested = True
            run.status = BuildStatus.PAUSING
            run.updated_at = datetime.now()
            run.can_pause = False
            run.can_resume = False
            self._append_event(
                run,
                "status",
                {
                    "message": "收到暂停请求，正在安全收尾",
                    "stage": run.stage.value,
                    "status": run.status.value,
                },
            )
            return run.to_summary()

    def resume_run(self, run_id: str) -> BuildRunSummary:
        """Resume one paused run as an incremental build."""
        with self._manager_lock:
            self._ensure_no_active_run()
            run = self._require_run_state(run_id)
            with run.lock:
                if run.status != BuildStatus.PAUSED:
                    raise ValueError("只有已暂停的任务可以恢复")
                run.mode = BuildMode.INCREMENTAL
                run.status = BuildStatus.RUNNING
                run.stage = BuildStage.COLLECTING_DOCS
                run.updated_at = datetime.now()
                run.pause_requested = False
                run.can_pause = True
                run.can_resume = False
                self._append_event(
                    run,
                    "status",
                    {
                        "message": "已恢复任务，继续执行增量更新",
                        "stage": run.stage.value,
                        "status": run.status.value,
                    },
                )
            self._active_run_id = run.id
            run.worker = threading.Thread(
                target=self._run_workflow,
                args=(run.id, BuildMode.INCREMENTAL, True),
                daemon=True,
            )
            run.worker.start()
            return run.to_summary()

    async def stream_events(self, run_id: str):
        """Yield SSE events for one run by polling in-memory history."""
        run = self._require_run_state(run_id)
        index = 0
        while True:
            with run.lock:
                events = list(run.events[index:])
                terminal = run.status in {
                    BuildStatus.PAUSED,
                    BuildStatus.COMPLETED,
                    BuildStatus.FAILED,
                }
            for event in events:
                index += 1
                yield event
            if terminal and index >= len(run.events):
                break
            await asyncio.sleep(0.2)

    def _run_workflow(self, run_id: str, mode: BuildMode, is_resume: bool):
        """Execute sync/build work in a background thread."""
        run = self._require_run_state(run_id)
        try:
            if mode == BuildMode.SYNC_INCREMENTAL and not is_resume:
                self._sync_repo(run)
                if self._pause_before_next_stage(run):
                    return
            elif mode == BuildMode.INCREMENTAL:
                self._append_progress_message(run, "进入增量构建，跳过仓库同步")
            elif mode == BuildMode.FULL_REBUILD:
                self._append_progress_message(run, "开始全量重建，准备清空 SQLite 和 Qdrant 现有索引")
                self._append_progress_message(run, "已清空 SQLite 和 Qdrant，开始重新建库")

            self._run_index_build(
                run,
                full_rebuild=(mode == BuildMode.FULL_REBUILD),
            )
        except Exception as exc:
            with run.lock:
                run.status = BuildStatus.FAILED
                run.stage = BuildStage.FAILED
                run.updated_at = datetime.now()
                run.can_pause = False
                run.can_resume = False
                self._append_event(
                    run,
                    "error",
                    {
                        "message": f"构建失败：{exc}",
                        "stage": run.stage.value,
                        "status": run.status.value,
                    },
                )
            self._clear_active_run(run.id)

    def _sync_repo(self, run: BuildRunState):
        """Run the repository sync step with Chinese status events."""
        settings_snapshot = run.settings_snapshot or get_settings()
        with run.lock:
            run.stage = BuildStage.SYNCING_REPO
            run.updated_at = datetime.now()
            self._append_event(
                run,
                "progress",
                {
                    "message": "开始同步文档仓库",
                    "stage": run.stage.value,
                },
            )

        repo_path = Path(settings_snapshot.docs_local_path)
        if not repo_path.exists():
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    settings_snapshot.docs_branch,
                    settings_snapshot.docs_repo_url,
                    str(repo_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
        else:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "pull",
                    "origin",
                    settings_snapshot.docs_branch,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "同步仓库失败")

        file_count = 0
        for dir_name in settings_snapshot.include_dirs_list:
            target_dir = repo_path / dir_name
            if target_dir.exists():
                file_count += len(list(target_dir.rglob("*.md")))

        with run.lock:
            self._append_event(
                run,
                "progress",
                {
                    "message": f"仓库同步完成，已发现 {file_count} 个 Markdown 文件",
                    "stage": run.stage.value,
                    "total_docs": file_count,
                },
            )

    def _run_index_build(self, run: BuildRunState, full_rebuild: bool):
        """Execute the index builder with progress callbacks."""
        with run.lock:
            run.stage = BuildStage.COLLECTING_DOCS
            run.updated_at = datetime.now()

        builder = IndexBuilder(settings_snapshot=run.settings_snapshot)
        summary = asyncio.run(
            builder.build(
                full_rebuild=full_rebuild,
                progress_callback=lambda event: self._handle_builder_event(run, event),
                should_pause=lambda: self._should_pause(run),
            )
        )

        with run.lock:
            run.processed_docs = summary["processed_docs"]
            run.total_docs = summary["total_docs"]
            run.indexed_docs = summary["indexed_docs"]
            run.reindexed_docs = summary["reindexed_docs"]
            run.skipped_docs = summary["skipped_docs"]
            run.failed_docs = summary["failed_docs"]
            run.current_path = summary.get("current_path", "")
            run.updated_at = datetime.now()

            if summary["status"] == BuildStatus.PAUSED.value:
                run.status = BuildStatus.PAUSED
                run.stage = BuildStage.PAUSED
                run.can_pause = False
                run.can_resume = True
                self._append_event(
                    run,
                    "status",
                    {
                        "message": "已暂停，可继续增量恢复",
                        "stage": run.stage.value,
                        "status": run.status.value,
                    },
                )
            else:
                run.status = BuildStatus.COMPLETED
                run.stage = BuildStage.COMPLETED
                run.can_pause = False
                run.can_resume = False
                self._append_event(
                    run,
                    "completed",
                    {
                        "message": "构建任务已完成",
                        "stage": run.stage.value,
                        "status": run.status.value,
                    },
                )
        self._clear_active_run(run.id)

    def _handle_builder_event(self, run: BuildRunState, event: dict[str, Any]):
        """Translate build-index progress events into run state and Chinese messages."""
        event_type = event.get("type")
        if event_type == "collection_scanned":
            with run.lock:
                run.stage = BuildStage.COLLECTING_DOCS
                run.total_docs = event["total_docs"]
                run.updated_at = datetime.now()
                self._append_event(
                    run,
                    "progress",
                    {
                        "message": f"已发现 {event['total_docs']} 个 Markdown 文件",
                        "stage": run.stage.value,
                        "total_docs": run.total_docs,
                    },
                )
        elif event_type == "document_started":
            with run.lock:
                run.stage = BuildStage.INDEXING
                run.current_path = event["path"]
                run.updated_at = datetime.now()
                self._append_event(
                    run,
                    "progress",
                    {
                        "message": (
                            f"正在处理 {event['current_index']}/{event['total_docs']}："
                            f"{event['path']}"
                        ),
                        "stage": run.stage.value,
                        "processed_docs": event["processed_docs"],
                        "total_docs": event["total_docs"],
                        "current_path": event["path"],
                    },
                )

    def _append_event(self, run: BuildRunState, event_name: str, data: Dict[str, Any]):
        """Store one structured event for later SSE replay."""
        seq = len(run.events) + 1
        run.events.append(
            {
                "seq": seq,
                "event": event_name,
                "data": {
                    **data,
                    "seq": seq,
                },
            }
        )

    def _append_progress_message(self, run: BuildRunState, message: str) -> None:
        """Append one normalized progress message while keeping stage and timestamps consistent."""
        with run.lock:
            run.updated_at = datetime.now()
            self._append_event(
                run,
                "progress",
                {
                    "message": message,
                    "stage": run.stage.value,
                    "status": run.status.value,
                },
            )

    def _pause_before_next_stage(self, run: BuildRunState) -> bool:
        """Pause between sync and build if requested."""
        with run.lock:
            if not run.pause_requested:
                return False
            run.status = BuildStatus.PAUSED
            run.stage = BuildStage.PAUSED
            run.updated_at = datetime.now()
            run.can_pause = False
            run.can_resume = True
            self._append_event(
                run,
                "status",
                {
                    "message": "已暂停，可继续增量恢复",
                    "stage": run.stage.value,
                    "status": run.status.value,
                },
            )
        self._clear_active_run(run.id)
        return True

    def _should_pause(self, run: BuildRunState) -> bool:
        """Return whether the current build should stop at the next safe point."""
        with run.lock:
            return run.pause_requested

    def _ensure_no_active_run(self):
        """Reject concurrent build runs."""
        if self._active_run_id is not None:
            active = self._runs.get(self._active_run_id)
            if active and active.status in {
                BuildStatus.RUNNING,
                BuildStatus.PAUSING,
            }:
                raise ValueError("当前已有构建任务在运行，请稍后再试")

    def _require_run_state(self, run_id: str) -> BuildRunState:
        """Return the mutable run state or raise."""
        run = self._runs.get(run_id)
        if not run:
            raise KeyError(run_id)
        return run

    def _clear_active_run(self, run_id: str):
        """Release the single-active-run lock."""
        with self._manager_lock:
            if self._active_run_id == run_id:
                self._active_run_id = None
