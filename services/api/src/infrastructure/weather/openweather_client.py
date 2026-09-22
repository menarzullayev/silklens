"""OpenWeatherMap API client for weather-aware travel recommendations. SILK-0074."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from src.core.settings import get_settings

logger = logging.getLogger(__name__)

_FREE_TIER_CALLS_PER_DAY = 1_000  # OpenWeatherMap free tier limit


@dataclass(slots=True, frozen=True)
class WeatherData:
    city: str
    country_code: str
    temperature_c: float
    feels_like_c: float
    condition: str  # e.g. "Clear", "Rain", "Clouds", "Snow", "Thunderstorm"
    condition_code: int  # OpenWeatherMap weather code
    humidity_pct: int
    wind_speed_ms: float
    is_daytime: bool
    icon_code: str  # e.g. "01d", "10n"
    description: str  # e.g. "clear sky", "light rain"


class StubWeatherClient:
    """Deterministic weather stub for dev/test — always returns clear Samarkand weather."""

    async def current(self, lat: float, lng: float) -> WeatherData:
        return WeatherData(
            city="Samarkand",
            country_code="UZ",
            temperature_c=28.0,
            feels_like_c=27.0,
            condition="Clear",
            condition_code=800,
            humidity_pct=40,
            wind_speed_ms=3.2,
            is_daytime=True,
            icon_code="01d",
            description="clear sky",
        )

    async def forecast(self, lat: float, lng: float, days: int = 3) -> list[WeatherData]:
        return [await self.current(lat, lng)] * min(days, 3)


class OpenWeatherMapClient:
    """Real OpenWeatherMap API v2.5 client."""

    _BASE = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def current(self, lat: float, lng: float) -> WeatherData:
        params: dict[str, str | float] = {
            "lat": lat,
            "lon": lng,
            "appid": self._api_key,
            "units": "metric",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._BASE}/weather", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("OpenWeatherMap error: %s — using stub", exc)
            return await StubWeatherClient().current(lat, lng)

        weather = data.get("weather", [{}])[0]
        main = data.get("main", {})
        wind = data.get("wind", {})
        sys = data.get("sys", {})
        is_daytime = weather.get("icon", "01d").endswith("d")

        return WeatherData(
            city=data.get("name", ""),
            country_code=sys.get("country", ""),
            temperature_c=round(main.get("temp", 20.0), 1),
            feels_like_c=round(main.get("feels_like", 20.0), 1),
            condition=weather.get("main", "Clear"),
            condition_code=weather.get("id", 800),
            humidity_pct=int(main.get("humidity", 50)),
            wind_speed_ms=round(wind.get("speed", 0.0), 1),
            is_daytime=is_daytime,
            icon_code=weather.get("icon", "01d"),
            description=weather.get("description", ""),
        )

    async def forecast(self, lat: float, lng: float, days: int = 3) -> list[WeatherData]:
        """Simplified forecast using 3-hour blocks, returning daily summaries."""
        params: dict[str, str | float | int] = {
            "lat": lat,
            "lon": lng,
            "appid": self._api_key,
            "units": "metric",
            "cnt": min(days * 8, 24),  # 8 x 3-hour blocks per day
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._BASE}/forecast", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("OpenWeatherMap forecast error: %s — using stub", exc)
            return await StubWeatherClient().forecast(lat, lng, days)

        results: list[WeatherData] = []
        seen_dates: set[str] = set()
        for item in data.get("list", []):
            date = item.get("dt_txt", "")[:10]
            if date in seen_dates:
                continue
            seen_dates.add(date)
            weather = item.get("weather", [{}])[0]
            main = item.get("main", {})
            wind = item.get("wind", {})
            icon = weather.get("icon", "01d")
            results.append(
                WeatherData(
                    city=data.get("city", {}).get("name", ""),
                    country_code=data.get("city", {}).get("country", ""),
                    temperature_c=round(main.get("temp", 20.0), 1),
                    feels_like_c=round(main.get("feels_like", 20.0), 1),
                    condition=weather.get("main", "Clear"),
                    condition_code=weather.get("id", 800),
                    humidity_pct=int(main.get("humidity", 50)),
                    wind_speed_ms=round(wind.get("speed", 0.0), 1),
                    is_daytime=icon.endswith("d"),
                    icon_code=icon,
                    description=weather.get("description", ""),
                )
            )
        return results[:days]


def get_weather_client() -> OpenWeatherMapClient | StubWeatherClient:
    """Factory: real client if API key set, else stub."""
    settings = get_settings()
    key = settings.openweather_api_key
    if key:
        return OpenWeatherMapClient(api_key=key)
    return StubWeatherClient()
