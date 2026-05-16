"""Watcher do log do rsync.

Tail incremental + batch detection. Publica:
- <prefix>/<host_id>/in-progress  retain=true   (state "idle"|"running")
- <prefix>/<host_id>/last-run     retain=true   (sumário ao fechar batch)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiofiles

from listener import Listener
from mqtt_client import MqttClient

log = logging.getLogger(__name__)


@dataclass
class RsyncEvent:
    kind: str       # "start" | "ok" | "error"
    pid: str
    ts: str
    error_code: int = 0
    error_msg: str = ""
    path: str = ""


_RE_START = re.compile(
    r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+\[(\d+)\] building file list\s*$"
)
_RE_OK = re.compile(
    r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+\[(\d+)\] total size is .+? speedup is"
)
_RE_ERR = re.compile(
    r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+\[(\d+)\] rsync error: .+ \(code (\d+)\)"
)
_RE_LINK = re.compile(
    r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+\[(\d+)\] rsync: .* \"([^\"]+)\" failed"
)


def parse_log_line(line: str) -> RsyncEvent | None:
    line = line.rstrip()
    m = _RE_START.match(line)
    if m:
        return RsyncEvent(kind="start", ts=m.group(1), pid=m.group(2))
    m = _RE_OK.match(line)
    if m:
        return RsyncEvent(kind="ok", ts=m.group(1), pid=m.group(2))
    m = _RE_ERR.match(line)
    if m:
        return RsyncEvent(
            kind="error", ts=m.group(1), pid=m.group(2), error_code=int(m.group(3))
        )
    m = _RE_LINK.match(line)
    if m:
        return RsyncEvent(
            kind="error", ts=m.group(1), pid=m.group(2),
            error_code=2, path=m.group(3), error_msg="link_stat failed",
        )
    return None


@dataclass
class _BatchState:
    started_at_ts: int = 0
    started_at_str: str = ""
    rsyncs_total: int = 0
    rsyncs_ok: int = 0
    rsyncs_error: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    last_event_ts: int = 0
    last_started_pid: str = ""


class BatchAggregator:
    """Acumula RsyncEvents. Fecha quando batch_size atingido ou idle_seconds sem evento."""

    def __init__(self, batch_size: int, idle_seconds: int):
        self._batch_size = batch_size
        self._idle_seconds = idle_seconds
        self._state: _BatchState | None = None

    def process(self, ev: RsyncEvent, *, now_ts: int) -> bool:
        """Retorna True se batch fechou após esse evento."""
        if self._state is None:
            self._state = _BatchState(started_at_ts=now_ts, started_at_str=ev.ts)
        self._state.last_event_ts = now_ts

        if ev.kind == "start":
            self._state.last_started_pid = ev.pid
        elif ev.kind == "ok":
            self._state.rsyncs_total += 1
            self._state.rsyncs_ok += 1
        elif ev.kind == "error":
            # Dedupar: "link_stat failed" (code 2) frequentemente vem ANTES do
            # "rsync error code 23" do mesmo rsync. Promove o registro pra code 23.
            if (ev.error_code == 23 and self._state.errors
                    and self._state.errors[-1]["code"] == 2):
                self._state.errors[-1]["code"] = 23
            else:
                self._state.rsyncs_total += 1
                self._state.rsyncs_error += 1
                self._state.errors.append({
                    "path": ev.path, "code": ev.error_code, "msg": ev.error_msg,
                })

        return self._state.rsyncs_total >= self._batch_size

    def maybe_close(self, *, now_ts: int) -> dict[str, Any] | None:
        if self._state is None:
            return None
        if now_ts - self._state.last_event_ts >= self._idle_seconds and self._state.rsyncs_total > 0:
            return self.close()
        return None

    def close(self) -> dict[str, Any] | None:
        if self._state is None:
            return None
        s = self._state
        self._state = None
        return {
            "ts": int(time.time()),
            "source_host": "",  # caller (BackupLogWatcher) preenche
            "dest_host": "",    # caller preenche
            "started_at": s.started_at_ts,
            "duration_sec": max(0, s.last_event_ts - s.started_at_ts),
            "rsyncs_total": s.rsyncs_total,
            "rsyncs_ok": s.rsyncs_ok,
            "rsyncs_error": s.rsyncs_error,
            "bytes_sent": 0,
            "bytes_received": 0,
            "errors": s.errors,
        }


class BackupLogWatcher(Listener):
    name = "backup-watcher"

    def __init__(
        self,
        mqtt: MqttClient,
        topic_prefix: str,
        log_path: str,
        host_id: str,
        dest_host: str = "",
        batch_size: int = 18,
        idle_seconds: int = 60,
    ):
        self._mqtt = mqtt
        self._prefix = topic_prefix
        self._log_path = Path(log_path)
        self._host_id = host_id
        self._dest_host = dest_host
        self._agg = BatchAggregator(batch_size=batch_size, idle_seconds=idle_seconds)
        self._poll_interval_s = 2.0

    async def run(self) -> None:
        self._publish_in_progress({"state": "idle"})
        offset = self._log_path.stat().st_size if self._log_path.is_file() else 0

        while True:
            try:
                if not self._log_path.is_file():
                    await asyncio.sleep(self._poll_interval_s)
                    continue

                size = self._log_path.stat().st_size
                if size < offset:
                    log.warning("log truncated; reopening")
                    offset = 0
                if size > offset:
                    async with aiofiles.open(self._log_path, mode="r") as f:
                        await f.seek(offset)
                        async for line in f:
                            ev = parse_log_line(line)
                            if ev is None:
                                continue
                            now = int(time.time())
                            self._publish_in_progress({
                                "state": "running",
                                "dirs_done": (
                                    self._agg._state.rsyncs_total if self._agg._state else 0
                                ),
                            })
                            if self._agg.process(ev, now_ts=now):
                                summary = self._agg.close()
                                if summary:
                                    self._publish_summary(summary)
                                    self._publish_in_progress({"state": "idle"})
                    offset = size

                summary = self._agg.maybe_close(now_ts=int(time.time()))
                if summary:
                    self._publish_summary(summary)
                    self._publish_in_progress({"state": "idle"})

                await asyncio.sleep(self._poll_interval_s)
            except Exception:
                log.exception("backup_watcher loop error")
                await asyncio.sleep(5)

    def _publish_in_progress(self, payload: dict[str, Any]) -> None:
        topic = f"{self._prefix}/{self._host_id}/in-progress"
        if "ts" not in payload:
            payload["ts"] = int(time.time())
        self._mqtt.publish_retained(topic, payload, qos=1)

    def _publish_summary(self, summary: dict[str, Any]) -> None:
        summary["source_host"] = self._host_id
        summary["dest_host"] = self._dest_host
        topic = f"{self._prefix}/{self._host_id}/last-run"
        self._mqtt.publish_retained(topic, summary, qos=1)
        log.info(
            "published %s ok=%d err=%d", topic, summary["rsyncs_ok"], summary["rsyncs_error"],
        )
