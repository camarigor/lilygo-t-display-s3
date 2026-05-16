"""Wrapper paho-mqtt: connect com auth + LWT + publish retained."""
from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

log = logging.getLogger(__name__)


class MqttPublisher:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        client_id: str,
        lwt_topic: str | None = None,
        lwt_payload: str = "offline",
        keepalive_s: int = 60,
    ):
        self._host = host
        self._port = port
        self._client_id = client_id
        self._keepalive_s = keepalive_s
        self._lwt_topic = lwt_topic
        self._lwt_payload = lwt_payload

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            clean_session=False,
        )
        self._client.username_pw_set(username, password)
        if lwt_topic:
            self._client.will_set(lwt_topic, payload=lwt_payload, qos=1, retain=True)

    def connect(self) -> None:
        log.info("connecting to %s:%d as %s", self._host, self._port, self._client_id)
        self._client.connect(self._host, self._port, keepalive=self._keepalive_s)
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def publish_retained(self, topic: str, payload: dict[str, Any], qos: int = 0) -> None:
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self._client.publish(topic, serialized, qos=qos, retain=True)

    def publish_online_status(self) -> None:
        if not self._lwt_topic:
            return
        self._client.publish(self._lwt_topic, "online", qos=1, retain=True)
