# Bugs Found and Fixed During End-to-End Testing

## Bug 1 — `InvalidRateId` on validate (Gemini double-escaping JSON)

**Symptom:** `validate` call returned 400 `InvalidRateId` even though the rate_id came directly from `get_results`.

**Root cause:** The Netactica API returns `RateId` as a JSON string, e.g. `[{"RtaId":1,"RoomOptionId":1}]`. When Gemini passes this back as a tool parameter, it double-escapes the inner quotes: `[{\"RtaId\":1,...}]`. The API rejected this malformed value.

**Fix:** In `client.validate()`, normalize the rate_id before sending:
```python
if rate_id and '\\"' in rate_id:
    rate_id = rate_id.replace('\\"', '"')
```

**File:** `netactica/client.py`

---

## Bug 2 — `Invalid ValidateOptionId` when booking (expired across turns)

**Symptom:** `book` call returned 400 `invalidvalidateOptionid` even when using the `validate_option_id` returned by a prior `validate` call.

**Root cause:** `validate_option_id` is short-lived. The agent was calling `validate` in turn 2 (the "validate price" message) and then `book` in turn 3 (the "book it" message). By the time turn 3 executed — including full Gemini processing — the `validate_option_id` had expired.

**Fix:** Updated system prompt and tool description to enforce that `get_results → validate → book` must all happen in a **single response turn**. Also added `option_id` to session context so the agent knows which hotel was selected without re-searching.

**Files:** `agent.py`, `tools.py`

---

## Bug 3 — Agent hallucinating rate_id from session context

**Symptom:** Agent called `validate` with `rate_id='1'` (a bare integer string) instead of the correct JSON array.

**Root cause:** When `rate_id` was saved to session context and injected as a plain-text hint, Gemini parsed `[{"RtaId":1,...}]` and extracted `1` as the rate_id value (confused by the JSON structure in the hint string).

**Fix:** Removed `rate_id` from session context/hint entirely. Agent is instructed to always call `get_results` to get a fresh rate_id before validating and booking. Only `option_id` is persisted across turns.

**File:** `agent.py`, `tools.py`

---

## Bug 4 — `InvalidRateId` on validate (agent skipping get_results)

**Symptom:** When asked to validate, the agent sometimes called `get_hotel_details → validate` without calling `get_results` first, arriving at validate without a valid rate_id.

**Root cause:** The validate tool description did not make it explicit that rate_id must come from `get_results`. The agent inferred a rate_id from context or conversation history instead.

**Fix:** Updated validate tool description and system prompt: "IMPORTANT: rate_id must come from get_results best_rate.rate_id — call get_results first if you don't have it."

**Files:** `agent.py`, `tools.py`

---

## Summary

| Bug | Symptom | HTTP Error | Fix |
|-----|---------|-----------|-----|
| Gemini double-escaping RateId | InvalidRateId on validate | 400 | Unescape `\"` in client.py |
| validate_option_id expires across turns | Invalid ValidateOptionId on book | 400 | Enforce get_results→validate→book in same turn |
| Agent reads rate_id from JSON string in hint | rate_id='1' on validate | 400 | Remove rate_id from session context hint |
| Agent skips get_results before validate | InvalidRateId on validate | 400 | Enforce get_results before validate in system prompt |
