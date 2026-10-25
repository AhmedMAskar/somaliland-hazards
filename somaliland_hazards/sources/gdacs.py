"""GDACS multi-hazard alerts (cyclones, floods, earthquakes, wildfires, drought, volcanoes).

No API key. Docs: https://www.gdacs.org/floodmerge/data_v2.aspx
"""
from datetime import datetime, timedelta, timezone
import logging

from .. import config, geo, naming
from ..http import get

log = logging.getLogger(__name__)

BASE = "https://www.gdacs.org/gdacsapi/api"
EVENT_TYPES = "TC;FL;EQ;WF;DR;VO"
TYPE_NAMES = {"TC": "Tropical cyclone", "FL": "Flood", "EQ": "Earthquake",
              "WF": "Wildfire", "DR": "Drought", "VO": "Volcano"}


def fetch(days=config.GDACS_LOOKBACK_DAYS, radius_km=config.GDACS_RADIUS_KM):
    """Return GeoJSON point features for GDACS events near Somaliland."""
    today = datetime.now(timezone.utc).date()
    params = {
        "eventlist": EVENT_TYPES,
        "fromdate": (today - timedelta(days=days)).isoformat(),
        "todate": today.isoformat(),
        "alertlevel": "green;orange;red",
    }
    data = get(f"{BASE}/events/geteventlist/SEARCH", params=params).json()
    return parse(data, radius_km)


def parse(data, radius_km=config.GDACS_RADIUS_KM):
    out = []
    for f in data.get("features", []):
        geom = f.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        lon, lat = geom["coordinates"][:2]
        p = f.get("properties", {})
        countries = (p.get("country") or "") + " " + " ".join(
            c.get("countryname", "") for c in p.get("affectedcountries") or [])
        dist = geo.km_to_somaliland(lat, lon)
        if dist > radius_km and "Somali" not in countries:
            continue
        etype = p.get("eventtype", "")
        url = p.get("url") or {}
        sev = p.get("severitydata") or {}
        out.append(geo.point_feature(lon, lat, {
            "source": "GDACS",
            "hazard": TYPE_NAMES.get(etype, etype),
            "eventtype": etype,
            "eventid": p.get("eventid"),
            "episodeid": p.get("episodeid"),
            "name": naming.fix_text(p.get("name") or p.get("eventname"), lat, lon),
            "alertlevel": (p.get("alertlevel") or "").capitalize(),
            "severity": naming.fix_text(sev.get("severitytext"), lat, lon),
            "from": p.get("fromdate"),
            "to": p.get("todate"),
            "country": naming.fix_text(p.get("country"), lat, lon),
            "km_to_somaliland": round(dist),
            "report_url": url.get("report"),
            "geometry_url": url.get("geometry"),
        }))
    log.info("GDACS: %d events near Somaliland", len(out))
    return out


def fetch_geometry(feature):
    """Optional: impact polygons (cyclone cone, flood extent) for one event."""
    url = feature["properties"].get("geometry_url")
    if not url:
        return None
    try:
        return get(url).json()
    except Exception as e:  # noqa: BLE001
        log.warning("GDACS geometry failed for %s: %s", feature["properties"].get("eventid"), e)
        return None
