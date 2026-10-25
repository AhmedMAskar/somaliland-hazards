"""Render everything to a single interactive HTML map with folium."""
from datetime import datetime, timedelta, timezone
import html

import folium
from branca.element import MacroElement
from jinja2 import Template
from folium.plugins import Fullscreen, MousePosition

from . import config
from .sources.jtwc import category_from_kt

GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services"

# (name, url, attribution, max native zoom). No API keys needed.
BASEMAPS = [
    ("Esri light gray", f"{_ESRI}/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}",
     "Esri, HERE, Garmin, © OpenStreetMap contributors", 16),
    ("Esri imagery", f"{_ESRI}/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
     "Esri, Maxar, Earthstar Geographics", 18),
    ("Esri streets", f"{_ESRI}/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}",
     "Esri, HERE, Garmin, © OpenStreetMap contributors", 18),
    ("Esri topographic", f"{_ESRI}/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}",
     "Esri, HERE, Garmin, © OpenStreetMap contributors", 18),
    ("CARTO light", "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
     "© OpenStreetMap contributors © CARTO", 18),
    ("OpenStreetMap (needs http://localhost)", "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
     "© OpenStreetMap contributors", 18),
]

# Counts tile failures per base layer and shows a banner explaining what to do.
TILE_WATCH_JS = """
(function (map) {
  var box = document.createElement('div');
  box.style.cssText = 'position:fixed;bottom:28px;left:50%;transform:translateX(-50%);z-index:10000;' +
    'max-width:560px;background:#fdecea;color:#7b1f1f;border:1px solid #e6a5a5;border-radius:6px;' +
    'padding:8px 12px;font:12px/1.4 system-ui,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.2);display:none';
  document.body.appendChild(box);
  var fails = {}, oks = {};
  function hook(layer) {
    if (!(layer instanceof L.TileLayer) || layer._watched) return;
    layer._watched = true;
    var name = (layer.options.attribution || 'tiles').split(',')[0];
    layer.on('tileload', function () { oks[name] = (oks[name] || 0) + 1; });
    layer.on('tileerror', function () {
      fails[name] = (fails[name] || 0) + 1;
      if (fails[name] >= 4 && !(oks[name] > 0)) {
        var local = location.protocol === 'file:';
        box.innerHTML = '<b>Map tiles from ' + name + ' are not loading.</b><br>' +
          (local ? 'This page was opened as a file. Run <code>python -m somaliland_hazards serve</code> ' +
                   'and use the http://localhost link instead. ' : '') +
          'Try another base map (layers list, top left), or pause your ad blocker / tracking ' +
          'protection for this page.';
        box.style.display = 'block';
      }
    });
  }
  map.eachLayer(hook);
  map.on('layeradd', function (e) { hook(e.layer); });
  map.on('baselayerchange', function () { box.style.display = 'none'; });
})(__MAP__);
"""
LEVEL_COLOR = {"Warning": "#c0392b", "Watch": "#e67e22", "Info": "#2e86c1"}
GDACS_COLOR = {"Red": "#c0392b", "Orange": "#e67e22", "Green": "#27ae60"}
CAT_COLOR = {"Depression": "#5dade2", "Deep depression": "#48c9b0", "Cyclonic storm": "#f4d03f",
             "Severe cyclonic storm": "#f39c12", "Very severe cyclonic storm": "#e74c3c",
             "Extremely severe cyclonic storm": "#a93226", "Super cyclonic storm": "#6c3483",
             "Unknown": "#7f8c8d"}


def _esc(x):
    return html.escape("" if x is None else str(x))


def _forecast_table(city, days):
    rows = "".join(
        f"<tr><td>{d['date'][5:]}</td><td>{_esc(d['summary'])}</td>"
        f"<td>{d['tmax']:.0f}/{d['tmin']:.0f}</td><td>{(d['rain_mm'] or 0):.0f}</td>"
        f"<td>{(d['gust_kmh'] or 0):.0f}</td></tr>"
        for d in days if d["tmax"] is not None)
    return (f"<b>{_esc(city)}</b> — 7-day forecast"
            "<table style='font-size:11px;border-collapse:collapse' cellpadding=3>"
            "<tr style='background:#eee'><th>Day</th><th>Sky</th><th>°C hi/lo</th>"
            f"<th>Rain mm</th><th>Gust km/h</th></tr>{rows}</table>")


