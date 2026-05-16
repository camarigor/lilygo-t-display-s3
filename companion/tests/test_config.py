"""Tests for config loader."""
import pytest

from config import CompanionConfig, load_config


def _base_env():
    return {
        "MQTT_HOST": "broker.example",
        "MQTT_PORT": "1883",
        "MQTT_USER": "daemon-host",
        "MQTT_PASS": "secret123",
        "TELEGRAF_HOSTNAME": "host-a",
        "TOPIC_PREFIX_NOTIFICATIONS": "notifications",
        "TOPIC_PREFIX_BACKUPS": "backups",
        "TOPIC_CLAUDE_USAGE": "claude/usage",
        "CLAUDE_PROJECTS_DIR": "/data/claude/projects",
        "BACKUP_LOG_PATH": "/data/backup.log",
        "BACKUP_BATCH_SIZE": "18",
        "BACKUP_BATCH_IDLE_SECONDS": "60",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        "FILTER_APPS": "teams-for-linux,org.telegram.desktop",
        "LOG_LEVEL": "INFO",
    }


def test_loads_full_config():
    cfg = load_config(_base_env())
    assert isinstance(cfg, CompanionConfig)
    assert cfg.mqtt_host == "broker.example"
    assert cfg.mqtt_port == 1883
    assert cfg.host_id == "host-a"
    assert cfg.backup_batch_size == 18
    assert cfg.filter_apps == ["teams-for-linux", "org.telegram.desktop"]


def test_loads_pass_from_file(tmp_path):
    pass_file = tmp_path / "pass.txt"
    pass_file.write_text("from-file\n")
    env = _base_env()
    del env["MQTT_PASS"]
    env["MQTT_PASS_FILE"] = str(pass_file)
    cfg = load_config(env)
    assert cfg.mqtt_pass == "from-file"


def test_missing_required_field_raises():
    env = _base_env()
    del env["MQTT_HOST"]
    with pytest.raises((KeyError, ValueError)):
        load_config(env)


def test_filter_apps_strips_whitespace():
    env = _base_env()
    env["FILTER_APPS"] = " teams-for-linux , Telegram Desktop "
    cfg = load_config(env)
    assert cfg.filter_apps == ["teams-for-linux", "Telegram Desktop"]
