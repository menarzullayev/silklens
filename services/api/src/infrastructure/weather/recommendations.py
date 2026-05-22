"""Weather-based venue recommendation logic. SILK-0074."""

from __future__ import annotations

from src.infrastructure.weather.openweather_client import WeatherData

# OpenWeatherMap weather code ranges:
# 2xx = Thunderstorm, 3xx = Drizzle, 5xx = Rain, 6xx = Snow
# 7xx = Atmosphere (fog/haze), 800 = Clear, 80x = Clouds


def _is_bad_weather(w: WeatherData) -> bool:
    return w.condition_code < 800 or w.condition in ("Thunderstorm", "Snow")


def _is_hot(w: WeatherData) -> bool:
    return w.temperature_c >= 35


def _is_cold(w: WeatherData) -> bool:
    return w.temperature_c <= 5


def _is_rainy(w: WeatherData) -> bool:
    return w.condition_code in range(200, 622)


def get_recommendations(w: WeatherData, language: str = "en") -> dict:  # type: ignore[type-arg]
    """Return weather-aware venue recommendations and health tips."""

    if _is_rainy(w) or _is_bad_weather(w):
        venue_kinds = ["museum", "gallery", "indoor_bazaar", "restaurant", "virtual_tour"]
        activity_tip_en = (
            f"It's {w.description} outside — great time for indoor heritage sites and museums."
        )
        avoid_tip_en: str | None = "Avoid exposed archaeological sites and open-air bazaars."
    elif _is_hot(w):
        venue_kinds = ["museum", "gallery", "mosque", "mausoleum", "restaurant"]
        activity_tip_en = (
            f"It's {w.temperature_c}°C — visit shaded mosques, mausoleums and"
            " museums during midday."
        )
        avoid_tip_en = "Avoid outdoor walking tours between 11:00-15:00."
    elif _is_cold(w):
        venue_kinds = ["museum", "gallery", "indoor_bazaar", "restaurant", "caravanserai"]
        activity_tip_en = f"It's {w.temperature_c}°C — warm indoor sites are ideal."
        avoid_tip_en = "Dress in layers for outdoor sites."
    else:
        venue_kinds = ["monument", "archaeological_site", "mosque", "park", "bazaar", "city_walk"]
        activity_tip_en = (
            f"Perfect {w.description} weather — ideal for outdoor heritage exploration!"
        )
        avoid_tip_en = None

    # Health tips
    health_tips: list[str] = []
    if w.temperature_c >= 30:
        health_tips.append("Drink at least 2L of water per hour outdoors.")
    if w.temperature_c >= 38:
        health_tips.append("Extreme heat alert — limit outdoor exposure, seek shade frequently.")
    if _is_rainy(w):
        health_tips.append("Carry an umbrella — some heritage sites have slippery stone surfaces.")
    if w.humidity_pct >= 80:
        health_tips.append("High humidity — light cotton clothing recommended.")

    result: dict = {  # type: ignore[type-arg]
        "condition": w.condition,
        "temperature_c": w.temperature_c,
        "description": w.description,
        "recommended_venue_kinds": venue_kinds,
        "activity_tip": activity_tip_en,
        "health_tips": health_tips,
    }
    if avoid_tip_en:
        result["avoid_tip"] = avoid_tip_en
    return result
