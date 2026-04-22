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
- Always call search_location before search_hotels — never guess LocationIds.
- Always call validate before book — price may have changed.
- Before calling book, confirm all passenger details with the user.
- After book, always call confirm to finalize with the supplier.
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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def run(messages: list[dict]) -> str:
    """Run the agent loop: send messages, handle tool calls, return final text.

    Handles multi-turn tool calling: Gemini may call multiple tools in sequence
    before producing a final text response.
    """
    from tools import TOOLS, execute_tool

    model = _build_model(TOOLS)
    history = _to_gemini_history(messages[:-1])
    last = messages[-1]["content"]

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
