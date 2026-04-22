import logging
import time

import httpx

from config import settings

logger = logging.getLogger(__name__)

_token: str | None = None
_token_expires_at: float = 0  # unix timestamp


def _fetch_token() -> str:
    response = httpx.post(
        f"{settings.netactica_base_url}/Session",
        json={
            "UserName": settings.netactica_username,
            "Password": settings.netactica_password,
            "UserService": settings.netactica_user_service,
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()["Token"]["TokenId"]
    logger.info("Netactica token refreshed")
    return token


def get_token(force_refresh: bool = False) -> str:
    """Return a valid Netactica token, refreshing if expired or forced."""
    global _token, _token_expires_at

    if force_refresh or _token is None or time.time() >= _token_expires_at:
        _token = _fetch_token()
        _token_expires_at = time.time() + 23 * 3600  # 24h validity, renew at 23h

    return _token


def get_headers(force_refresh: bool = False) -> dict:
    """Return Authorization headers with a valid token."""
    return {"Authorization": f"Bearer {get_token(force_refresh)}"}
