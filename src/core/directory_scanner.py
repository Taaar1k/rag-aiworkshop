"""
Directory Scanner Worker for RAG System.
Monitors directories for file changes and triggers incremental indexing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from watchfiles import Change, awatch

from .incremental_index_manager import IncrementalIndexManager

logger = logging.getLogger(__name__)


class DirectoryScannerWorker:
    """Background worker that watches directories for file changes."""

    def __init__(
        self,
        index_manager: IncrementalIndexManager,
        watched_directories: List[Dict[str, Any]],
        debounce_ms: int = 500,
        poll_interval_s: int = 60,
        enabled: bool = True,
    ):
        self.index_manager = index_manager
        self.watched_directories = watched_directories
        self.debounce_ms = debounce_ms
        self.poll_interval_s = poll_interval_s
        self.enabled = enabled
        self._watch_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._running = False

    async def start(self) -> None:
        """Start the directory scanner."""
        if not self.enabled:
            logger.info("Directory scanning is disabled")
            return

        if self._running:
            logger.warning("Scanner already running")
            return

        paths_to_watch = [d.get("path", "") for d in self.watched_directories if d.get("path")]
        
        for dir_path in paths_to_watch:
            p = Path(dir_path)
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)

        initial_count = self.index_manager.initial_scan(paths_to_watch)
        logger.info("Initial scan complete: %d files", initial_count)

        self._stop_event.clear()
        self._watch_task = asyncio.create_task(self._watch_loop(paths_to_watch))
        self._running = True
        logger.info("DirectoryScannerWorker started")

    async def stop(self) -> None:
        """Stop the directory scanner."""
        if not self._running:
            return

        logger.info("Stopping DirectoryScannerWorker...")
        self._stop_event.set()

        if self._watch_task:
            try:
                await asyncio.wait_for(self._watch_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._watch_task.cancel()

        self._running = False
        self._watch_task = None

    async def _watch_loop(self, paths: List[str]) -> None:
        """Main watch loop."""
        logger.info("Watch loop started for paths: %s", paths)

        while not self._stop_event.is_set():
            try:
                changes = await asyncio.wait_for(
                    self._get_changes(paths),
                    timeout=self.poll_interval_s
                )

                if changes:
                    await self._process_changes(changes)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Watch loop error: %s", e)
                await asyncio.sleep(self.poll_interval_s)

    async def _get_changes(self, paths: List[str]) -> set:
        """Get file changes from watchfiles."""
        allowed_exts = set(ext.lower() for ext in self.index_manager.allowed_extensions)

        async for changes in awatch(*paths, recursive=True, raise_interrupt=False):
            filtered = set()
            for change_type, filepath in changes:
                if Path(filepath).suffix.lower() in allowed_exts:
                    filtered.add((change_type, filepath))
            return filtered
        return set()

    async def _process_changes(self, changes: set) -> None:
        """Process file changes."""
        file_changes: Dict[str, List] = {}
        for change_type, filepath in changes:
            if filepath not in file_changes:
                file_changes[filepath] = []
            file_changes[filepath].append(change_type)

        logger.info("Processing %d file change(s)", len(file_changes))

        for filepath, change_list in file_changes.items():
            final_change = "modified"
            if Change.deleted in change_list:
                final_change = "deleted"
            elif Change.added in change_list:
                final_change = "added"

            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.index_manager.handle_file_change,
                    filepath,
                    final_change
                )
            except Exception as e:
                logger.error("Failed to process %s: %s", filepath, e)

    def is_running(self) -> bool:
        """Check if scanner is running."""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """Get scanner status."""
        return {
            "scanner_running": self._running,
            "scanner_enabled": self.enabled,
            "watched_directories": len(self.watched_directories),
        }
