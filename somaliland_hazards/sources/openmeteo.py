"""7-day city forecasts and river-discharge (GloFAS) from Open-Meteo. No API key."""
import logging

from .. import config
from ..http import get

log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"
DAILY = ("temperature_2m_max,temperature_2m_min,precipitation_sum,"
         "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,weather_code")

# WMO weather codes -> short text
WMO = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog",
       48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
       61: "Light rain", 63: "Rain", 65: "Heavy rain", 80: "Showers",
       81: "Heavy showers", 82: "Violent showers", 95: "Thunderstorm",
       96: "Thunderstorm, hail", 99: "Severe thunderstorm"}


def _multi(url, params, cities):
    names = list(cities)
    params = {**params,
              "latitude": ",".join(str(cities[n][0]) for n in names),
              "longitude": ",".join(str(cities[n][1]) for n in names)}
    data = get(url, params=params).json()
    if isinstance(data, dict):  # single location returns a dict
        data = [data]
    return dict(zip(names, data))


def fetch_forecast(cities=None):
    cities = cities or config.CITIES
    raw = _multi(FORECAST_URL, {"daily": DAILY, "timezone": config.TIMEZONE,
                                "forecast_days": config.FORECAST_DAYS}, cities)
    return parse_forecast(raw)


def parse_forecast(raw):
    out = {}
    for city, d in raw.items():
        daily = d.get("daily", {})
        days = []
        for i, date in enumerate(daily.get("time", [])):
            def v(k):
                arr = daily.get(k) or []
                return arr[i] if i < len(arr) else None
            code = v("weather_code")
            days.append({
                "date": date, "tmax": v("temperature_2m_max"), "tmin": v("temperature_2m_min"),
                "rain_mm": v("precipitation_sum"), "rain_prob": v("precipitation_probability_max"),
                "wind_kmh": v("wind_speed_10m_max"), "gust_kmh": v("wind_gusts_10m_max"),
                "code": code, "summary": WMO.get(code, "—"),
            })
        out[city] = days
    log.info("Open-Meteo: forecasts for %d cities", len(out))
    return out


def fetch_river_discharge(cities=None):
    """GloFAS river discharge near each city. Most Somaliland rivers (togga) are
    seasonal, so values are often near zero; spikes still flag flash-flood risk."""
    cities = cities or config.CITIES
    raw = _multi(FLOOD_URL, {"daily": "river_discharge,river_discharge_max",
                             "forecast_days": 30}, cities)
    out = {}
    for city, d in raw.items():
        daily = d.get("daily", {})
        out[city] = [{"date": t, "discharge": q, "discharge_max": qm}
                     for t, q, qm in zip(daily.get("time", []),
                                         daily.get("river_discharge", []),
                                         daily.get("river_discharge_max", []))]
    return out
