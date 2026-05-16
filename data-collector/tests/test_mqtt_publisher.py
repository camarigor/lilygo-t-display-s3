import json
from unittest.mock import MagicMock, patch

from mqtt_publisher import MqttPublisher


def test_connects_with_auth_and_lwt():
    with patch("mqtt_publisher.mqtt.Client") as MockClient:
        inst = MagicMock(); MockClient.return_value = inst
        p = MqttPublisher(host="h", port=1, username="u", password="p",
                          client_id="c", lwt_topic="t", lwt_payload="offline")
        p.connect()
        inst.username_pw_set.assert_called_once_with("u", "p")
        inst.will_set.assert_called_once_with("t", payload="offline", qos=1, retain=True)
        inst.connect.assert_called_once_with("h", 1, keepalive=60)


def test_publish_retained_serializes():
    with patch("mqtt_publisher.mqtt.Client") as MockClient:
        inst = MagicMock(); MockClient.return_value = inst
        p = MqttPublisher(host="x", port=1, username="u", password="p", client_id="c")
        p._client = inst
        p.publish_retained("topic", {"k": "v"}, qos=0)
        inst.publish.assert_called_once()
        topic, payload = inst.publish.call_args[0]
        assert topic == "topic"
        assert json.loads(payload) == {"k": "v"}
