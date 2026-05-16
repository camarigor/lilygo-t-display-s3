import pytest
import respx
from httpx import Response

from weather_client import WeatherClient, WeatherSnapshot, map_weather_code


SAMPLE = {
    "current": {
        "time": "2026-05-15T23:00",
        "temperature_2m": 23.5, "apparent_temperature": 24.1,
        "relative_humidity_2m": 68, "wind_speed_10m": 12.0,
        "wind_direction_10m": 130, "weather_code": 3,
    },
    "daily": {
        "time": ["2026-05-15", "2026-05-16"],
        "temperature_2m_min": [18.0, 16.0],
        "temperature_2m_max": [27.0, 24.0],
        "precipitation_sum": [4.2, 0.0],
        "weather_code": [3, 1],
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_parsed_snapshot():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(return_value=Response(200, json=SAMPLE))
    c = WeatherClient(base_url="https://api.open-meteo.com/v1/forecast")
    s = await c.fetch_snapshot(lat=0.0, lon=0.0, city_label="TestCity")
    assert isinstance(s, WeatherSnapshot)
    assert s.city == "TestCity"
    assert s.temp_c == 23.5
    assert s.condition == "overcast"
    assert len(s.forecast) == 2
    assert s.forecast[0]["day"] == "today"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_on_500():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(return_value=Response(500))
    c = WeatherClient(base_url="https://api.open-meteo.com/v1/forecast")
    with pytest.raises(Exception):
        await c.fetch_snapshot(lat=0, lon=0, city_label="x")


def test_weather_code_mapping():
    assert map_weather_code(0) == ("clear", "clear_day")
    assert map_weather_code(3) == ("overcast", "cloudy")
    assert map_weather_code(63) == ("rain-moderate", "rain")
    assert map_weather_code(95) == ("thunderstorm", "thunderstorm")
