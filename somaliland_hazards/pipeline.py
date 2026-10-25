"""Fetch every source, build alerts, write GeoJSON/JSON outputs and the map."""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from . import alerts as alerts_mod
from . import geo, mapper, naming
from .sources import earthquakes, firms, gdacs, jtwc, openmeteo

log = logging.getLogger(__name__)


def _safe(name, fn, status, default):
    try:
        result = fn()
        status[name] = "ok"
        return result
    except Exception as e:  # noqa: BLE001 - one bad feed must not kill the run
        log.warning("%s failed: %s", name, e)
        status[name] = f"error: {e}"
        return default


def fetch_all(firms_key=None):
    status = {}
    data = {
        "storms": _safe("JTWC", jtwc.fetch, status, []),
        "gdacs": _safe("GDACS", gdacs.fetch, status, []),
        "quakes": _safe("Earthquakes", earthquakes.fetch, status, []),
        "forecasts": _safe("Open-Meteo", openmeteo.fetch_forecast, status, {}),
    }
    if firms_key:
        data["fires"] = _safe("FIRMS", lambda: firms.fetch(firms_key), status, [])
    else:
        data["fires"] = []
        status["FIRMS"] = "skipped (no key)"
    return data, status


def write_outputs(data, status, out_dir="output", boundary_path=None, sample=False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    alerts = alerts_mod.build(data["storms"], data["quakes"], data["forecasts"],
                              data["fires"], data["gdacs"])

    storm_feats = [f for s in data["storms"] for f in jtwc.to_features(s)]
    files = {
        "cyclones.geojson": geo.feature_collection(storm_feats),
        "gdacs.geojson": geo.feature_collection(data["gdacs"]),
        "earthquakes.geojson": geo.feature_collection(data["quakes"]),
        "fires.geojson": geo.feature_collection(data["fires"]),
        "forecasts.json": data["forecasts"],
        "alerts.json": {
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sample_data": sample,
            "feed_status": status,
            "alerts": alerts,
        },
    }
    for name, obj in files.items():
        (out / name).write_text(json.dumps(obj, indent=2, default=str))

    boundary = json.loads(Path(boundary_path).read_text()) if boundary_path else None
    if boundary:
        naming.set_boundary(boundary)
    map_path = mapper.build_map(data["storms"], data["quakes"], data["forecasts"],
                                data["fires"], data["gdacs"], alerts, status,
                                out_path=str(out / "map.html"), boundary=boundary,
                                sample=sample)
    return alerts, map_path


def run(out_dir="output", firms_key=None, boundary_path=None):
    firms_key = firms_key or os.environ.get("FIRMS_MAP_KEY")
    if boundary_path:  # load before fetching so Somaliland labels use it
        naming.set_boundary(json.loads(Path(boundary_path).read_text()))
    data, status = fetch_all(firms_key)
    alerts, map_path = write_outputs(data, status, out_dir, boundary_path)
    return alerts, map_path, status
