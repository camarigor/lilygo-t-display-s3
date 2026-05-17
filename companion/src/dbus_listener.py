"""D-Bus session bus monitor -> MQTT notifications publisher.

Spawna `dbus-monitor --session` (binary whitelisted no AppArmor) e parseia
o stdout pra capturar method_calls org.freedesktop.Notifications.Notify.
Approach via subprocess porque dbus-next/BecomeMonitor via Python e
bloqueado pelo dbus-broker do Ubuntu 24.04 mesmo com apparmor:unconfined.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid

import bleach

from listener import Listener

log = logging.getLogger(__name__)

_APP_TO_SOURCE = {
    "teams-for-linux": "teams",
    "Teams for Linux": "teams",
    "org.telegram.desktop": "telegram",
    "Telegram Desktop": "telegram",
    "telegram-desktop": "telegram",
}

_URGENCY = {0: "low", 1: "normal", 2: "critical"}

_CTRL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_RE_METHOD_CALL_NOTIFY = re.compile(
    r"^method call .* interface=org\.freedesktop\.Notifications;\s*member=Notify\s*$"
)
_RE_STRING = re.compile(r'^\s*string "(.*)"\s*$')
_RE_URGENCY = re.compile(r"variant\s+byte (\d+)\s*$")
# Notify signature termina em int32 (expire_timeout) — usado como end-of-block
# marker porque dbus-monitor não emite blank line entre messages.
_RE_END_NOTIFY = re.compile(r"^\s*int32 -?\d+\s*$")


def parse_notification(*, app_name: str) -> str | None:
    return _APP_TO_SOURCE.get(app_name.strip())


def sanitize_body(text: str) -> str:
    cleaned = bleach.clean(text, tags=[], strip=True)
    cleaned = _CTRL_CHARS.sub("", cleaned)
    if len(cleaned) > 200:
        cleaned = cleaned[:199] + "…"
    return cleaned


def build_payload_from_dbus(*, app_name, summary, body, urgency_hint, ts):
    source = parse_notification(app_name=app_name)
    if source is None:
        return {}
    return {
        "ts":       int(ts),
        "id":       f"n-{uuid.uuid4().hex[:8]}",
        "source":   source,
        "app_name": app_name[:64],
        "summary":  sanitize_body(summary)[:256],
        "body":     sanitize_body(body),
        "icon":     source,
        "urgency":  _URGENCY.get(urgency_hint, "normal"),
    }


def parse_dbus_monitor_block(lines):
    """Parse bloco do dbus-monitor stdout, extrai campos do Notify.

    Notify signature (susssasa{sv}i): app_name(s) replaces_id(u)
    app_icon(s) summary(s) body(s) actions(as) hints(a{sv}) timeout(i)
    Strings na ordem 0/2/3/4 = app_name/app_icon/summary/body.
    """
    if not lines or not _RE_METHOD_CALL_NOTIFY.match(lines[0]):
        return None

    strings = []
    urgency = 1
    in_urgency_dict = False

    for raw in lines[1:]:
        m = _RE_STRING.match(raw)
        if m:
            strings.append(m.group(1))
            if strings[-1] == "urgency":
                in_urgency_dict = True
            continue
        if in_urgency_dict:
            m = _RE_URGENCY.search(raw)
            if m:
                try:
                    urgency = int(m.group(1))
                except ValueError:
                    pass
                in_urgency_dict = False

    if len(strings) < 4:
        return None

    return {
        "app_name": strings[0],
        "app_icon": strings[1],
        "summary":  strings[2],
        "body":     strings[3],
        "urgency":  urgency,
    }


class DBusNotificationListener(Listener):
    name = "dbus"

    _MATCH_RULE = "interface='org.freedesktop.Notifications',member='Notify'"

    def __init__(self, mqtt, topic_prefix, filter_apps=None):
        self._mqtt = mqtt
        self._prefix = topic_prefix
        self._filter_apps = set(filter_apps) if filter_apps else set(_APP_TO_SOURCE.keys())

    async def run(self):
        backoff = 1.0
        while True:
            proc = None
            try:
                # stdbuf -oL força line-buffering no stdout do dbus-monitor
                # (default = block-buffering ~4KB quando piped, atrasa readline).
                proc = await asyncio.create_subprocess_exec(
                    "stdbuf", "-oL", "dbus-monitor", "--session", self._MATCH_RULE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                log.info("dbus-monitor started (pid=%d)", proc.pid)
                backoff = 1.0

                current_block = []
                while True:
                    line_bytes = await proc.stdout.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")

                    if line.startswith("method call ") or line.startswith("signal "):
                        if current_block:
                            self._handle_block(current_block)
                        current_block = [line]
                    elif line.strip() or current_block:
                        current_block.append(line)
                        # Flush eager quando vê o int32 final do Notify signature
                        # (caso contrário block só processa na próxima message).
                        if current_block and _RE_END_NOTIFY.match(line):
                            self._handle_block(current_block)
                            current_block = []

                if current_block:
                    self._handle_block(current_block)

                ret = await proc.wait()
                log.warning("dbus-monitor exited rc=%d; reconnecting in %.0fs", ret, backoff)
            except Exception:
                log.exception("dbus listener error; reconnecting in %.0fs", backoff)
                if proc and proc.returncode is None:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=3)
                    except asyncio.TimeoutError:
                        proc.kill()
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    def _handle_block(self, lines):
        parsed = parse_dbus_monitor_block(lines)
        if not parsed:
            return
        payload = build_payload_from_dbus(
            app_name=parsed["app_name"],
            summary=parsed["summary"],
            body=parsed["body"],
            urgency_hint=parsed["urgency"],
            ts=int(time.time()),
        )
        if not payload:
            return
        topic = f"{self._prefix}/{payload['source']}"
        self._mqtt.publish_event(topic, payload, qos=1)
        log.info("published %s id=%s urgency=%s", topic, payload["id"], payload["urgency"])
