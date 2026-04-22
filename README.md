# Amelia — Hotel Booking AI Agent

Amelia is an AI agent that helps users search, book, and cancel hotel reservations via natural language, powered by Gemini and the Netactica hotel API.

---

## Requirements

- Python 3.10+
- A [Google AI Studio](https://aistudio.google.com) API key (free)

---

## Setup

```bash
git clone <repo>
cd amelia

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the environment file and fill in your keys — all variables are documented in `.env.example`:

```bash
cp .env.example .env
```

> **Note:** The `.env.example` in this repo contains a temporary test key exposed intentionally. It has no billing attached and will be revoked after evaluation.

---

## Running locally

```bash
uvicorn main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

---

## Running tests
> **Note:** this test suite was created to support development and basic validation. In a real-world application, many more tests would be included, covering additional scenarios, integrations, and edge cases.

```bash
pytest tests/ -v -s
```

Current smoke tests:

| Test | What it checks |
|---|---|
| `test_gemini_conectado` | Gemini API key is valid and model responds |
| `test_auth` | Netactica auth returns a valid token |
| `test_autocomplete` | Netactica location search returns results |

---

## Architectural decisions

**Netactica token stored in-memory, not Redis**

The Netactica token is a service-level credential — it represents the application, not an individual user. A single token is shared across all concurrent users, which means there is no need for per-user token storage.

In-memory is the right fit here because:
- The app runs as a single process for this challenge
- If the process restarts, fetching a new token costs one cheap HTTP request
- Adding Redis as a hard dependency just to cache a token that refreshes every 23 hours would be over-engineering

Redis is used exclusively for user session storage (conversation history and booking context), where persistence and isolation between users actually matter.

`netactica/auth.py` is a standalone module responsible only for token lifecycle. `netactica/client.py` consumes it via `get_headers()`, and passes `force_refresh=True` on any 401 response to transparently renew the token.

---

## Development notes

This project was developed as a single-developer challenge without feature branches or pull requests — all commits go directly to `main`. In a team setting, each feature would live in its own branch with a PR and review before merging.
