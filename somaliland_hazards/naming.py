"""Country naming: label places in Somaliland as "Somaliland", not "Somalia".

Data feeds (GDACS, USGS, EMSC) report everything in the Horn as "Somalia". This
module relabels a location as Somaliland when it falls inside the former British
Somaliland Protectorate, and leaves it as Somalia otherwise.

Eastern border with former Italian Somaliland (Anglo-Italian protocol, 1894):
    the 49°E meridian from the coast south to 9°N,
    then the 9°N parallel west to 48°E,
    then the 48°E meridian south to 8°N (Ethiopian border).
The Ethiopia and Djibouti sides below are approximate (they only matter if a feed
calls a point there "Somalia"). The polygon extends offshore to about 12°N so
Gulf of Aden events off the Somaliland coast are labelled too.

To use an exact boundary file instead, pass its GeoJSON to set_boundary().
"""
import re

# (lon, lat) vertices, closed ring.
SOMALILAND_RING = [
    (43.30, 11.50),   # Djibouti border at the coast (Loyada)
    (43.60, 11.90),   # offshore, west end
    (49.00, 12.00),   # offshore, east end
    (49.00, 9.00),    # 49°E meridian down to 9°N   (British/Italian line)
    (48.00, 9.00),    # 9°N parallel west to 48°E   (British/Italian line)
    (48.00, 8.00),    # 48°E meridian down to 8°N   (British/Italian line)
    (47.00, 8.00),    # Ethiopia border (approx.)
    (46.00, 8.30),
    (44.00, 9.00),
    (43.33, 9.55),    # near Wajaale / Tog Wajaale
    (42.85, 10.00),
    (42.92, 10.98),   # Djibouti / Ethiopia tripoint (approx.)
    (43.30, 11.50),
]

# Towns inside former British Somaliland, used when a feed names a town
# ("35 km N of Berbera, Somalia"). Lower-case, several spellings.
SOMALILAND_TOWNS = {
    "hargeisa", "hargeysa", "berbera", "burao", "burco", "borama", "boorama",
    "erigavo", "ceerigaabo", "las anod", "laascaanood", "gabiley", "gebiley",
    "zeila", "saylac", "sheikh", "sheekh", "oodweyne", "odweyne", "lughaya",
    "lughaye", "maydh", "mait", "las qoray", "laasqoray", "baki", "buhodle",
    "buuhoodle", "ainabo", "caynabo", "badhan", "dhahar", "taleex", "taleh",
    "el afweyn", "ceel afweyn", "garadag", "hudun", "xudun", "wajaale",
    "tog wajaale", "kalabaydh", "salahlee", "balli gubadle", "dilla",
    "berbera port", "erigabo", "las khorey",
}

_ring = SOMALILAND_RING
_SOMALIA = re.compile(r"\bSomalia\b", re.IGNORECASE)
_OF_TOWN = re.compile(r"\bof\s+([^,]+),\s*Somalia\b", re.IGNORECASE)


def set_boundary(geojson):
    """Use the outer ring of a (Multi)Polygon GeoJSON as the Somaliland boundary."""
    global _ring
    geom = geojson
    if geom.get("type") == "FeatureCollection":
        geom = geom["features"][0]["geometry"]
    elif geom.get("type") == "Feature":
        geom = geom["geometry"]
    if geom["type"] == "Polygon":
        _ring = [tuple(p[:2]) for p in geom["coordinates"][0]]
    elif geom["type"] == "MultiPolygon":
        biggest = max(geom["coordinates"], key=lambda poly: len(poly[0]))
        _ring = [tuple(p[:2]) for p in biggest[0]]


def in_somaliland(lat, lon, ring=None):
    """Ray-casting point-in-polygon test."""
    ring = ring or _ring
    inside = False
    n = len(ring)
    for i in range(n - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > lat) != (y2 > lat):
            x_cross = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x_cross:
                inside = not inside
    return inside


def _swap(text):
    def rep(m):
        w = m.group(0)
        if w.isupper():
            return "SOMALILAND"
        if w.islower():
            return "somaliland"
        return "Somaliland"
    return _SOMALIA.sub(rep, text)


def fix_text(text, lat=None, lon=None):
    """Replace "Somalia" with "Somaliland" in `text` when it refers to Somaliland.

    - "X km N of <town>, Somalia": decided by the town (the country there
      describes the town, not the event point).
    - anything else: decided by whether (lat, lon) is inside Somaliland.
    """
    if not text or not _SOMALIA.search(text):
        return text
    m = _OF_TOWN.search(text)
    if m:
        town = m.group(1).strip().lower()
        return _swap(text) if town in SOMALILAND_TOWNS else text
    if lat is not None and lon is not None and in_somaliland(lat, lon):
        return _swap(text)
    return text


def country_for(lat, lon):
    return "Somaliland" if in_somaliland(lat, lon) else None
