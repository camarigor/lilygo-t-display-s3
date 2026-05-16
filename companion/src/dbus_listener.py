"""D-Bus session bus monitor → MQTT notifications publisher.

Usa dbus-next em modo monitor (BecomeMonitor) pra eavesdrop em
org.freedesktop.Notifications.Notify (qualquer app que envia notif desktop).
Filtra apps mapeados em _APP_TO_SOURCE, sanitiza body via bleach + strip
de control chars, publica em <prefix>/<source> com qos=1, retain=False.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from typing import Any

import bleach
from dbus_next import Message
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType, MessageType

from listener import Listener
from mqtt_client import MqttClient

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


def parse_notification(*, app_name: str) -> str | None:
    """Map app_name to canonical source. Returns None se app não filtrado."""
    return _APP_TO_SOURCE.get(app_name.strip())


def sanitize_body(text: str) -> str:
    """Remove HTML tags + control chars + trunca em 200 chars (ellipsis)."""
    cleaned = bleach.clean(text, tags=[], strip=True)
    cleaned = _CTRL_CHARS.sub("", cleaned)
    if len(cleaned) > 200:
        cleaned = cleaned[:199] + "…"
    return cleaned


def build_payload_from_dbus(
    *,
    app_name: str,
    summary: str,
    body: str,
    urgency_hint: int,
    ts: int,
) -> dict[str, Any]:
    """Constrói payload pra publish. Retorna {} se app filtrado fora."""
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


class DBusNotificationListener(Listener):
    name = "dbus"

    def __init__(self, mqtt: MqttClient, topic_prefix: str, filter_apps: list[str] | None = None):
        self._mqtt = mqtt
        self._prefix = topic_prefix
        self._filter_apps = set(filter_apps) if filter_apps else set(_APP_TO_SOURCE.keys())

    async def run(self) -> None:
        """Conecta ao session bus, vira monitor, processa Notify chamadas."""
        backoff = 1.0
        while True:
            try:
                bus = await MessageBus(bus_type=BusType.SESSION).connect()
                log.info("connected to D-Bus session bus")

                rule = (
                    "type='method_call',"
                    "interface='org.freedesktop.Notifications',"
                    "member='Notify'"
                )
                msg = Message(
                    destination="org.freedesktop.DBus",
                    path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus.Monitoring",
                    member="BecomeMonitor",
                    signature="asu",
                    body=[[rule], 0],
                )
                reply = await bus.call(msg)
                if reply.message_type == MessageType.ERROR:
                    raise RuntimeError(f"BecomeMonitor failed: {reply.body}")

                queue: asyncio.Queue[Message] = asyncio.Queue()

                def _enqueue(m: Message) -> bool:
                    queue.put_nowait(m)
                    return False

                bus.add_message_handler(_enqueue)

                backoff = 1.0
                while True:
                    next_msg = await queue.get()
                    self._handle(next_msg)
            except Exception:
                log.exception("dbus listener error; reconnecting in %.0fs", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def _handle(self, msg: Message) -> None:
        if msg.member != "Notify" or msg.interface != "org.freedesktop.Notifications":
            return
        body = msg.body
        if len(body) < 8:
            return

        app_name = body[0] if isinstance(body[0], str) else ""
        summary = body[3] if isinstance(body[3], str) else ""
        body_text = body[4] if isinstance(body[4], str) else ""
        hints = body[6] if isinstance(body[6], dict) else {}

        urgency = 1
        if "urgency" in hints:
            try:
                urgency = int(hints["urgency"].value)
            except Exception:
                pass

        payload = build_payload_from_dbus(
            app_name=app_name, summary=summary, body=body_text,
            urgency_hint=urgency, ts=int(time.time()),
        )
        if not payload:
            return

        topic = f"{self._prefix}/{payload['source']}"
        self._mqtt.publish_event(topic, payload, qos=1)
        log.info("published %s id=%s urgency=%s", topic, payload["id"], payload["urgency"])
