"""Cliente Open-Meteo: fetch current + daily forecast → WeatherSnapshot."""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any

import httpx


_WEATHER_CODES: dict[int, tuple[str, str]] = {
    0:  ("clear", "clear_day"),
    1:  ("mostly-clear", "mostly_clear"),
    2:  ("partly-cloudy", "partly_cloudy"),
    3:  ("overcast", "cloudy"),
    45: ("fog", "fog"),
    48: ("fog-rime", "fog"),
    51: ("drizzle-light", "drizzle"),
    53: ("drizzle-moderate", "drizzle"),
    55: ("drizzle-dense", "drizzle"),
    61: ("rain-slight", "rain"),
    63: ("rain-moderate", "rain"),
    65: ("rain-heavy", "rain"),
    71: ("snow-slight", "snow"),
    73: ("snow-moderate", "snow"),
    75: ("snow-heavy", "snow"),
    80: ("showers-slight", "rain"),
    81: ("showers-moderate", "rain"),
    82: ("showers-violent", "rain"),
    95: ("thunderstorm", "thunderstorm"),
    96: ("thunderstorm-hail", "thunderstorm"),
    99: ("thunderstorm-hail-heavy", "thunderstorm"),
}


def map_weather_code(code: int) -> tuple[str, str]:
    return _WEATHER_CODES.get(code, ("unknown", "unknown"))


def _wind_dir_to_compass(degrees: float) -> str:
    if degrees < 0 or degrees > 360:
        return "?"
    idx = int((degrees + 22.5) / 45) % 8
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][idx]


@dataclass
class WeatherSnapshot:
    ts: int
    city: str
    temp_c: float
    feels_c: float
    humidity_pct: float
    wind_kmh: float
    wind_dir: str
    condition: str
    icon: str
    forecast: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


class WeatherClient:
    """Cliente Open-Meteo: sem auth, sem token. Padrão 10min polling."""

    def __init__(self, base_url: str, timeout_s: float = 10.0):
        self._base_url = base_url
        self._timeout_s = timeout_s

    async def fetch_snapshot(self, *, lat: float, lon: float, city_label: str) -> WeatherSnapshot:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "wind_speed_10m,wind_direction_10m,weather_code",
            "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,weather_code",
            "forecast_days": 2,
            "timezone": "auto",
            "wind_speed_unit": "kmh",
        }
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            resp = await client.get(self._base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        cur = data["current"]
        cond, icon = map_weather_code(int(cur["weather_code"]))

        forecast: list[dict[str, Any]] = []
        daily = data["daily"]
        for i, day_label in enumerate(["today", "tomorrow"]):
            if i >= len(daily["time"]):
                break
            f_cond, f_icon = map_weather_code(int(daily["weather_code"][i]))
            forecast.append({
                "day":     day_label,
                "min":     float(daily["temperature_2m_min"][i]),
                "max":     float(daily["temperature_2m_max"][i]),
                "icon":    f_icon,
                "rain_mm": float(daily["precipitation_sum"][i]),
            })

        return WeatherSnapshot(
            ts=int(time.time()),
            city=city_label,
            temp_c=float(cur["temperature_2m"]),
            feels_c=float(cur["apparent_temperature"]),
            humidity_pct=float(cur["relative_humidity_2m"]),
            wind_kmh=float(cur["wind_speed_10m"]),
            wind_dir=_wind_dir_to_compass(float(cur["wind_direction_10m"])),
            condition=cond,
            icon=icon,
            forecast=forecast,
        )
