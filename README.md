# Amelia — Hotel Booking AI Agent

Amelia is an AI agent that helps users search, book, and cancel hotel reservations via natural language, powered by Gemini and the Netactica hotel API.

---

## Requirements

- Python 3.10+
- A [Google AI Studio](https://aistudio.google.com) API key (free)

> **Model:** defaults to `gemini-2.5-flash` — chosen as the best available model for reasoning and function calling. The free tier without billing is limited to 20 req/day, which is impractical for testing. Adding a billing account to Google AI Studio unlocks significantly higher quotas (pay-as-you-go). A more capable model directly improves the agent's ability to handle complex conversations, ambiguous requests, and multi-step booking flows. The model can be changed via `GEMINI_MODEL` in `.env`.

---

## Setup

```bash
git clone <repo>
cd karta

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
# Start Redis (required for session persistence)
docker compose up redis -d

uvicorn main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Running with Docker (API + Redis together)

```bash
docker compose up --build
```

---

## API

### `POST /chat`

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "session-001", "message": "Search 4-star hotels in Cancun, June 1-3 2026, 2 adults"}'
```

### `GET /sessions/{session_id}/history`

```bash
curl http://localhost:8000/sessions/session-001/history
```

### Postman collection

Import `amelia.postman_collection.json` to run a full conversation flow: search → validate → book → cancel.

---

## Running tests
> **Note:** this test suite was created to support development and basic validation. In a real-world application, many more tests would be included, covering additional scenarios, integrations, and edge cases.

```bash
pytest tests/ -v -s
```

> **Note:** `test_redis_conectado` and `test_session_persiste_no_redis` require Redis running (`docker compose up redis -d`). All other tests run without Docker.

Current smoke tests:

| Test | What it checks |
|---|---|
| `test_gemini_conectado` | Gemini API key is valid and model responds |
| `test_auth` | Netactica auth returns a valid token |
| `test_autocomplete` | Netactica location search returns results |
| `test_search_location_retorna_id` | City name resolves to correct LocationId |
| `test_search_location_cidade_invalida` | Invalid city raises ValueError |
| `test_search_hotels_retorna_search_id` | HotelSearchV3 returns a SearchId |
| `test_get_results_retorna_hoteis` | HotelResultsV2 returns filtered hotel list |
| `test_get_hotel_details` | Hotel details returns images and reviews |
| `test_fluxo_completo` | Full flow: search → validate → book → confirm → cancel |
| `test_redis_conectado` | Redis is reachable and responding |
| `test_session_persiste_no_redis` | Session data persists and is isolated between users |

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

**Session storage: Redis**

Each user conversation needs to persist two things across HTTP requests: the message history (so the AI remembers what was said) and the booking context (`search_id`, `option_id`, `reservation_id`, etc. so the AI knows where the flow is).

We considered several approaches:

| Option | How it works | Why we didn't choose it |
|---|---|---|
| **Client-side (frontend)** | Frontend sends full history on every request | No frontend in this challenge; also leaks booking context to the client |
| **JWT / signed token** | Encode session state in the request token | State grows with every message — tokens become large and can't be invalidated |
| **Sticky sessions** | Route each user to the same server instance | Breaks with multiple workers; not portable |
| **Database (Postgres/Mongo)** | Persist sessions in a DB | Too heavy for ephemeral conversation state; adds schema migrations |
| **In-memory dict** | Python dict in the process | Lost on restart; breaks with multiple workers |
| **Redis** ✅ | Key-value store with TTL | Fast, simple, survives restarts, works with multiple workers, native TTL support |

Redis fits perfectly because sessions are short-lived (24h TTL), the data is unstructured (JSON blob), and read/write performance matters more than query flexibility. The code falls back to in-memory automatically if Redis is unavailable, which keeps local development simple.

---

**Netactica API divergences from documentation**

Several behaviors discovered by testing the actual API differ from what the provided docs describe:

| What the doc said | What the API actually does |
|---|---|
| `DestinationType: "multi_city_vicinity"` | Only accepts `"location"` or `"hotel"` |
| `HotelResult.Category` is a string (`"4"`) | Returns an int (`4`) |
| `HotelResult.PriceFrom` is a Price object | Returns a plain float |
| `HotelResult.PropertyTypes` is a list | Returns a string (`"Hotels"`) |
| `HotelResultsV2.ResultCountUpperBound` is optional | Required and must be >= 1 |
| Hotel details: use `optionId` param | Param name is `hotelOptionId` |
| Hotel details endpoint: `static-content.netactica.io` | Must use `scapi-testing.netactica.io` |
| Hotel `Images` are objects with a `url` field | Images are plain URL strings |
| Gemini returns `INTEGER` schema values as floats | All integer tool args must be cast with `int()` in the dispatcher |

---

## Development notes

This project was developed as a single-developer challenge without feature branches or pull requests — all commits go directly to `main`. In a team setting, each feature would live in its own branch with a PR and review before merging.
