"""Offline sample payloads in each API's real response format.

Used by `python -m somaliland_hazards sample` and by the tests. The storm,
quakes and fires here are made up — they exist to exercise the parsers and map.
"""
from datetime import date, datetime, timedelta, timezone

from . import config
from .sources import earthquakes, firms, gdacs, jtwc, openmeteo

JTWC_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>JTWC</title>
<item><title>Tropical Cyclone 03A (Three) Warning #06</title>
<description><![CDATA[ <a href="https://www.metoc.navy.mil/jtwc/products/io0326web.txt">TC Warning Text</a> ]]></description>
</item></channel></rss>"""

JTWC_WARNING = """WTIO31 PGTW 191500
MSGID/GENADMIN/JOINT TYPHOON WRNCEN PEARL HARBOR HI//
SUBJ/TROPICAL CYCLONE 03A (THREE) WARNING NR 006//
RMKS/
1. TROPICAL CYCLONE 03A (THREE) WARNING NR 006
   01 ACTIVE TROPICAL CYCLONE IN NORTHIO
   MAX SUSTAINED WINDS BASED ON ONE-MINUTE AVERAGE
    ---
   WARNING POSITION:
   191200Z --- NEAR 13.1N 54.2E
     MOVEMENT PAST SIX HOURS - 265 DEGREES AT 07 KTS
     POSITION ACCURATE TO WITHIN 030 NM
   PRESENT WIND DISTRIBUTION:
   MAX SUSTAINED WINDS - 055 KT, GUSTS 070 KT
   RADIUS OF 034 KT WINDS - 060 NM NORTHEAST QUADRANT
    ---
   FORECASTS:
   12 HRS, VALID AT:
   200000Z --- 12.8N 53.0E
   MAX SUSTAINED WINDS - 060 KT, GUSTS 075 KT
    ---
   24 HRS, VALID AT:
   201200Z --- 12.4N 51.6E
   MAX SUSTAINED WINDS - 060 KT, GUSTS 075 KT
    ---
   36 HRS, VALID AT:
   210000Z --- 12.0N 50.1E
   MAX SUSTAINED WINDS - 050 KT, GUSTS 065 KT
    ---
   48 HRS, VALID AT:
   211200Z --- 11.5N 48.6E
   MAX SUSTAINED WINDS - 040 KT, GUSTS 050 KT
    ---
   EXTENDED OUTLOOK:
   72 HRS, VALID AT:
   221200Z --- 10.8N 46.2E
   MAX SUSTAINED WINDS - 030 KT, GUSTS 040 KT
   DISSIPATED AS A SIGNIFICANT TROPICAL CYCLONE OVER LAND
    ---
