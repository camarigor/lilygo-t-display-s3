"""Carrega config do env, valida via pydantic.

Source of truth pro host id é a env var TELEGRAF_HOSTNAME — mesma que
o telegraf-system-docker.conf consome. Internalmente fica como
`host_id` no model pra clareza.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CompanionConfig(BaseModel):
    mqtt_host: str
    mqtt_port: int = 1883
    mqtt_user: str
    mqtt_pass: str
    host_id: str
    topic_prefix_notifications: str = "notifications"
    topic_prefix_backups: str = "backups"
    topic_claude_usage: str = "claude/usage"
    claude_projects_dir: str = "/data/claude/projects"
    backup_log_path: str = "/data/backup.log"
    backup_batch_size: int = 18
    backup_batch_idle_seconds: int = 60
    dbus_session_bus_address: str = ""
    filter_apps: list[str] = Field(default_factory=list)
    log_level: str = "INFO"

    @field_validator("filter_apps", mode="before")
    @classmethod
    def _split_csv(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v or []


def load_config(env: dict[str, str]) -> CompanionConfig:
    mqtt_pass = env.get("MQTT_PASS")
    if not mqtt_pass:
        pass_file = env.get("MQTT_PASS_FILE")
        if pass_file and Path(pass_file).is_file():
            mqtt_pass = Path(pass_file).read_text().strip()
        else:
            raise ValueError("MQTT_PASS or MQTT_PASS_FILE required")

    return CompanionConfig(
        mqtt_host=env["MQTT_HOST"],
        mqtt_port=int(env.get("MQTT_PORT", "1883")),
        mqtt_user=env["MQTT_USER"],
        mqtt_pass=mqtt_pass,
        host_id=env["TELEGRAF_HOSTNAME"],
        topic_prefix_notifications=env.get("TOPIC_PREFIX_NOTIFICATIONS", "notifications"),
        topic_prefix_backups=env.get("TOPIC_PREFIX_BACKUPS", "backups"),
        topic_claude_usage=env.get("TOPIC_CLAUDE_USAGE", "claude/usage"),
        claude_projects_dir=env.get("CLAUDE_PROJECTS_DIR", "/data/claude/projects"),
        backup_log_path=env.get("BACKUP_LOG_PATH", "/data/backup.log"),
        backup_batch_size=int(env.get("BACKUP_BATCH_SIZE", "18")),
        backup_batch_idle_seconds=int(env.get("BACKUP_BATCH_IDLE_SECONDS", "60")),
        dbus_session_bus_address=env.get("DBUS_SESSION_BUS_ADDRESS", ""),
        filter_apps=env.get("FILTER_APPS", ""),
        log_level=env.get("LOG_LEVEL", "INFO"),
    )
