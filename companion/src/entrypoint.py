"""Entry point: spawn cada listener como task asyncio em paralelo."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from backup_watcher import BackupLogWatcher
from claude_usage import ClaudeUsagePoller
from config import load_config
from dbus_listener import DBusNotificationListener
from mqtt_client import MqttClient

log = logging.getLogger("companion")

_HEALTH_FILE = Path("/tmp/companion-health")


async def _heartbeat_task() -> None:
    """Touch health file a cada 30s pro Docker HEALTHCHECK."""
    while True:
        try:
            _HEALTH_FILE.touch()
        except OSError:
            log.warning("could not touch %s", _HEALTH_FILE)
        await asyncio.sleep(30)


async def main_async() -> None:
    cfg = load_config(dict(os.environ))
    logging.basicConfig(
        level=cfg.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log.info(
        "starting companion: host=%s mqtt=%s:%d",
        cfg.host_id, cfg.mqtt_host, cfg.mqtt_port,
    )

    mqtt = MqttClient(
        host=cfg.mqtt_host, port=cfg.mqtt_port,
        username=cfg.mqtt_user, password=cfg.mqtt_pass,
        client_id=f"companion-{cfg.host_id}",
        lwt_topic=f"{cfg.topic_prefix_notifications}/status",
    )
    mqtt.connect()
    mqtt.publish_online_status()

    dbus_listener = DBusNotificationListener(
        mqtt=mqtt,
        topic_prefix=cfg.topic_prefix_notifications,
        filter_apps=cfg.filter_apps,
    )
    claude_poller = ClaudeUsagePoller(
        mqtt=mqtt,
        topic=cfg.topic_claude_usage,
        projects_dir=cfg.claude_projects_dir,
    )
    backup_watcher = BackupLogWatcher(
        mqtt=mqtt,
        topic_prefix=cfg.topic_prefix_backups,
        log_path=cfg.backup_log_path,
        host_id=cfg.host_id,
        batch_size=cfg.backup_batch_size,
        idle_seconds=cfg.backup_batch_idle_seconds,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    tasks = [
        asyncio.create_task(_heartbeat_task(), name="heartbeat"),
        asyncio.create_task(dbus_listener.run(), name="dbus"),
        asyncio.create_task(claude_poller.run(), name="claude"),
        asyncio.create_task(backup_watcher.run(), name="backup"),
        asyncio.create_task(stop_event.wait(), name="stop"),
    ]
    _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    log.info("shutting down")
    mqtt.disconnect()


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
