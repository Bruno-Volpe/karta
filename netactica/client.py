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
    if not r.is_success:
        logger.error("POST %s → %s: %s", url, r.status_code, r.text[:500])
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


def search_hotels(
    location_id: int,
    checkin: str,
    checkout: str,
    adults: int = 2,
    children: int = 0,
    max_results: int = 50,
) -> str:
    """Start an async hotel search and return the SearchId.

    The search is asynchronous — call get_results(search_id) to fetch hotels.
    """
    from netactica.auth import get_token

    payload = {
        "DestinationType": "location",
        "LocationId": location_id,
        "CheckIn": checkin,
        "CheckOut": checkout,
        "Rooms": [{"Adults": adults, "Children": children}],
        "SessionToken": get_token(),
        "IncludeHotelInfo": True,
        "IncludeRooms": True,
        "MaxResults": max_results,
    }
    r = _post(f"{settings.netactica_base_url}/HotelSearchV3", json=payload)
    data = r.json()
    search_id = data["SearchId"]
    logger.info("Search started: id=%s count=%s", search_id, data.get("ResultsCount"))
    return search_id


def get_results(
    search_id: str,
    categories: list[str] | None = None,
    refundable_only: bool = False,
    price_from: float | None = None,
    price_to: float | None = None,
    order_by: str = "RECOMENDATION",
    limit: int = 10,
) -> list[dict]:
    """Fetch hotel results for a given SearchId with optional filters.

    Returns a simplified list of hotels ready to show to the user.
    Note: Categories must be strings (["4","5"]), not ints.
    Note: RefundableType 0=Refundable, 1=NonRefundable (inverted in API).
    """
    from netactica.auth import get_token

    payload: dict = {
        "SearchId": search_id,
        "SessionToken": get_token(),
        "IncludeRooms": True,
        "OrderCriteria": order_by,
        "ResultCountUpperBound": limit,
    }

    if categories:
        payload["Categories"] = [str(c) for c in categories]  # must be strings
    if refundable_only:
        payload["RefundableType"] = 0  # 0=Refundable (inverted!)
    if price_from is not None:
        payload["PriceFrom"] = price_from
    if price_to is not None:
        payload["PriceTo"] = price_to

    r = _post(f"{settings.netactica_base_url}/HotelResultsV2", json=payload)
    hotels = r.json().get("Results", [])

    return [_format_hotel(h) for h in hotels]


def get_hotel_details(search_id: str, option_id: int) -> dict:
    """Fetch extended hotel info: images, amenities, reviews.

    Uses scapi-testing endpoint (Static Content API).
    Note: param name is hotelOptionId (not optionId).
    Images are returned as a list of URL strings.
    """
    r = _get(
        "https://scapi-testing.netactica.io/hotel/details",
        params={"searchId": search_id, "hotelOptionId": str(option_id), "language": "en"},
    )
    data = r.json()
    info = data.get("Info", {})

    amenities = [
        desc.get("Description", "")
        for amenity in info.get("Ammenities", [])
        for desc in amenity.get("Description", [])
        if desc.get("Locale") == "en"
    ] or [
        desc.get("Description", "")
        for amenity in info.get("Ammenities", [])
        for desc in amenity.get("Description", [])
    ]

    meta_reviews = [
        {
            "category": m.get("CategoryName"),
            "score": m.get("Score"),
            "text": m.get("ShortText") or m.get("Text"),
        }
        for m in info.get("MetaReviews", [])
    ]

    return {
        "name": info.get("HotelName"),
        "description": info.get("ShortDescription"),
        "address": info.get("FullAddress"),
        "images": info.get("Images", []),           # list of URL strings
        "thumbnail": info.get("Thumbnail"),
        "amenities": amenities[:10],
        "reviews_count": info.get("ReviewsCount"),
        "meta_reviews": meta_reviews[:5],
        "cancellation_policies": data.get("Result", {}).get("CancellationPolicies", []),
    }


