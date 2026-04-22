"""Structured output — extracts passenger data from natural language using Gemini."""
import json
import logging

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

_EXTRACTION_PROMPT = """Extract passenger booking information from the text below.

Rules:
- gender: must be exactly "Male" or "Female"
- nationality: ISO 2-letter country code (e.g. MX, BR, US, AR)
- dob: YYYY-MM-DD format
- Return null for any field not mentioned in the text.

Text: {text}
"""

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "first_name":       {"type": "string"},
        "last_name":        {"type": "string"},
        "gender":           {"type": "string", "enum": ["Male", "Female"]},
        "document_number":  {"type": "string"},
        "nationality":      {"type": "string"},
        "dob":              {"type": "string"},
        "phone":            {"type": "string"},
        "email":            {"type": "string"},
    },
}


def extract_traveler(text: str) -> dict:
    """Extract structured passenger data from a natural language string.

    Returns a dict with the extracted fields. Missing fields are omitted.
    Raises ValueError if mandatory fields (first_name, last_name, gender,
    document_number, nationality, dob) cannot be extracted.
    """
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        ),
    )

    response = model.generate_content(_EXTRACTION_PROMPT.format(text=text))
    data: dict = json.loads(response.text)

    # Remove null values
    data = {k: v for k, v in data.items() if v is not None}

    # Normalize
    if "nationality" in data:
        data["nationality"] = data["nationality"].upper()

    logger.info("Extracted traveler fields: %s", list(data.keys()))
    return data


REQUIRED_FIELDS = {"first_name", "last_name", "gender", "document_number", "nationality", "dob"}


def missing_traveler_fields(data: dict) -> list[str]:
    """Return list of required fields not yet present in data."""
    return [f for f in REQUIRED_FIELDS if not data.get(f)]
