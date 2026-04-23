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
git clone https://github.com/Bruno-Volpe/karta
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

## Running

```bash
docker compose up --build
```

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
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

### `DELETE /sessions/{session_id}`

Clears a session (history + context). Useful before starting a new flow.

```bash
curl -X DELETE http://localhost:8000/sessions/session-001
```

---

## Complete booking conversation example

The full flow requires four messages in the same session. Each request builds on the previous one — Amelia maintains context automatically via `session_id`.

> For a faster experience, import `amelia.postman_collection.json` — it has all four requests pre-configured with environment variables for `base_url` and `session_id`.

**Step 0 — Clear the session** (run once before starting a new flow)

```bash
curl -X DELETE http://localhost:8000/sessions/session-001
```

**Step 1 — Search hotels**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-001",
    "message": "Search for 4-star hotels in Playa del Carmen, check-in June 1 2026, checkout June 3 2026, 2 adults"
  }'
```

Amelia resolves the city, starts the search, and returns a list of hotels with prices and refundable status.

**Step 2 — Select and validate**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-001",
    "message": "I'\''d like the first option. Can you validate the price and show me the cancellation policy?"
  }'
```

Amelia validates the current price against the API and shows the cancellation policy before you commit.

**Step 3 — Book**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-001",
    "message": "Please book it. Passenger: Juan Perez, Male, passport MX123456, Mexican, born 1990-01-15, phone +5215551234567, email juan@test.com"
  }'
```

Amelia extracts the passenger data, re-validates the price, creates the reservation, and confirms it with the supplier — all in one response.

**Step 4 — Cancel**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-001",
    "message": "Please cancel the reservation."
  }'
```

Amelia uses the reservation ID saved in context and cancels the booking.

---

## Example conversation (real session)

This is an actual session recorded during testing, showing the full flow including image retrieval and a natural language cancel:

```
→ "Search for 4-star hotels in Playa del Carmen, check-in June 1 2026, checkout June 3 2026, 2 adults"

← Here are some 4-star hotels in Playa del Carmen for your dates:
   • Hotel Colonial Playa del Carmen: 4 stars, $80.78, refundable.
   • Illusion Boutique Hotel By BFH: 4 stars, $86.56, refundable.
   • Tukan Hotel Playa del Carmen: 4 stars, $90.52, refundable.
   • (7 more options...)

→ "I'd like the first option. Can you validate the price and show me the cancellation policy?"

← The validated price for Hotel Colonial Playa del Carmen is $80.78 USD.
   Cancellation policy:
   • Cancel before May 31, 2026 10:58 PM UTC → fee of $40.39 USD
   • Cancel after May 31, 2026 10:59 PM UTC → fee of $80.78 USD

→ "show me pictures of the hotel"

← Here are some pictures of Hotel Colonial Playa del Carmen:
   https://i.travelapi.com/lodging/.../3688fc12_z.jpg
   https://i.travelapi.com/lodging/.../193d3f1c_z.jpg
   (+ more)

→ "ill have a commitment that day, i wont be able to be at the hotel"

← Do you mean you would like to cancel your reservation? Or would you like to search for a different date?

→ "yes"

← I understand you want to cancel, but I don't have a record of a reservation being made. Did you complete the booking process?

→ "Please book it. Passenger: Juan Perez, Male, passport MX123456, Mexican, born 1990-01-15, phone 5215551234567, email juan@test.com"

← Your booking for Hotel Colonial Playa del Carmen is confirmed! Your reservation ID is 354767.

→ "now may i cancel?"

← I have successfully cancelled your reservation.
```

When asked for photos, Amelia returns real image URLs from the Netactica Static Content API:

<img width="564" alt="Hotel Colonial Playa del Carmen" src="https://github.com/user-attachments/assets/060a6ebb-3c5f-4186-b1be-b49d65cebd75" />

---

## Nice to have

All three optional items from the challenge spec are implemented:

| Feature | How |
|---|---|
| **Image URLs in hotel results** | `get_hotel_details` returns a list of image URLs — ask Amelia "show me photos of this hotel" |
| **Cancellation policies before booking** | `validate` returns policies and Amelia displays them in Step 2 before you confirm |
| **Filter support** | `get_results` supports stars (`categories`), price range (`price_from`/`price_to`), refundable-only, and sort order — the agent applies them from natural language |

---

## Running tests
> **Note:** this test suite was created to support development and basic validation. In a real-world application, many more tests would be included, covering additional scenarios, integrations, and edge cases.

```bash
pip install -r requirements.txt
docker compose up redis -d
pytest tests/ -v -s
```

> **Note:** `test_redis_conectado` and `test_session_persiste_no_redis` require Redis running. All other tests run without Docker.

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

## Future improvements

These are known limitations and natural next steps beyond the scope of this challenge:

**Latency & UX**
- **Streaming responses (SSE)** — the agent currently waits for all tool calls to finish before returning a response. With Server-Sent Events, the backend could emit progress events while tools execute ("Searching hotels… ✓ Validating price… ✓") and stream the final text token by token. Requires a `/chat/stream` endpoint on the back and an EventSource listener on the front.
- **Frontend** — a web or mobile UI with loading states and streaming support would make the latency far less noticeable than the current 30-40s of silence on a raw API call.

**Agent quality**
- **Better model** — Gemini 2.5-flash was chosen as the best available model within the free-tier quota. A more capable model (e.g. Gemini 2.5-pro or GPT-4o) would produce more reliable tool call sequences and fewer hallucinated arguments.
- **Structured output for passenger extraction** — currently the agent extracts passenger data from free text and passes it to the `book` tool. A dedicated structured-output step would validate all required fields before attempting to book, reducing booking failures from missing data.
- **Tool call observability** — log tool call sequences and latencies per request to Datadog/OpenTelemetry so you can see which tool is the bottleneck in production.

**Features**
- **Multi-room support** — the current implementation books a single room. Supporting multiple rooms would require passing an array of `Rooms` objects and one `Traveler` per room.
- **Children ages** — Netactica accepts children ages per room; the current implementation ignores this field.
- **Multiple passengers** — only the lead passenger is collected today. Full group bookings require one `Traveler` per adult.
- **Booking retrieval** — a `get_reservation(reservation_id)` tool to look up existing bookings by ID.
- **Price alerts** — notify the user if the price of a watched hotel drops.

**Infrastructure**
- **Authentication on `/chat`** — the endpoint is currently open. In production it should require a JWT or API key tied to the Karta card account.
- **Rate limiting** — prevent abuse with per-session or per-IP request throttling.
- **Horizontal scaling** — Redis already makes sessions stateless, so scaling to multiple API workers is straightforward. The Netactica token cache would need to move to Redis as well.
- **Async HTTP client** — replacing `httpx` sync calls with `httpx.AsyncClient` inside async FastAPI handlers would free the event loop during I/O-heavy tool calls.

---

## Development notes

This project was developed as a single-developer challenge without feature branches or pull requests — all commits go directly to `main`. In a team setting, each feature would live in its own branch with a PR and review before merging.
