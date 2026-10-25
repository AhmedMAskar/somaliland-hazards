"""Turn fetched data into ranked alerts (Warning > Watch > Info)."""
from . import config, geo

RANK = {"Warning": 0, "Watch": 1, "Info": 2}


def _alert(level, hazard, title, detail, source, lat=None, lon=None):
    return {"level": level, "hazard": hazard, "title": title, "detail": detail,
            "source": source, "lat": lat, "lon": lon}


def cyclone_alerts(storms):
    out = []
    for s in storms:
        km = s["min_km_to_somaliland"]
        if km > config.CYCLONE_WATCH_KM:
            continue
        level = "Warning" if km <= config.CYCLONE_WARNING_KM else "Watch"
        cur = s["current"]
        label = f"{s['storm_id'] or 'Storm'}" + (f" ({s['name']})" if s["name"] else "")
        closest = min(s["track"], key=lambda p: geo.km_to_somaliland(p["lat"], p["lon"]))
        out.append(_alert(level, "Tropical cyclone",
                          f"{s['category']} {label}",
                          f"Now {cur['wind_kt']} kt at {cur['lat']}, {cur['lon']}. "
                          + (f"Forecast track reaches Somaliland at +{closest['tau_h']} h."
                             if km == 0 else
                             f"Track comes within {km} km of Somaliland (+{closest['tau_h']} h)."),
                          "JTWC", cur["lat"], cur["lon"]))
    return out


def earthquake_alerts(quakes):
    out = []
    for q in quakes:
        p = q["properties"]
        if p["mag"] is None or p["mag"] < config.EQ_ALERT_MAG:
            continue
        lon, lat = q["geometry"]["coordinates"]
        level = "Warning" if p["mag"] >= config.EQ_WARNING_MAG else "Watch"
        out.append(_alert(level, "Earthquake", f"M{p['mag']} earthquake",
                          f"{p['place'] or ''} — {p['km_to_city']} km from {p['nearest_city']}, "
                          f"depth {p['depth_km']} km, {p['time'][:16].replace('T', ' ')} UTC",
                          p["source"], lat, lon))
    return out


def weather_alerts(forecasts):
    out = []
    for city, days in forecasts.items():
        lat, lon = config.CITIES.get(city, (None, None))
        rain = max(days, key=lambda d: d["rain_mm"] or 0, default=None)
        if rain and (rain["rain_mm"] or 0) >= config.RAIN_WATCH_MM:
            lvl = "Warning" if rain["rain_mm"] >= config.RAIN_WARNING_MM else "Watch"
            out.append(_alert(lvl, "Heavy rain / flash flood", f"Heavy rain — {city}",
                              f"{rain['rain_mm']:.0f} mm forecast on {rain['date']}. "
                              "Watch toggas (seasonal riverbeds) for flash floods.",
                              "Open-Meteo", lat, lon))
        gust = max(days, key=lambda d: d["gust_kmh"] or 0, default=None)
        if gust and (gust["gust_kmh"] or 0) >= config.GUST_WATCH_KMH:
            lvl = "Warning" if gust["gust_kmh"] >= config.GUST_WARNING_KMH else "Watch"
            out.append(_alert(lvl, "High wind / dust", f"Strong winds — {city}",
                              f"Gusts to {gust['gust_kmh']:.0f} km/h on {gust['date']}.",
                              "Open-Meteo", lat, lon))
        hot = max(days, key=lambda d: d["tmax"] or -99, default=None)
        if hot and (hot["tmax"] or -99) >= config.HEAT_WATCH_C:
            lvl = "Warning" if hot["tmax"] >= config.HEAT_WARNING_C else "Watch"
            out.append(_alert(lvl, "Extreme heat", f"Extreme heat — {city}",
                              f"High of {hot['tmax']:.0f} °C on {hot['date']}.",
                              "Open-Meteo", lat, lon))
    return out


def fire_alerts(fires):
    inside = [f for f in fires
              if geo.in_bbox(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0],
                             config.LAND_BBOX)]
    n = len(inside)
    if n < config.FIRE_WATCH_COUNT:
        return []
    lvl = "Warning" if n >= config.FIRE_WARNING_COUNT else "Watch"
    by_city = {}
    for f in inside:
        c = f["properties"]["nearest_city"]
        by_city[c] = by_city.get(c, 0) + 1
    top = ", ".join(f"{c} ({k})" for c, k in sorted(by_city.items(), key=lambda x: -x[1])[:3])
    return [_alert(lvl, "Wildfire", f"{n} active fire hotspots",
                   f"Most near: {top}.", "NASA FIRMS")]


def gdacs_alerts(events):
    out = []
    for e in events:
        p = e["properties"]
        if p["eventtype"] == "EQ":  # already covered by USGS/EMSC
            continue
        lon, lat = e["geometry"]["coordinates"]
        lvl = {"Red": "Warning", "Orange": "Watch"}.get(p["alertlevel"], "Info")
        out.append(_alert(lvl, p["hazard"], f"GDACS {p['alertlevel']}: {p['name']}",
                          f"{p['severity'] or ''} ({p['km_to_somaliland']} km away)".strip(),
                          "GDACS", lat, lon))
    return out


def build(storms, quakes, forecasts, fires, gdacs_events):
    alerts = (cyclone_alerts(storms) + earthquake_alerts(quakes) + weather_alerts(forecasts)
              + fire_alerts(fires) + gdacs_alerts(gdacs_events))
    alerts.sort(key=lambda a: (RANK[a["level"]], a["hazard"]))
    return alerts