def validate(search_id: str, option_id: int, rate_id: str) -> dict:
    """Validate price, availability and cancellation policies before booking.

    Returns a dict with: validate_option_id, config_doc_id, amount, policies, status.
    StatusChanged values: Available, NotAvailable, PriceDifference, CancellationPoliciesChanged.
    CancellationPoliciesChanged still allows booking — just inform the user.
    """
    from netactica.auth import get_token
    token = get_token()

    # Gemini double-escapes JSON strings (\" → \") — normalize before sending
    if rate_id and '\\"' in rate_id:
        rate_id = rate_id.replace('\\"', '"')
    logger.info("Validate: search_id=%s option_id=%s rate_id=%r", search_id, option_id, rate_id)
    r = _post(f"{settings.netactica_base_url}/hotelvalidation", json={
        "SearchId": search_id,
        "SessionToken": token,
        "OptionId": option_id,
        "RateId": rate_id,
        "IncludeAlternativeCurrencies": False,
    })
    data = r.json()

    status = data.get("StatusChanged")
    if status == "NotAvailable":
        raise ValueError("Hotel option is no longer available.")

    policies = [
        {
            "date_from": p.get("DateFromGmtAgency") or p.get("DateFrom"),
            "date_to": p.get("DateToGmtAgency") or p.get("DateTo"),
            "amount": p.get("Amount", {}).get("Fare"),
            "currency": p.get("Amount", {}).get("CurrencyCode"),
        }
        for p in data.get("CancellationPolicies", [])
    ]

    amount = data.get("Amount", {})
    return {
        "validate_option_id": data.get("ValidateOptionId"),
        "config_doc_id": data.get("ValidDocuments", [{}])[0].get("Id"),  # int!
        "total": amount.get("Total"),
        "currency": amount.get("CurrencyCode"),
        "status": status,
        "cancellation_policies": policies,
        "allow_only_first_pax": data.get("AllowOnlyFirstPax", False),
    }


def book(validate_option_id: str, travelers: list[dict]) -> dict:
    """Create a hotel reservation.

    travelers: list of dicts matching the Traveler model fields.
    Returns: reservation_id, travel_itinerary_id, hotel info.
    """
    from netactica.auth import get_token
    token = get_token()

    payload = {
        "SessionToken": token,
        "ValidateOptionId": validate_option_id,
        "Travelers": travelers,
    }
    logger.info("Book payload (no token): ValidateOptionId=%s Travelers=%s", validate_option_id, travelers)
    r = _post(f"{settings.netactica_base_url}/HotelBook", json=payload)
    data = r.json()
    return {
        "reservation_id": data.get("ReservationId"),
        "travel_itinerary_id": data.get("TravelItineraryId"),
        "hotel_name": data.get("Reservation", {}).get("Hotel", {}).get("HotelName"),
    }


def confirm(reservation_id: int) -> dict:
    """Confirm a booked reservation with the supplier.

    Returns: status, supplier_reference_code.
    """
    from netactica.auth import get_token
    token = get_token()

    r = _post(f"{settings.netactica_base_url}/Hotel/Confirm", json={
        "HotelReservationId": reservation_id,
        "SessionToken": token,
    })
    reservation = r.json().get("Reservation", {})
    status = reservation.get("Status")
    if status != "Confirm":
        raise ValueError(f"Confirmation failed with status: {status}")

    return {
        "reservation_id": reservation_id,
        "status": status,
        "supplier_reference": reservation.get("SupplierReferenceCode"),
    }


def cancel(reservation_id: int) -> dict:
    """Cancel a reservation.

    Returns: reservation_id, status.
    """
    from netactica.auth import get_token
    token = get_token()

    r = _post(f"{settings.netactica_base_url}/Hotel/Cancel/", json={
        "HotelReservationId": reservation_id,
        "SessionToken": token,
    })
    reservation = r.json().get("Reservation", {})
    status = reservation.get("Status")
    if status != "Cancelled":
        raise ValueError(f"Cancellation failed with status: {status}")

    return {
        "reservation_id": reservation_id,
        "status": status,
    }


def _format_hotel(h: dict) -> dict:
    """Extract the fields relevant to show the user."""
    # Pick the cheapest refundable rate, fallback to cheapest overall
    rates = h.get("RoomRates", [])
    refundable_rates = [r for r in rates if r.get("RefundableType") == 0]
    best_rate = min(refundable_rates or rates, key=lambda r: r.get("Price", {}).get("Total", 9999), default=None)

    return {
        "option_id": h.get("OptionId"),
        "hotel_id": h.get("HotelId"),
        "name": h.get("HotelName"),
        "category": h.get("Category"),  # int: 3, 4, 5
        "zone": h.get("Zone"),
        "address": h.get("FullAddress"),
        "score": h.get("Score"),
        "price_from": h.get("PriceFrom"),
        "currency": h.get("CurrencyCode"),
        "thumbnail": h.get("Thumbnail"),
        "best_rate": {
            "rate_id": best_rate.get("RateId"),
            "total": best_rate["Price"]["Total"],
            "currency": best_rate["Price"]["CurrencyCode"],
            "refundable": best_rate.get("RefundableType") == 0,
            "board": h.get("RoomRates", [{}])[0].get("BoardTypeCode"),
        } if best_rate else None,
    }
