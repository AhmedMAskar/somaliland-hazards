"""Region, places, and alert thresholds for the Somaliland hazard monitor.

Edit this file to tune what counts as an alert.
"""

# Area of interest: Somaliland plus a maritime buffer over the Gulf of Aden.
# (west, south, east, north) in decimal degrees.
LAND_BBOX = (42.6, 7.5, 49.5, 11.6)
WATCH_BBOX = (38.0, 2.0, 60.0, 18.0)  # wider box for cyclones offshore

# Cities used for forecasts and distance checks.
CITIES = {
    "Hargeisa": (9.5600, 44.0650),
    "Berbera": (10.4396, 45.0143),
    "Burao": (9.5221, 45.5336),
    "Borama": (9.9361, 43.1828),
    "Erigavo": (10.6162, 47.3680),
    "Las Anod": (8.4774, 47.3597),
    "Gabiley": (9.7000, 43.6333),
    "Zeila": (11.3528, 43.4733),
}

# Coastal points used to judge how close a cyclone is to shore.
COAST_POINTS = {
    "Zeila": (11.3528, 43.4733),
    "Lughaya": (10.6864, 43.9469),
    "Berbera": (10.4396, 45.0143),
    "Maydh": (10.9967, 47.0961),
    "Las Qoray": (11.1667, 48.2000),
}

TIMEZONE = "Africa/Mogadishu"  # EAT, UTC+3
FORECAST_DAYS = 7

# Lookback windows
EQ_LOOKBACK_DAYS = 7
GDACS_LOOKBACK_DAYS = 14
FIRMS_LOOKBACK_DAYS = 2  # API allows 1-10

# ---- Alert thresholds -------------------------------------------------------
CYCLONE_WATCH_KM = 800      # storm center or forecast point within this of coast
CYCLONE_WARNING_KM = 300
EQ_MIN_MAG_FETCH = 2.5
EQ_ALERT_MAG = 4.5
EQ_WARNING_MAG = 5.5
RAIN_WATCH_MM = 30          # daily total at a city
RAIN_WARNING_MM = 60
GUST_WATCH_KMH = 60
GUST_WARNING_KMH = 90
HEAT_WATCH_C = 40
HEAT_WARNING_C = 44
FIRE_WATCH_COUNT = 5        # hotspots inside LAND_BBOX
FIRE_WARNING_COUNT = 25
GDACS_RADIUS_KM = 500       # GDACS events within this of Somaliland count

HTTP_TIMEOUT = 30
USER_AGENT = "somaliland-hazards/0.1 (research prototype)"
