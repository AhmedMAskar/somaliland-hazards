"""Joint Typhoon Warning Center (JTWC) tropical cyclone warnings.

JTWC posts an RSS feed with links to plain-text warnings. North Indian Ocean
warnings use the "io" prefix (e.g. io0326web.txt = storm 03, 2026). We parse
current and forecast positions plus winds from the text.

Note: JTWC says its products are intended for U.S. government use. For a public
app, show IMD (RSMC New Delhi) as the official source for this basin.
"""
import logging
import re
import xml.etree.ElementTree as ET

from .. import config, geo
from ..http import get

log = logging.getLogger(__name__)

RSS_URL = "https://www.metoc.navy.mil/jtwc/rss/jtwc.rss"
TEXT_LINK = re.compile(r"https?://[^\s\"'<>]*/products/(io|sh)\d{4}web\.txt", re.I)

_POS = re.compile(
    r"(\d{6})Z\s*-{2,3}\s*(?:NEAR\s+)?(\d{1,2}\.\d)\s*([NS])\s+(\d{1,3}\.\d)\s*([EW])", re.I)
_WIND = re.compile(r"MAX(?:IMUM)?\s+SUSTAINED\s+WINDS\s*-\s*(\d{2,3})\s*KT", re.I)
_TAU = re.compile(r"(\d{2,3})\s+HRS?,\s*VALID\s+AT", re.I)
_NAME = re.compile(r"(TROPICAL\s+(?:CYCLONE|STORM|DEPRESSION)|CYCLONE|TYPHOON)\s+(\d{2}[A-Z])"
                   r"(?:\s+\(([A-Z\-]+)\))?", re.I)
_WARN_NO = re.compile(r"WARNING\s+NR\s+(\d+)", re.I)


def category_from_kt(kt):
    """IMD-style North Indian Ocean classes from (approx.) knots."""
    if kt is None:
        return "Unknown"
    if kt < 28:
        return "Depression"
    if kt < 34:
        return "Deep depression"
    if kt < 48:
        return "Cyclonic storm"
    if kt < 64:
        return "Severe cyclonic storm"
    if kt < 90:
        return "Very severe cyclonic storm"
    if kt < 120:
        return "Extremely severe cyclonic storm"
    return "Super cyclonic storm"


def warning_links(rss_text):
    links = set(m.group(0) for m in TEXT_LINK.finditer(rss_text))
    try:  # also scan <link> tags explicitly
        for el in ET.fromstring(rss_text).iter():
            if el.text and TEXT_LINK.search(el.text):
                links.add(TEXT_LINK.search(el.text).group(0))
    except ET.ParseError:
        pass
    return sorted(links)


def parse_warning(text, url=""):
    """Parse one JTWC warning text into a storm dict, or None."""
    name_m = _NAME.search(text)
    storm_id = name_m.group(2).upper() if name_m else None
    storm_name = name_m.group(3) if name_m and name_m.group(3) else None
    warn = _WARN_NO.search(text)

    # Split on each position line; associate the next wind value and tau label.
    points = []
    matches = list(_POS.finditer(text))
    for i, m in enumerate(matches):
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        seg_start = matches[i - 1].end() if i > 0 else 0
        after = text[m.end():seg_end]
        before = text[seg_start:m.start()]
        lat = float(m.group(2)) * (1 if m.group(3).upper() == "N" else -1)
        lon = float(m.group(4)) * (1 if m.group(5).upper() == "E" else -1)
        wind = _WIND.search(after)
        tau = _TAU.findall(before)
        points.append({
            "dtg": m.group(1) + "Z",
            "lat": lat, "lon": lon,
            "tau_h": int(tau[-1]) if tau else 0,
            "wind_kt": int(wind.group(1)) if wind else None,
        })

    # Drop duplicates (JTWC repeats the current position in a remarks section).
    seen, track = set(), []
    for p in points:
        key = (p["dtg"], p["lat"], p["lon"])
        if key not in seen:
            seen.add(key)
            track.append(p)
    if not track:
        return None
    # First point is the current (tau 0) position.
    track[0]["tau_h"] = 0
    current = track[0]
    min_km = min(geo.km_to_somaliland(p["lat"], p["lon"]) for p in track)
    return {
        "source": "JTWC",
        "storm_id": storm_id,
        "name": storm_name,
        "warning_no": int(warn.group(1)) if warn else None,
        "basin": "North Indian Ocean" if storm_id and storm_id.endswith(("A", "B")) else "Indian Ocean",
        "current": current,
        "category": category_from_kt(current["wind_kt"]),
        "track": track,
        "min_km_to_somaliland": round(min_km),
        "url": url,
    }


def to_features(storm):
    """GeoJSON: forecast track line + one point per position."""
    feats = []
    coords = [[p["lon"], p["lat"]] for p in storm["track"]]
    base = {k: storm[k] for k in ("source", "storm_id", "name", "category",
                                  "min_km_to_somaliland", "url", "warning_no")}
    if len(coords) > 1:
        feats.append({"type": "Feature",
                      "geometry": {"type": "LineString", "coordinates": coords},
                      "properties": {**base, "kind": "forecast_track"}})
    for p in storm["track"]:
        feats.append(geo.point_feature(p["lon"], p["lat"], {
            **base, "kind": "position", "hazard": "Tropical cyclone",
            "dtg": p["dtg"], "tau_h": p["tau_h"], "wind_kt": p["wind_kt"],
            "point_category": category_from_kt(p["wind_kt"]),
        }))
    return feats


def fetch():
    """Return a list of storm dicts in the watch box (usually empty)."""
    rss = get(RSS_URL).text
    storms = []
    for link in warning_links(rss):
        try:
            storm = parse_warning(get(link).text, link)
        except Exception as e:  # noqa: BLE001
            log.warning("JTWC warning %s failed: %s", link, e)
            continue
        if storm and any(geo.in_bbox(p["lat"], p["lon"], config.WATCH_BBOX) for p in storm["track"]):
            storms.append(storm)
    log.info("JTWC: %d active storms in watch area", len(storms))
    return storms
