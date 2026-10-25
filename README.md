# Somaliland Hazard Monitor

Python pipeline that pulls live hazard data for Somaliland, runs alert rules, and
writes GeoJSON files plus an interactive map (`output/map.html`).

| Hazard | Source | Key needed |
|---|---|---|
| Tropical cyclones (track + forecast) | JTWC RSS + warning text | No |
| Multi-hazard alerts (cyclone, flood, drought, wildfire, volcano) | GDACS API | No |
| Earthquakes (Gulf of Aden rift, Afar) | USGS + EMSC, merged/de-duplicated | No |
| 7-day forecast: rain, gusts, heat | Open-Meteo (ECMWF/GFS blend) | No |
| River discharge (GloFAS) | Open-Meteo flood API (`openmeteo.fetch_river_discharge`) | No |
| Wildfire hotspots | NASA FIRMS (VIIRS + MODIS) | Free MAP_KEY |
| Satellite + rainfall map layers | NASA GIBS (VIIRS true color, GPM IMERG) | No |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m somaliland_hazards sample      # offline demo with made-up data
python -m somaliland_hazards run         # live run, writes output/
python -m somaliland_hazards watch --every 30   # refresh every 30 minutes
python -m somaliland_hazards serve         # open output/map.html at http://localhost:8000
pytest -q                                # parser tests, no network
```

## Test in Jupyter first

Open `notebooks/somaliland_hazards_test.ipynb` (Jupyter Lab, VS Code, or Colab) and run top to
bottom. Each source runs in its own cell with a table of results, then alerts, then the map inline.
Set `USE_SAMPLE = True` in the setup cell to test offline.

Wildfire hotspots: get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/
then `export FIRMS_MAP_KEY=yourkey` (or `--firms-key yourkey`).

Draw a real outline instead of the box: `--boundary somaliland.geojson`
(build one from HDX Somalia admin1 regions: Awdal, Woqooyi Galbeed, Togdheer, Sool, Sanaag).

## Blank basemap?

Open the map with `python -m somaliland_hazards serve` (or notebook cell 11), not by
double-clicking `map.html`. Pages opened straight from disk send no web address with their
tile requests, and OpenStreetMap blocks those. If tiles still fail, the map shows a red banner;
pick another base map from the layer list (Esri, CARTO, NASA) or pause your ad blocker for the page.

## Outputs (`output/`)

- `map.html` — layers for cyclones, GDACS, earthquakes, fires, city forecasts, satellite; alert panel
- `alerts.json` — ranked alerts (Warning / Watch / Info) with per-feed status
- `cyclones.geojson`, `gdacs.geojson`, `earthquakes.geojson`, `fires.geojson`, `forecasts.json`

## Tuning

All thresholds, cities, coast points and bounding boxes live in
`somaliland_hazards/config.py` (e.g. `RAIN_WARNING_MM`, `CYCLONE_WATCH_KM`, `EQ_ALERT_MAG`).

## Layout

```
somaliland_hazards/
  config.py      region, cities, thresholds
  geo.py         distance / bbox helpers
  http.py        session with retries
  sources/       jtwc.py gdacs.py earthquakes.py openmeteo.py firms.py
  alerts.py      alert rules
  mapper.py      folium map
  pipeline.py    fetch -> alerts -> files
  sample.py      offline payloads in real API formats
tests/test_parsers.py
```

## Notes

- **Somaliland naming.** Feeds label the whole region "Somalia". `somaliland_hazards/naming.py`
  relabels any location inside former British Somaliland as **Somaliland** and leaves
  everything else as Somalia. The eastern line follows the 1894 Anglo-Italian boundary
  (49°E from the coast to 9°N, 9°N west to 48°E, 48°E south to 8°N); the Ethiopia/Djibouti
  sides are approximate. Passing `--boundary yourfile.geojson` uses your boundary for this too.
  Links out to GDACS/USGS pages show their own wording.

- JTWC products are intended for U.S. government use; IMD / RSMC New Delhi is the
  official warning center for the North Indian Ocean. Credit both on any public page.
- JTWC parsing reads the plain-text warnings (`io##YYweb.txt`). If JTWC changes its
  feed URL, update `RSS_URL` in `sources/jtwc.py`.
- Each feed fails independently; a dead source shows ✗ in the map panel and the rest still run.

## Publish a live public map (GitHub Pages)

`.github/workflows/update-map.yml` runs the pipeline on GitHub every 30 minutes and publishes
the map. No server needed.

1. Create an empty repo on GitHub (e.g. `somaliland-hazards`), then from this folder:
   ```bash
   git remote add origin https://github.com/<you>/somaliland-hazards.git
   git push -u origin main
   ```
2. Repo **Settings > Pages > Source: GitHub Actions**.
3. (Optional) **Settings > Secrets and variables > Actions**: add `FIRMS_MAP_KEY`.
4. **Actions > Update hazard map > Run workflow** for the first build.
   The map appears at `https://<you>.github.io/somaliland-hazards/`.

Notes: GitHub may delay scheduled runs by several minutes, and on public repos it pauses
scheduled workflows after 60 days with no repository activity; re-enable from the Actions tab.
Pages is public even if you only want to share a link, so keep the JTWC/IMD credit in the panel.

Run locally on a schedule instead: cron
`*/30 * * * * cd /path/to/somaliland-hazards && .venv/bin/python -m somaliland_hazards run`
or Windows Task Scheduler.
