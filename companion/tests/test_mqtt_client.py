"""Tests for mqtt_client wrapper."""
import json
from unittest.mock import MagicMock, patch

from mqtt_client import MqttClient


def test_connects_with_lwt_and_clean_session_false():
    with patch("mqtt_client.mqtt.Client") as MockClient:
        instance = MagicMock()
        MockClient.return_value = instance
        c = MqttClient(
            host="broker.example", port=1883,
            username="daemon-host", password="x",
            client_id="companion-test",
            lwt_topic="some/status",
        )
        c.connect()
        MockClient.assert_called_once()
        kwargs = MockClient.call_args.kwargs
        assert kwargs.get("client_id") == "companion-test"
        assert kwargs.get("clean_session") is False
        instance.username_pw_set.assert_called_once_with("daemon-host", "x")
        instance.will_set.assert_called_once_with(
            "some/status", payload="offline", qos=1, retain=True
        )
        instance.connect.assert_called_once_with("broker.example", 1883, keepalive=60)


def test_publish_retained_serializes_and_sets_flags():
    with patch("mqtt_client.mqtt.Client") as MockClient:
        instance = MagicMock()
        MockClient.return_value = instance
        c = MqttClient(host="x", port=1, username="u", password="p", client_id="c")
        c.connect()
        c.publish_retained("t", {"k": "v"}, qos=1)
        instance.publish.assert_called_with(
            "t", json.dumps({"k": "v"}, ensure_ascii=False, separators=(",", ":")),
            qos=1, retain=True,
        )


def test_publish_event_no_retain():
    with patch("mqtt_client.mqtt.Client") as MockClient:
        instance = MagicMock()
        MockClient.return_value = instance
        c = MqttClient(host="x", port=1, username="u", password="p", client_id="c")
        c.connect()
        c.publish_event("notifications/teams", {"id": "n-1"}, qos=1)
        instance.publish.assert_called_with(
            "notifications/teams",
            json.dumps({"id": "n-1"}, ensure_ascii=False, separators=(",", ":")),
            qos=1, retain=False,
        )


def test_publish_online_signals_via_lwt_topic():
    with patch("mqtt_client.mqtt.Client") as MockClient:
        instance = MagicMock()
        MockClient.return_value = instance
        c = MqttClient(host="x", port=1, username="u", password="p", client_id="c", lwt_topic="status")
        c.connect()
        c.publish_online_status()
        instance.publish.assert_called_with("status", "online", qos=1, retain=True)
