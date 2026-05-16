"""Polla ~/.claude/projects/ e publica claude/usage.

Heurística pra V1:
- Session: dir mais recentemente modificado dentro de projects_dir.
- Weekly: soma de todos os dirs nos últimos 7 dias.
- Tokens: soma de tokens_in + tokens_out de cada JSONL transcript.

Limits default ajustáveis via env vars CLAUDE_SESSION_LIMIT / CLAUDE_WEEKLY_LIMIT.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from listener import Listener
from mqtt_client import MqttClient

log = logging.getLogger(__name__)

SESSION_LIMIT_TOKENS_DEFAULT = 1_000_000
WEEKLY_LIMIT_TOKENS_DEFAULT = 50_000_000


def compute_rate_bucket(tokens_per_minute: float) -> str:
    if tokens_per_minute < 100:
        return "idle"
    if tokens_per_minute < 2000:
        return "low"
    if tokens_per_minute < 5000:
        return "medium"
    return "high"


def parse_transcript_tokens(path: Path) -> tuple[int, str]:
    """Lê JSONL, soma tokens_in+tokens_out, captura último 'model'."""
    if not path.is_file():
        return 0, ""
    total = 0
    model = ""
    try:
        with path.open() as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total += int(obj.get("tokens_in", 0)) + int(obj.get("tokens_out", 0))
                if "model" in obj:
                    model = str(obj["model"])
    except OSError:
        return 0, ""
    return total, model


def aggregate_session(projects_dir: Path) -> dict[str, Any]:
    """Acha o dir mais recente e soma tokens do transcript dentro."""
    if not projects_dir.is_dir():
        return {"tokens_used": 0, "model": ""}
    subdirs = sorted(
        (p for p in projects_dir.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if not subdirs:
        return {"tokens_used": 0, "model": ""}
    latest = subdirs[0]
    for name in ("transcript.jsonl", "session.jsonl", "messages.jsonl"):
        candidate = latest / name
        if candidate.is_file():
            total, model = parse_transcript_tokens(candidate)
            return {"tokens_used": total, "model": model}
    total = 0
    model = ""
    for jsonl in latest.rglob("*.jsonl"):
        t, m = parse_transcript_tokens(jsonl)
        total += t
        if m and not model:
            model = m
    return {"tokens_used": total, "model": model}


def aggregate_weekly(projects_dir: Path, now_ts: int) -> int:
    """Soma tokens de todos os dirs modificados nos últimos 7 dias."""
    if not projects_dir.is_dir():
        return 0
    cutoff = now_ts - 7 * 24 * 3600
    total = 0
    for sub in projects_dir.iterdir():
        if not sub.is_dir():
            continue
        if sub.stat().st_mtime < cutoff:
            continue
        for jsonl in sub.rglob("*.jsonl"):
            t, _ = parse_transcript_tokens(jsonl)
            total += t
    return total


class ClaudeUsagePoller(Listener):
    name = "claude-usage"

    def __init__(
        self,
        mqtt: MqttClient,
        topic: str,
        projects_dir: str,
        poll_interval_s: int = 60,
        session_limit: int = SESSION_LIMIT_TOKENS_DEFAULT,
        weekly_limit: int = WEEKLY_LIMIT_TOKENS_DEFAULT,
    ):
        self._mqtt = mqtt
        self._topic = topic
        self._dir = Path(projects_dir)
        self._poll_interval_s = poll_interval_s
        self._session_limit = session_limit
        self._weekly_limit = weekly_limit
        self._last_session_tokens = 0
        self._last_check_ts = int(time.time())

    async def run(self) -> None:
        while True:
            try:
                now = int(time.time())
                session = aggregate_session(self._dir)
                weekly_used = aggregate_weekly(self._dir, now)

                elapsed_min = max(1, (now - self._last_check_ts) / 60.0)
                delta = max(0, session["tokens_used"] - self._last_session_tokens)
                rate_tpm = delta / elapsed_min

                self._last_session_tokens = session["tokens_used"]
                self._last_check_ts = now

                payload = {
                    "ts": now,
                    "session": {
                        "tokens_used": session["tokens_used"],
                        "limit": self._session_limit,
                        "pct": round(session["tokens_used"] / self._session_limit * 100, 1),
                        "rate_tpm": round(rate_tpm, 0),
                    },
                    "weekly": {
                        "tokens_used": weekly_used,
                        "limit": self._weekly_limit,
                        "pct": round(weekly_used / self._weekly_limit * 100, 1),
                    },
                    "model": session["model"],
                    "rate_bucket": compute_rate_bucket(rate_tpm),
                }
                self._mqtt.publish_retained(self._topic, payload, qos=0)
                log.info(
                    "published %s session=%d weekly=%d",
                    self._topic, session["tokens_used"], weekly_used,
                )
            except Exception:
                log.exception("claude_usage poll error")
            await asyncio.sleep(self._poll_interval_s)
