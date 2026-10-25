"""Small geometry helpers (no GIS dependencies needed)."""
import math

from . import config


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def in_bbox(lat, lon, bbox):
    w, s, e, n = bbox
    return s <= lat <= n and w <= lon <= e


def nearest(lat, lon, places=None):
    """Return (name, km) of the nearest place."""
    places = places or config.CITIES
    best = min(places.items(), key=lambda kv: haversine_km(lat, lon, *kv[1]))
    return best[0], haversine_km(lat, lon, *best[1])


def km_to_somaliland(lat, lon):
    """Distance to the nearest city or coastal point; 0 if inside the land box."""
    if in_bbox(lat, lon, config.LAND_BBOX):
        return 0.0
    pts = {**config.CITIES, **config.COAST_POINTS}
    return nearest(lat, lon, pts)[1]


def point_feature(lon, lat, props):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props,
    }


def feature_collection(features):
    return {"type": "FeatureCollection", "features": list(features)}
