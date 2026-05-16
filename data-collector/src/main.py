"""Entry point: loop infinito pollando Open-Meteo pra cada cidade definida."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

from mqtt_publisher import MqttPublisher
from weather_client import WeatherClient

log = logging.getLogger("data-collector")


def build_cities_from_env(env: dict[str, str]) -> list[dict[str, Any]]:
    csv = env.get("WEATHER_CITIES", "").strip()
    if not csv:
        return []
    ids = [c.strip() for c in csv.split(",") if c.strip()]
    cities = []
    for city_id in ids:
        cities.append({
            "id":    city_id,
            "label": env[f"WEATHER_{city_id}_LABEL"],
            "lat":   float(env[f"WEATHER_{city_id}_LAT"]),
            "lon":   float(env[f"WEATHER_{city_id}_LON"]),
        })
    return cities


async def run_once(
    *,
    client: WeatherClient,
    publisher: MqttPublisher,
    cities: list[dict[str, Any]],
    topic_prefix: str,
) -> None:
    for city in cities:
        try:
            snap = await client.fetch_snapshot(lat=city["lat"], lon=city["lon"], city_label=city["label"])
            topic = f"{topic_prefix}/{city['id']}"
            publisher.publish_retained(topic, snap.to_payload(), qos=0)
            log.info("published %s temp=%s", topic, snap.temp_c)
        except Exception:
            log.exception("failed to fetch/publish city=%s", city["id"])


async def main_loop(env: dict[str, str]) -> None:
    logging.basicConfig(
        level=env.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    mqtt_host       = env["MQTT_HOST"]
    mqtt_port       = int(env.get("MQTT_PORT", "1883"))
    mqtt_user       = env["MQTT_USER"]
    mqtt_pass       = env["MQTT_PASS"]
    open_meteo_url  = env.get("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
    poll_interval_s = int(env.get("POLL_INTERVAL_S", "600"))
    topic_prefix    = env.get("TOPIC_PREFIX_WEATHER", "data/weather")

    cities = build_cities_from_env(env)
    if not cities:
        log.error("no WEATHER_CITIES configured. Exiting.")
        sys.exit(1)
    log.info("configured cities: %s", [c["id"] for c in cities])

    publisher = MqttPublisher(
        host=mqtt_host, port=mqtt_port,
        username=mqtt_user, password=mqtt_pass,
        client_id="data-collector",
        lwt_topic="data/status", lwt_payload="offline",
    )
    publisher.connect()
    publisher.publish_online_status()

    client = WeatherClient(base_url=open_meteo_url)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    while not stop.is_set():
        await run_once(client=client, publisher=publisher, cities=cities, topic_prefix=topic_prefix)
        try:
            await asyncio.wait_for(stop.wait(), timeout=poll_interval_s)
        except asyncio.TimeoutError:
            pass

    log.info("shutting down")
    publisher.disconnect()


def main() -> None:
    env = dict(os.environ)
    if "MQTT_PASS_FILE" in env:
        with open(env["MQTT_PASS_FILE"]) as f:
            env["MQTT_PASS"] = f.read().strip()
    asyncio.run(main_loop(env))


if __name__ == "__main__":
    main()
