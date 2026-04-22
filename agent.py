import logging
from typing import Any

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

SYSTEM_PROMPT = """You are Amelia, a hotel booking assistant for Karta, a premium credit card company.

You help clients search for hotels, review options, validate prices, make reservations, and cancel bookings.

Rules:
- Always respond in the same language the user writes in.
- Always resolve city names to a LocationId using the search_location tool — never guess IDs.
- Always validate price and cancellation policy before booking.
- Before booking, confirm passenger details with the user.
- Never log or repeat sensitive data like document numbers or emails in your responses.
- Be concise and professional.
"""


def _build_model(tools: list[Any] | None = None) -> genai.GenerativeModel:
    kwargs: dict[str, Any] = {
        "model_name": settings.gemini_model,
        "system_instruction": SYSTEM_PROMPT,
    }
    if tools:
        kwargs["tools"] = tools
    return genai.GenerativeModel(**kwargs)


def _to_gemini_history(messages: list[dict]) -> list[dict]:
    """Convert internal message list to Gemini content format.

    Internal format: [{"role": "user"|"assistant", "content": "..."}]
    Gemini format:   [{"role": "user"|"model",      "parts": ["..."]}]
    """
    result = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        result.append({"role": role, "parts": [msg["content"]]})
    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def send_message(
    messages: list[dict],
    tools: list[Any] | None = None,
) -> genai.types.GenerateContentResponse:
    """Send a conversation to Gemini and return the raw response.

    Args:
        messages: Full conversation history in internal format.
                  Last message must be from the user.
        tools:    Gemini tool definitions (added in Etapa 9).

    Returns:
        Gemini GenerateContentResponse.
    """
    model = _build_model(tools)
    history = _to_gemini_history(messages[:-1])  # everything except last
    last = messages[-1]["content"]

    chat = model.start_chat(history=history)
    response = chat.send_message(last)
    return response


def extract_text(response: genai.types.GenerateContentResponse) -> str:
    """Extract plain text from a Gemini response."""
    return response.text
