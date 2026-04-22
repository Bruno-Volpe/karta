"""Smoke tests — verifica conexão e funcionalidades básicas da Netactica."""
import pytest
import httpx
from config import settings
from netactica.client import search_location

#Just to get it easier the debugging, development
def test_auth():
    r = httpx.post(f"{settings.netactica_base_url}/Session", json={
        "UserName": settings.netactica_username,
        "Password": settings.netactica_password,
        "UserService": settings.netactica_user_service,
    })
    assert r.status_code == 200
    token = r.json()["Token"]["TokenId"]
    assert token
    print(f"\nToken: {token[:12]}...")


def test_autocomplete():
    r = httpx.get(f"{settings.netactica_static_url}/net/search", params={"searchText": "Cancun", "locale": "en"})
    assert r.status_code == 200
    locations = r.json().get("locations", [])
    assert len(locations) > 0
    print(f"\nPrimeiro resultado: {locations[0]['NameFull']}")


def test_search_location_retorna_id():
    loc = search_location("Cancun")
    assert loc["Id"] == 340317
    assert loc["Type"] == "multi_city_vicinity"
    print(f"\n{loc['NameFull']} → id={loc['Id']}")


def test_search_location_cidade_invalida():
    with pytest.raises(ValueError):
        search_location("xyzabc123")


def test_search_hotels_retorna_search_id():
    from netactica.client import search_hotels
    loc = search_location("Cancun")
    search_id = search_hotels(loc["Id"], "2026-06-01", "2026-06-03", adults=2)
    assert search_id
    print(f"\nSearchId: {search_id}")


def test_get_results_retorna_hoteis():
    from netactica.client import search_hotels, get_results
    loc = search_location("Cancun")
    search_id = search_hotels(loc["Id"], "2026-06-01", "2026-06-03", adults=2)
    hotels = get_results(search_id, categories=["4", "5"], limit=3)
    assert len(hotels) > 0
    assert hotels[0]["name"]
    assert hotels[0]["best_rate"]["total"] > 0
    print(f"\n{len(hotels)} hotéis: {[h['name'] for h in hotels]}")


def test_get_hotel_details():
    from netactica.client import search_hotels, get_results, get_hotel_details
    loc = search_location("Cancun")
    sid = search_hotels(loc["Id"], "2026-06-01", "2026-06-03", adults=2)
    hotels = get_results(sid, limit=1)
    details = get_hotel_details(sid, hotels[0]["option_id"])
    assert details["name"]
    assert len(details["images"]) > 0
    print(f"\n{details['name']}: {len(details['images'])} imagens, {details['reviews_count']} reviews")


def test_fluxo_completo():
    from netactica.client import search_hotels, get_results, validate, book, confirm, cancel
    loc = search_location("Playa del Carmen")
    sid = search_hotels(loc["Id"], "2026-06-01", "2026-06-03", adults=2)
    hotels = get_results(sid, categories=["4", "5"], limit=1)
    h = hotels[0]
    rate = h["best_rate"]

    v = validate(sid, h["option_id"], rate["rate_id"])
    assert v["validate_option_id"]
    assert v["config_doc_id"]
    assert v["total"] > 0

    traveler = {
        "RoomNumber": 1, "PaxType": "Adult", "Gender": "Male",
        "FirstName": "Juan", "LastName": "Perez",
        "Phone": "5215551234567", "Email": "juan@test.com",
        "DocumentNumber": "MX123456",
        "ConfigurationDocumentId": v["config_doc_id"],
        "Nationality": "MX", "DOB": "1990-01-15",
    }
    b = book(v["validate_option_id"], [traveler])
    assert b["reservation_id"]
    print(f"\nReservationId: {b['reservation_id']}")

    c = confirm(b["reservation_id"])
    assert c["status"] == "Confirm"

    cx = cancel(b["reservation_id"])
    assert cx["status"] == "Cancelled"
    print(f"Cancelado: #{cx['reservation_id']}")