def _panel(alerts, status, generated, sample):
    items = "".join(
        f"<div style='border-left:4px solid {LEVEL_COLOR[a['level']]};padding:4px 8px;margin:6px 0'>"
        f"<b>{_esc(a['level'])}</b> · {_esc(a['hazard'])}<br><b>{_esc(a['title'])}</b><br>"
        f"<span style='color:#555'>{_esc(a['detail'])}</span>"
        f"<div style='color:#888;font-size:10px'>{_esc(a['source'])}</div></div>"
        for a in alerts)
    failed = [k for k, v in status.items() if not (v == "ok" or v.startswith("skipped"))]
    if failed:
        items = ("<div style='background:#fdecea;color:#922;padding:4px 8px;border-radius:4px'>"
                 f"Feeds unavailable: {_esc(', '.join(failed))}. Alerts may be incomplete.</div>"
                 + items)
    elif not items:
        items = "<div style='color:#2e7d32'>No active alerts.</div>"
    stat = " · ".join(f"{_esc(k)}: {'✓' if v == 'ok' else '✗'}" for k, v in status.items())
    banner = ("<div style='background:#fff3cd;color:#7a5b00;padding:4px 8px;margin-bottom:6px;"
              "border-radius:4px'><b>Sample data</b> — not live observations</div>") if sample else ""
    return f"""
    <div style="position:fixed;top:12px;right:12px;width:320px;max-height:78vh;overflow:auto;
      z-index:9999;background:rgba(255,255,255,.96);border-radius:8px;padding:10px 12px;
      box-shadow:0 2px 10px rgba(0,0,0,.25);font:12px/1.35 system-ui,sans-serif">
      {banner}
      <div style="font-size:15px;font-weight:600">Somaliland Hazard Monitor</div>
      <div style="color:#666;font-size:11px">Updated {_esc(generated)} UTC</div>
      <div style="margin-top:6px">{items}</div>
      <div style="color:#888;font-size:10px;margin-top:8px">Feeds: {stat}</div>
      <div style="color:#888;font-size:10px">Official cyclone warnings for this basin:
        IMD / RSMC New Delhi. JTWC data shown for reference.</div>
    </div>"""


class _TileWatch(MacroElement):
    """Injects TILE_WATCH_JS right after the Leaflet map is created."""
    _template = Template(
        "{% macro script(this, kwargs) %}"
        + TILE_WATCH_JS.replace("__MAP__", "{{ this._parent.get_name() }}")
        + "{% endmacro %}")


def build_map(storms, quakes, forecasts, fires, gdacs_events, alerts, status,
              out_path="map.html", boundary=None, sample=False):
    m = make_map(storms, quakes, forecasts, fires, gdacs_events, alerts, status,
                 boundary=boundary, sample=sample)
    m.save(out_path)
    return out_path


