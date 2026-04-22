"""Smoke test — verifica se a conexão com a Netactica está funcionando."""
import httpx
from config import settings


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
    # Precisa de token
    r = httpx.post(f"{settings.netactica_base_url}/Session", json={
        "UserName": settings.netactica_username,
        "Password": settings.netactica_password,
        "UserService": settings.netactica_user_service,
    })
    token = r.json()["Token"]["TokenId"]

    r2 = httpx.get(f"{settings.netactica_static_url}/net/search", params={"searchText": "Cancun", "locale": "en"})
    assert r2.status_code == 200
    locations = r2.json().get("locations", [])
    assert len(locations) > 0
    print(f"\nPrimeiro resultado: {locations[0]['NameFull']}")
