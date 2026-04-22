"""Smoke tests — verifica conexão e funcionalidades básicas da Netactica."""
import pytest
import httpx
from config import settings
from netactica.client import search_location


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
