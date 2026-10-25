"""Somaliland vs Somalia labelling along the former British/Italian Somaliland border."""
import pytest

from somaliland_hazards import naming, sample
from somaliland_hazards.sources import earthquakes, gdacs

# (name, lat, lon) — inside former British Somaliland
SOMALILAND = [
    ("Hargeisa", 9.560, 44.065), ("Berbera", 10.440, 45.014), ("Burao", 9.522, 45.534),
    ("Borama", 9.936, 43.183), ("Zeila", 11.353, 43.473), ("Gabiley", 9.700, 43.633),
    ("Erigavo", 10.616, 47.368), ("Las Anod", 8.477, 47.360), ("Buhodle", 8.240, 46.330),
    ("Taleex", 9.150, 48.420), ("Dhahar", 9.770, 48.850), ("Las Qoray", 11.167, 48.200),
    ("Gulf of Aden off Berbera", 10.900, 45.000),
]
# outside it — former Italian Somaliland (Somalia), Ethiopia, Djibouti
SOMALIA_OR_OTHER = [
    ("Bosaso", 11.284, 49.182), ("Garowe", 8.405, 48.482), ("Galkayo", 6.769, 47.431),
    ("Mogadishu", 2.047, 45.318), ("Qardho", 9.500, 49.083), ("Coast east of 49E (Puntland)", 10.70, 49.30),
    ("Sea north of Bosaso", 11.60, 49.30), ("Jijiga (Ethiopia)", 9.350, 42.800),
    ("Djibouti city", 11.588, 43.145), ("Dhagahbur (Ethiopia)", 8.220, 43.560),
]


@pytest.mark.parametrize("name,lat,lon", SOMALILAND)
def test_inside(name, lat, lon):
    assert naming.in_somaliland(lat, lon), name


@pytest.mark.parametrize("name,lat,lon", SOMALIA_OR_OTHER)
def test_outside(name, lat, lon):
    assert not naming.in_somaliland(lat, lon), name


def test_text_by_point():
    assert naming.fix_text("Flood in Somalia", 9.56, 44.07) == "Flood in Somaliland"
    assert naming.fix_text("Flood in Somalia", 8.40, 48.48) == "Flood in Somalia"      # Garowe
    assert naming.fix_text("SOMALIA", 10.44, 45.01) == "SOMALILAND"
    assert naming.fix_text("Somalia, Ethiopia", 9.5, 45.0) == "Somaliland, Ethiopia"
    assert naming.fix_text("Somaliland", 9.5, 45.0) == "Somaliland"                     # unchanged
    assert naming.fix_text("Ethiopia", 9.5, 45.0) == "Ethiopia"


def test_text_by_town():
    # USGS style: the country describes the named town, not the point
    assert naming.fix_text("35 km N of Berbera, Somalia", 10.75, 45.0) == "35 km N of Berbera, Somaliland"
    assert naming.fix_text("60 km W of Bosaso, Somalia", 11.2, 48.6) == "60 km W of Bosaso, Somalia"


def test_feeds_apply_naming():
    ev = {e["properties"]["eventid"]: e["properties"] for e in gdacs.parse(sample.GDACS_RESPONSE)}
    assert ev[1102999]["name"] == "Flood in Somaliland"          # point near Burao
    assert ev[1102999]["country"] == "Somaliland"
    assert ev[1001234]["country"] == "Somalia, Yemen"             # cyclone point off Puntland
    q = earthquakes.parse_usgs({"features": [{"geometry": {"coordinates": [45.1, 10.8, 10]},
        "properties": {"mag": 4.0, "place": "40 km NNE of Berbera, Somalia", "time": 0, "url": ""}}]})
    assert q[0]["properties"]["place"] == "40 km NNE of Berbera, Somaliland"


def test_custom_boundary_used_before_fetch(tmp_path, monkeypatch):
    from somaliland_hazards import pipeline
    box = {"type": "Polygon", "coordinates": [[[40, 0], [41, 0], [41, 1], [40, 1], [40, 0]]]}
    f = tmp_path / "b.geojson"
    f.write_text(__import__("json").dumps(box))
    seen = {}
    def fake_fetch(key):
        seen["hargeisa_inside"] = naming.in_somaliland(9.56, 44.07)
        raise SystemExit
    monkeypatch.setattr(pipeline, "fetch_all", fake_fetch)
    try:
        pipeline.run(tmp_path, boundary_path=str(f))
    except SystemExit:
        pass
    finally:
        naming._ring = naming.SOMALILAND_RING
    assert seen["hargeisa_inside"] is False   # custom box was active during fetch
