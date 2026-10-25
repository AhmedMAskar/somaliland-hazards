"""Parser and alert tests against sample payloads (no network)."""
from somaliland_hazards import alerts, geo, pipeline, sample
from somaliland_hazards.sources import earthquakes, firms, gdacs, jtwc


def test_jtwc_parse_track():
    s = jtwc.parse_warning(sample.JTWC_WARNING)
    assert s["storm_id"] == "03A" and s["name"] == "THREE" and s["warning_no"] == 6
    taus = [p["tau_h"] for p in s["track"]]
    assert taus == [0, 12, 24, 36, 48, 72]          # remarks position not duplicated
    assert s["current"]["wind_kt"] == 55 and s["current"]["lon"] == 54.2
    assert s["category"] == "Severe cyclonic storm"
    assert s["min_km_to_somaliland"] == 0           # 72 h point is over land


def test_jtwc_links():
    links = jtwc.warning_links(sample.JTWC_RSS)
    assert links == ["https://www.metoc.navy.mil/jtwc/products/io0326web.txt"]


def test_gdacs_filters_far_events():
    ev = gdacs.parse(sample.GDACS_RESPONSE)
    names = [e["properties"]["name"] for e in ev]
    assert "Far-away typhoon" not in names and len(ev) == 2


def test_quake_merge_dedupes_usgs_emsc():
    q = earthquakes.merge(earthquakes.parse_usgs(sample.USGS_RESPONSE),
                          earthquakes.parse_emsc(sample.EMSC_RESPONSE))
    assert len(q) == 3
    big = [x for x in q if x["properties"]["mag"] == 4.8][0]
    assert big["properties"]["source"] == "USGS"
    assert big["properties"]["also_reported_by"] == "EMSC"


def test_firms_csv():
    f = firms.parse_csv(sample.FIRMS_CSV)
    assert len(f) == 6 and f[0]["properties"]["nearest_city"] == "Hargeisa"


def test_alerts_and_outputs(tmp_path):
    data, status = sample.sample_data()
    found, path = pipeline.write_outputs(data, status, tmp_path, sample=True)
    hazards = {a["hazard"] for a in found}
    assert {"Tropical cyclone", "Earthquake", "Heavy rain / flash flood", "Wildfire"} <= hazards
    assert found[0]["level"] == "Warning"            # sorted by severity
    for name in ("map.html", "alerts.json", "cyclones.geojson", "earthquakes.geojson"):
        assert (tmp_path / name).exists()


def test_geo():
    assert round(geo.haversine_km(9.56, 44.065, 10.4396, 45.0143)) in range(140, 150)
    assert geo.km_to_somaliland(9.56, 44.065) == 0
