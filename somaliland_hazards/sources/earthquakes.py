"""Earthquakes from USGS and EMSC (no API key). Merged and de-duplicated."""
from datetime import datetime, timedelta, timezone
import logging

from .. import config, geo, naming
from ..http import get

log = logging.getLogger(__name__)

USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query"
EMSC = "https://www.seismicportal.eu/fdsnws/event/1/query"

# Earthquake box: Somaliland + Gulf of Aden rift + Afar triangle.
EQ_BBOX = (40.0, 6.0, 52.0, 15.0)


def _start(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


def fetch_usgs(days=config.EQ_LOOKBACK_DAYS, minmag=config.EQ_MIN_MAG_FETCH):
    w, s, e, n = EQ_BBOX
    params = dict(format="geojson", starttime=_start(days), minmagnitude=minmag,
                  minlatitude=s, maxlatitude=n, minlongitude=w, maxlongitude=e,
                  orderby="time")
    return parse_usgs(get(USGS, params=params).json())


def parse_usgs(data):
    out = []
    for f in data.get("features", []):
        lon, lat, depth = (f["geometry"]["coordinates"] + [None])[:3]
        p = f["properties"]
        out.append(_eq(lon, lat, depth, p.get("mag"), p.get("time"), p.get("place"),
                       "USGS", p.get("url")))
    return out


def fetch_emsc(days=config.EQ_LOOKBACK_DAYS, minmag=config.EQ_MIN_MAG_FETCH):
    w, s, e, n = EQ_BBOX
    params = dict(format="json", start=_start(days), minmag=minmag,
                  minlat=s, maxlat=n, minlon=w, maxlon=e, limit=500)
    r = get(EMSC, params=params)
    if r.status_code == 204 or not r.content:
        return []
    return parse_emsc(r.json())


def parse_emsc(data):
    out = []
    for f in data.get("features", []):
        p = f["properties"]
        lon, lat = p.get("lon"), p.get("lat")
        if lon is None:
            lon, lat = f["geometry"]["coordinates"][:2]
        t = p.get("time")
        ms = None
        if t:
            ms = int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() * 1000)
        uid = p.get("unid")
        out.append(_eq(lon, lat, p.get("depth"), p.get("mag"), ms, p.get("flynn_region"),
                       "EMSC", f"https://www.seismicportal.eu/eventdetails.html?unid={uid}" if uid else None))
    return out


def _eq(lon, lat, depth, mag, time_ms, place, source, url):
    when = (datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).isoformat()
            if time_ms else None)
    near, km = geo.nearest(lat, lon)
    return geo.point_feature(lon, lat, {
        "source": source, "hazard": "Earthquake",
        "mag": round(mag, 1) if mag is not None else None,
        "depth_km": round(depth, 1) if depth is not None else None,
        "time": when, "time_ms": time_ms, "place": naming.fix_text(place, lat, lon),
        "nearest_city": near, "km_to_city": round(km), "url": url,
    })


def merge(*lists, km=50, seconds=90):
    """Combine sources; treat events within `km` and `seconds` as the same quake.
    USGS is preferred when both report it."""
    order = {"USGS": 0, "EMSC": 1}
    allq = sorted((q for lst in lists for q in lst),
                  key=lambda q: order.get(q["properties"]["source"], 9))
    kept = []
    for q in allq:
        lon, lat = q["geometry"]["coordinates"]
        t = q["properties"]["time_ms"] or 0
        dup = False
        for k in kept:
            klon, klat = k["geometry"]["coordinates"]
            kt = k["properties"]["time_ms"] or 0
            if abs(t - kt) <= seconds * 1000 and geo.haversine_km(lat, lon, klat, klon) <= km:
                k["properties"]["also_reported_by"] = q["properties"]["source"]
                dup = True
                break
        if not dup:
            kept.append(q)
    kept.sort(key=lambda q: q["properties"]["time_ms"] or 0, reverse=True)
    return kept


def fetch():
    results = []
    for name, fn in (("USGS", fetch_usgs), ("EMSC", fetch_emsc)):
        try:
            results.append(fn())
        except Exception as e:  # noqa: BLE001
            log.warning("%s earthquakes failed: %s", name, e)
    if not results:
        raise RuntimeError("both USGS and EMSC unreachable")
    quakes = merge(*results)
    log.info("Earthquakes: %d after merge", len(quakes))
    return quakes
