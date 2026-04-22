"""Session store — persists conversation history and booking context per session.

Uses Redis when available, falls back to an in-memory dict if Redis is not configured
or unreachable. TTL is 24 hours for both backends.
"""
import json
import logging
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

TTL = 24 * 3600  # 24 hours in seconds

# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------
_store: dict[str, dict] = {}


def _get_redis():
    try:
        import redis
        client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        return client
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_session(session_id: str) -> dict:
    """Load session data. Returns empty session if not found."""
    r = _get_redis()
    if r:
        raw = r.get(f"session:{session_id}")
        if raw:
            return json.loads(raw)
    elif session_id in _store:
        return _store[session_id]

    return _empty_session()


def save_session(session_id: str, data: dict) -> None:
    """Persist session data with TTL."""
    r = _get_redis()
    if r:
        r.setex(f"session:{session_id}", TTL, json.dumps(data))
    else:
        _store[session_id] = data


def _empty_session() -> dict:
    return {
        "messages": [],   # conversation history: [{"role": "user"|"assistant", "content": "..."}]
        "context": {},    # booking state: search_id, option_id, reservation_id, etc.
    }


def update_context(session_id: str, **kwargs: Any) -> None:
    """Merge key/value pairs into the session context."""
    session = get_session(session_id)
    session["context"].update(kwargs)
    save_session(session_id, session)


def append_message(session_id: str, role: str, content: str) -> None:
    """Append a message to the session history."""
    session = get_session(session_id)
    session["messages"].append({"role": role, "content": content})
    save_session(session_id, session)
