import logging

import httpx

from config import settings
from netactica.auth import get_headers

logger = logging.getLogger(__name__)

PREFERRED_LOCATION_TYPES = ["multi_city_vicinity", "city", "neighborhood"]


def _get(url: str, **kwargs) -> httpx.Response:
    """GET with automatic 401 retry."""
    r = httpx.get(url, headers=get_headers(), timeout=30, **kwargs)
    if r.status_code == 401:
        r = httpx.get(url, headers=get_headers(force_refresh=True), timeout=30, **kwargs)
    r.raise_for_status()
    return r


def _post(url: str, **kwargs) -> httpx.Response:
    """POST with automatic 401 retry."""
    r = httpx.post(url, headers=get_headers(), timeout=30, **kwargs)
    if r.status_code == 401:
        r = httpx.post(url, headers=get_headers(force_refresh=True), timeout=30, **kwargs)
    r.raise_for_status()
    return r


def search_location(city: str) -> dict:
    """Resolve a city name to a Netactica LocationId via autocomplete.

    Prefers multi_city_vicinity > city > neighborhood.
    Returns a dict with keys: Id, Type, Name, NameFull.
    Raises ValueError if no location is found.
    """
    r = httpx.get(
        f"{settings.netactica_static_url}/net/search",
        params={"searchText": city, "locale": "en"},
        timeout=30,
    )
    r.raise_for_status()
    locations: list[dict] = r.json().get("locations", [])

    if not locations:
        raise ValueError(f"No location found for '{city}'")

    # Pick the best match by preferred type
    for preferred_type in PREFERRED_LOCATION_TYPES:
        for loc in locations:
            if loc.get("Type") == preferred_type:
                logger.info("Resolved '%s' → %s (id=%s)", city, loc["NameFull"], loc["Id"])
                return loc

    # Fallback to first result
    loc = locations[0]
    logger.info("Resolved '%s' → %s (id=%s) [fallback]", city, loc["NameFull"], loc["Id"])
    return loc