def make_map(storms, quakes, forecasts, fires, gdacs_events, alerts, status,
             boundary=None, sample=False):
    """Return the folium.Map (display it directly in a notebook)."""
    m = folium.Map(location=[10.0, 45.8], zoom_start=6, tiles=None, control_scale=True)

    _TileWatch().add_to(m)  # must come before the tile layers are added

    # Base maps from several providers, so one blocked server doesn't leave the map blank.
    # The first one is shown by default.
    for name, url, attr, max_native in BASEMAPS:
        folium.TileLayer(url, attr=attr, name=name, max_native_zoom=max_native,
                         max_zoom=18, overlay=False, control=True,
                         show=(name == BASEMAPS[0][0])).add_to(m)

    # Satellite date: 2 days back, because GIBS daily mosaics finish late in the day UTC.
    day = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    folium.TileLayer(
        tiles=f"{GIBS}/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/{day}/"
              "GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
        attr="NASA GIBS / VIIRS", name=f"NASA satellite true color ({day})",
        max_native_zoom=9, max_zoom=18, overlay=False, show=False).add_to(m)
    folium.TileLayer(
        tiles=f"{GIBS}/IMERG_Precipitation_Rate/default/{day}/"
              "GoogleMapsCompatible_Level6/{z}/{y}/{x}.png",
        attr="NASA GIBS / GPM IMERG", name=f"Rainfall rate IMERG ({day})",
        overlay=True, opacity=0.7, max_native_zoom=6, show=False).add_to(m)

    if boundary:
        folium.GeoJson(boundary, name="Somaliland boundary",
                       style_function=lambda _: {"color": "#2c3e50", "weight": 2,
                                                 "fill": False}).add_to(m)
    else:
        w, s, e, n = config.LAND_BBOX
        folium.Rectangle([[s, w], [n, e]], color="#2c3e50", weight=1, dash_array="6",
                         fill=False, tooltip="Monitoring area").add_to(m)

    # Cyclones
    fg = folium.FeatureGroup(name="Tropical cyclones (JTWC)")
    for s in storms:
        pts = [[p["lat"], p["lon"]] for p in s["track"]]
        folium.PolyLine(pts, color="#8e44ad", weight=3, dash_array="8 6",
                        tooltip=f"{s['storm_id']} forecast track").add_to(fg)
        for p in s["track"]:
            cat = category_from_kt(p["wind_kt"])
            folium.CircleMarker(
                [p["lat"], p["lon"]], radius=9 if p["tau_h"] == 0 else 6,
                color="#333", weight=1, fill=True, fill_opacity=.9,
                fill_color=CAT_COLOR.get(cat, "#7f8c8d"),
                tooltip=f"{s['storm_id']} +{p['tau_h']}h · {p['wind_kt']} kt · {cat}",
                popup=folium.Popup(
                    f"<b>{_esc(s['storm_id'])} {_esc(s['name'] or '')}</b><br>"
                    f"{_esc(p['dtg'])} (+{p['tau_h']} h)<br>{p['wind_kt']} kt — {_esc(cat)}"
                    f"<br><a href='{_esc(s['url'])}' target=_blank>JTWC warning</a>", max_width=260)
            ).add_to(fg)
    fg.add_to(m)

    # GDACS
    fg = folium.FeatureGroup(name="GDACS alerts")
    for e in gdacs_events:
        p = e["properties"]
        lon, lat = e["geometry"]["coordinates"]
        folium.Marker(
            [lat, lon], icon=folium.Icon(color={"Red": "red", "Orange": "orange"}.get(
                p["alertlevel"], "green"), icon="exclamation-sign"),
            tooltip=f"GDACS {p['alertlevel']}: {p['name']}",
            popup=folium.Popup(
                f"<b>{_esc(p['hazard'])}</b> — {_esc(p['name'])}<br>{_esc(p['severity'])}<br>"
                f"{_esc(p['from'])} → {_esc(p['to'])}<br>"
                f"<a href='{_esc(p['report_url'])}' target=_blank>GDACS report</a>", max_width=280)
        ).add_to(fg)
    fg.add_to(m)

    # Earthquakes
    fg = folium.FeatureGroup(name="Earthquakes (USGS/EMSC)")
    for q in quakes:
        p = q["properties"]
        lon, lat = q["geometry"]["coordinates"]
        mag = p["mag"] or 0
        folium.CircleMarker(
            [lat, lon], radius=max(3, mag ** 1.6), weight=1, color="#7b241c",
            fill=True, fill_color="#e74c3c" if mag >= config.EQ_ALERT_MAG else "#f5b041",
            fill_opacity=.7, tooltip=f"M{mag} · {p['time'][:16].replace('T', ' ')} UTC",
            popup=folium.Popup(
                f"<b>M{mag}</b> {_esc(p['place'])}<br>Depth {p['depth_km']} km<br>"
                f"{p['km_to_city']} km from {_esc(p['nearest_city'])}<br>"
                f"<a href='{_esc(p['url'])}' target=_blank>{_esc(p['source'])}</a>", max_width=260)
        ).add_to(fg)
    fg.add_to(m)

    # Fires
    fg = folium.FeatureGroup(name="Fire hotspots (NASA FIRMS)")
    for f in fires:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        folium.CircleMarker([lat, lon], radius=3, color="#d35400", fill=True,
                            fill_opacity=.9, weight=0,
                            tooltip=f"Fire {p['date']} {p['time_utc']} · FRP {p['frp_mw']} MW"
                            ).add_to(fg)
    fg.add_to(m)

    # Cities + forecasts
    fg = folium.FeatureGroup(name="City forecasts")
    alert_cities = {a["title"].split("— ")[-1] for a in alerts if "— " in a["title"]}
    for city, (lat, lon) in config.CITIES.items():
        days = forecasts.get(city, [])
        today = days[0] if days else None
        label = f"{city}: {today['tmax']:.0f}°C, {today['summary']}" if today else city
        folium.CircleMarker(
            [lat, lon], radius=6, weight=2, color="#1b4f72", fill=True,
            fill_color="#e67e22" if city in alert_cities else "#ffffff", fill_opacity=1,
            tooltip=label,
            popup=folium.Popup(_forecast_table(city, days) if days else city, max_width=360)
        ).add_to(fg)
    fg.add_to(m)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    m.get_root().html.add_child(folium.Element(_panel(alerts, status, generated, sample)))
    folium.LayerControl(position="topleft", collapsed=False).add_to(m)

    Fullscreen(position="topleft").add_to(m)
    MousePosition(position="bottomleft", num_digits=3).add_to(m)
    m.get_root().header.add_child(folium.Element(
        "<title>Somaliland Hazard Monitor</title>"))
    return m
