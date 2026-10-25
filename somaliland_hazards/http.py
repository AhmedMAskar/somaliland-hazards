"""Shared HTTP session with retries and polite headers."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

_session = None


def session():
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(total=3, backoff_factor=1.5,
                      status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=("GET",))
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = config.USER_AGENT
        _session = s
    return _session


def get(url, **kw):
    kw.setdefault("timeout", config.HTTP_TIMEOUT)
    r = session().get(url, **kw)
    r.raise_for_status()
    return r