REMARKS:
191500Z POSITION NEAR 13.0N 53.9E.
TROPICAL CYCLONE 03A (THREE), LOCATED APPROXIMATELY 330 NM EAST OF BERBERA.
NEXT WARNINGS AT 192100Z AND 200300Z.//
"""

_today = date.today()
_now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

GDACS_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [54.2, 13.1]},
         "properties": {"eventtype": "TC", "eventid": 1001234, "episodeid": 6,
                        "name": "Tropical Cyclone THREE-26", "alertlevel": "Orange",
                        "country": "Somalia, Yemen", "fromdate": f"{_today - timedelta(days=2)}T00:00:00",
                        "todate": f"{_today}T12:00:00",
                        "severitydata": {"severity": 111, "severitytext": "Tropical Storm (maximum wind speed of 111 km/h)", "severityunit": "km/h"},
                        "url": {"report": "https://www.gdacs.org/report.aspx?eventid=1001234&eventtype=TC",
                                "geometry": "https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=TC&eventid=1001234&episodeid=6"}}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [45.6, 9.4]},
         "properties": {"eventtype": "FL", "eventid": 1102999, "episodeid": 1,
                        "name": "Flood in Somalia", "alertlevel": "Green", "country": "Somalia",
                        "fromdate": f"{_today - timedelta(days=5)}T00:00:00", "todate": f"{_today}T00:00:00",
                        "severitydata": {"severitytext": "Magnitude 0 Medium"},
                        "url": {"report": "https://www.gdacs.org/report.aspx?eventid=1102999&eventtype=FL"}}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [120.9, 14.6]},
         "properties": {"eventtype": "TC", "eventid": 9, "name": "Far-away typhoon",
                        "alertlevel": "Red", "country": "Philippines", "url": {}}},
    ],
}

USGS_RESPONSE = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [46.9, 11.9, 10.0]},
     "properties": {"mag": 4.8, "place": "Gulf of Aden", "time": _now_ms - 26 * 3600_000,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000xxxx"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [43.1, 11.5, 12.3]},
     "properties": {"mag": 3.6, "place": "Djibouti region", "time": _now_ms - 80 * 3600_000,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us6000yyyy"}},
]}


def _iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0Z")


EMSC_RESPONSE = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [46.95, 11.88, -10]},
     "properties": {"lat": 11.88, "lon": 46.95, "depth": 10, "mag": 4.7,
                    "time": _iso(_now_ms - 26 * 3600_000 + 20_000), "flynn_region": "GULF OF ADEN",
                    "unid": "20261018_0000111"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [48.2, 12.4, -10]},
     "properties": {"lat": 12.4, "lon": 48.2, "depth": 10, "mag": 3.1,
                    "time": _iso(_now_ms - 50 * 3600_000), "flynn_region": "GULF OF ADEN",
                    "unid": "20261017_0000222"}},
]}


def _om_city(i):
    dates = [str(_today + timedelta(days=d)) for d in range(config.FORECAST_DAYS)]
    rain = [0, 2, 18, 41, 12, 1, 0] if i in (1, 4) else [0, 0, 3, 8, 2, 0, 0]
    return {"daily": {
        "time": dates,
        "temperature_2m_max": [33 + i % 4, 34, 31, 29, 30, 32, 33],
        "temperature_2m_min": [20 + i % 3, 21, 21, 20, 20, 20, 21],
        "precipitation_sum": rain,
        "precipitation_probability_max": [5, 20, 70, 90, 60, 15, 5],
        "wind_speed_10m_max": [22, 28, 45, 52, 30, 20, 18],
        "wind_gusts_10m_max": [35, 44, 70, 82, 50, 33, 30] if i in (1, 4) else [30, 35, 48, 55, 40, 30, 28],
        "weather_code": [1, 2, 63, 65, 61, 2, 1],
    }}


FIRMS_CSV = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n" + "\n".join(
    f"{lat},{lon},330.1,0.4,0.4,{_today},1042,N,VIIRS,n,2.0NRT,295.2,{frp},D"
    for lat, lon, frp in [(9.81, 44.52, 6.1), (9.83, 44.55, 4.3), (9.80, 44.49, 8.8),
                          (10.12, 46.10, 3.2), (10.15, 46.13, 2.9), (8.95, 47.02, 12.4)])


def sample_data():
    """Run the real parsers on the sample payloads."""
    assert jtwc.warning_links(JTWC_RSS)
    storm = jtwc.parse_warning(JTWC_WARNING, jtwc.warning_links(JTWC_RSS)[0])
    raw_om = {c: _om_city(i) for i, c in enumerate(config.CITIES)}
    data = {
        "storms": [storm],
        "gdacs": gdacs.parse(GDACS_RESPONSE),
        "quakes": earthquakes.merge(earthquakes.parse_usgs(USGS_RESPONSE),
                                    earthquakes.parse_emsc(EMSC_RESPONSE)),
        "forecasts": openmeteo.parse_forecast(raw_om),
        "fires": firms.parse_csv(FIRMS_CSV, "VIIRS_SNPP_NRT"),
    }
    status = {k: "ok" for k in ("JTWC", "GDACS", "Earthquakes", "Open-Meteo", "FIRMS")}
    return data, status
