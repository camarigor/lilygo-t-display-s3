import pytest
from unittest.mock import AsyncMock, MagicMock

from main import build_cities_from_env, run_once


def test_build_cities_parses_csv():
    env = {
        "WEATHER_CITIES": "alpha,beta",
        "WEATHER_alpha_LABEL": "ALPHA",
        "WEATHER_alpha_LAT": "1.0",
        "WEATHER_alpha_LON": "2.0",
        "WEATHER_beta_LABEL": "BETA",
        "WEATHER_beta_LAT": "3.0",
        "WEATHER_beta_LON": "4.0",
    }
    cities = build_cities_from_env(env)
    assert len(cities) == 2
    assert cities[0]["id"] == "alpha"
    assert cities[0]["lat"] == 1.0


@pytest.mark.asyncio
async def test_run_once_polls_and_publishes():
    fake_client = MagicMock()
    fake_snap = MagicMock()
    fake_snap.to_payload.return_value = {"ts": 1, "city": "X"}
    fake_client.fetch_snapshot = AsyncMock(return_value=fake_snap)
    fake_pub = MagicMock()
    cities = [{"id": "alpha", "label": "ALPHA", "lat": 0.0, "lon": 0.0}]
    await run_once(client=fake_client, publisher=fake_pub, cities=cities, topic_prefix="data/weather")
    assert fake_pub.publish_retained.call_count == 1
    assert fake_pub.publish_retained.call_args[0][0] == "data/weather/alpha"
