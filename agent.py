import logging
from typing import Any

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted

from config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

SYSTEM_PROMPT = """You are Amelia, a hotel booking assistant for Karta, a premium credit card company.

You help clients search for hotels, review options, validate prices, make reservations, and cancel bookings.

Rules:
- Respond in English by default. Switch to the user's language if they write in another language.
- Always call search_location before search_hotels — never guess LocationIds.
- To validate or book a hotel you MUST have the rate_id from get_results. Always call get_results to get a fresh rate_id for the chosen option_id — never guess it.
- When booking: call get_results → validate → book in the same response. The validate_option_id expires immediately — these three calls must happen in the same turn.
- Before calling book, you must have all passenger details. If the user provides them in their message, use them directly.
- Never repeat sensitive data (document numbers, emails) in your responses.
- Be concise and professional.
- When showing hotel lists, include: name, stars, price, refundable status.
- When showing cancellation policies, use clear human-readable dates.
"""


def _build_model(tools=None) -> genai.GenerativeModel:
    kwargs: dict[str, Any] = {
        "model_name": settings.gemini_model,
        "system_instruction": SYSTEM_PROMPT,
    }
    if tools:
        kwargs["tools"] = tools
    return genai.GenerativeModel(**kwargs)


def _to_gemini_history(messages: list[dict]) -> list[dict]:
    """Convert internal message list to Gemini content format."""
    result = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        result.append({"role": role, "parts": [msg["content"]]})
    return result


def _context_message(context: dict) -> str | None:
    """Build a context hint for the agent based on current session state."""
    if not context:
        return None
    parts = []
    if context.get("search_id"):
        parts.append(f"search_id: {context['search_id']}")
    if context.get("option_id"):
        parts.append(f"selected option_id: {context['option_id']}")
    if context.get("reservation_id"):
        parts.append(f"reservation_id: {context['reservation_id']}")
    if not parts:
        return None
    return "[Session context: " + " | ".join(parts) + ". Use these IDs — do not start a new search unless the user asks for a different hotel.]"


def run(messages: list[dict], context: dict | None = None) -> str:
    """Run the agent loop, distinguishing rate limit errors from transient failures."""
    try:
        return _run(messages, context)
    except ResourceExhausted as e:
        logger.error("Gemini rate limit hit: %s", e)
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _run(messages: list[dict], context: dict | None = None) -> str:
    """Run the agent loop: send messages, handle tool calls, return final text.

    Handles multi-turn tool calling: Gemini may call multiple tools in sequence
    before producing a final text response.
    """
    from tools import TOOLS, execute_tool

    model = _build_model(TOOLS)
    history = _to_gemini_history(messages[:-1])
    last = messages[-1]["content"]

    # Inject session context so agent doesn't re-search unnecessarily
    ctx_hint = _context_message(context or {})
    if ctx_hint:
        last = f"{ctx_hint}\n\n{last}"

    chat = model.start_chat(history=history)
    response = chat.send_message(last)

    # Tool calling loop
    while True:
        # Collect all function calls in this response
        calls = [
            part.function_call
            for candidate in response.candidates
            for part in candidate.content.parts
            if part.function_call.name
        ]

        if not calls:
            break

        # Execute all tool calls and send results back
        tool_results = []
        for call in calls:
            result = execute_tool(call.name, dict(call.args))
            tool_results.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=call.name,
                        response={"result": result},
                    )
                )
            )

        response = chat.send_message(tool_results)

    return response.text


def extract_text(response) -> str:
    """Kept for backwards compatibility with smoke tests."""
    return response.text
