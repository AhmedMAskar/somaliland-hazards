"""NASA FIRMS active-fire hotspots (VIIRS + MODIS).

Needs a free MAP_KEY: https://firms.modaps.eosdis.nasa.gov/api/map_key/
Set env var FIRMS_MAP_KEY or pass --firms-key.
"""
import csv
import io
import logging

from .. import config, geo
from ..http import get

log = logging.getLogger(__name__)

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
PRODUCTS = ("VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT")


def fetch(map_key, days=config.FIRMS_LOOKBACK_DAYS, bbox=config.LAND_BBOX):
    if not map_key:
        log.info("FIRMS: no MAP_KEY, skipping wildfire hotspots")
        return []
    area = ",".join(str(x) for x in bbox)
    feats = []
    for prod in PRODUCTS:
        try:
            text = get(f"{BASE}/{map_key}/{prod}/{area}/{days}").text
        except Exception as e:  # noqa: BLE001
            log.warning("FIRMS %s failed: %s", prod, e)
            continue
        if text.lstrip().lower().startswith(("invalid", "error")):
            log.warning("FIRMS %s: %s", prod, text.strip()[:120])
            continue
        feats.extend(parse_csv(text, prod))
    log.info("FIRMS: %d hotspots", len(feats))
    return feats


def parse_csv(text, product=""):
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
        except (KeyError, ValueError):
            continue
        near, km = geo.nearest(lat, lon)
        out.append(geo.point_feature(lon, lat, {
            "source": "NASA FIRMS", "hazard": "Wildfire hotspot", "product": product,
            "date": row.get("acq_date"), "time_utc": row.get("acq_time"),
            "confidence": row.get("confidence"),
            "frp_mw": float(row["frp"]) if row.get("frp") else None,
            "daynight": row.get("daynight"), "nearest_city": near, "km_to_city": round(km),
        }))
    return out
