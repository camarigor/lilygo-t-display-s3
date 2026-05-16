"""Tests for D-Bus listener: filter + payload sanitization."""
from dbus_listener import (
    build_payload_from_dbus,
    parse_notification,
    sanitize_body,
)


def test_sanitize_body_strips_html_and_controls():
    s = sanitize_body("<script>alert('x')</script>\x00\x07Hello")
    assert "<script>" not in s
    assert "\x00" not in s
    assert "Hello" in s


def test_sanitize_body_truncates_at_200():
    s = sanitize_body("A" * 250)
    assert len(s) == 200
    assert s.endswith("…")


def test_parse_notification_maps_app_to_source():
    assert parse_notification(app_name="teams-for-linux") == "teams"
    assert parse_notification(app_name="org.telegram.desktop") == "telegram"
    assert parse_notification(app_name="Telegram Desktop") == "telegram"
    assert parse_notification(app_name="firefox") is None


def test_build_payload_from_dbus():
    payload = build_payload_from_dbus(
        app_name="teams-for-linux",
        summary="João Silva",
        body="<b>Reunião</b> confirmada",
        urgency_hint=1,
        ts=1715798400,
    )
    assert payload["source"] == "teams"
    assert payload["summary"] == "João Silva"
    assert "Reunião" in payload["body"]
    assert "<b>" not in payload["body"]
    assert payload["urgency"] == "normal"
    assert payload["ts"] == 1715798400
    assert payload["id"].startswith("n-")


def test_build_payload_critical_urgency():
    payload = build_payload_from_dbus(
        app_name="org.telegram.desktop",
        summary="ALERT",
        body="",
        urgency_hint=2,
        ts=1,
    )
    assert payload["urgency"] == "critical"


def test_build_payload_low_urgency_default():
    payload = build_payload_from_dbus(
        app_name="teams-for-linux", summary="x", body="y", urgency_hint=0, ts=1,
    )
    assert payload["urgency"] == "low"


def test_build_payload_filtered_app_returns_empty():
    payload = build_payload_from_dbus(
        app_name="firefox", summary="x", body="y", urgency_hint=1, ts=1,
    )
    assert payload == {}
