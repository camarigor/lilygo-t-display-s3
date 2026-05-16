"""Wrapper paho-mqtt sync (rodando em thread interna do paho)."""
from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)


class MqttClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        client_id: str,
        lwt_topic: str | None = None,
        keepalive_s: int = 60,
    ):
        self._host = host
        self._port = port
        self._keepalive_s = keepalive_s
        self._lwt_topic = lwt_topic

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=False,
        )
        self._client.username_pw_set(username, password)
        if lwt_topic:
            self._client.will_set(lwt_topic, payload="offline", qos=1, retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(self, *args, **kwargs):
        log.info("mqtt connected")

    def _on_disconnect(self, *args, **kwargs):
        log.warning("mqtt disconnected")

    def connect(self) -> None:
        self._client.connect(self._host, self._port, keepalive=self._keepalive_s)
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    @staticmethod
    def _serialize(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def publish_retained(self, topic: str, payload: dict[str, Any], qos: int = 0) -> None:
        self._client.publish(topic, self._serialize(payload), qos=qos, retain=True)

    def publish_event(self, topic: str, payload: dict[str, Any], qos: int = 1) -> None:
        self._client.publish(topic, self._serialize(payload), qos=qos, retain=False)

    def publish_online_status(self) -> None:
        if self._lwt_topic:
            self._client.publish(self._lwt_topic, "online", qos=1, retain=True)
