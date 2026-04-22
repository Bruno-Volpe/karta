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

Copy the environment file and fill in your keys:

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
