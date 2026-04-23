"""Gemini function calling tools — bridges AI decisions to Netactica API calls."""
import json
import logging
from typing import Optional

import google.generativeai as genai

import netactica.client as client

logger = logging.getLogger(__name__)

# Session ID injected by main.py before each request so tools can update context
_current_session_id: Optional[str] = None


def set_session(session_id: str) -> None:
    global _current_session_id
    _current_session_id = session_id

# ---------------------------------------------------------------------------
# Tool definitions (what Gemini sees)
# ---------------------------------------------------------------------------

TOOLS = [
    genai.protos.Tool(function_declarations=[
        genai.protos.FunctionDeclaration(
            name="search_location",
            description="Resolve a city or destination name to a LocationId. Always call this first before searching for hotels — never guess LocationIds.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "city": genai.protos.Schema(type=genai.protos.Type.STRING, description="City or destination name, e.g. 'Cancun', 'Playa del Carmen'"),
                },
                required=["city"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="search_hotels",
            description="Start a hotel search and return a SearchId. The search is asynchronous — call get_results afterwards to get the hotel list.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "location_id": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="LocationId from search_location"),
                    "checkin":     genai.protos.Schema(type=genai.protos.Type.STRING,  description="Check-in date in YYYY-MM-DD format"),
                    "checkout":    genai.protos.Schema(type=genai.protos.Type.STRING,  description="Check-out date in YYYY-MM-DD format"),
                    "adults":      genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Number of adults (default 2)"),
                    "children":    genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Number of children (default 0)"),
                },
                required=["location_id", "checkin", "checkout"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="get_results",
            description="Fetch hotel results for a SearchId with optional filters. Returns a list of hotels with prices.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "search_id":      genai.protos.Schema(type=genai.protos.Type.STRING, description="SearchId from search_hotels"),
                    "categories":     genai.protos.Schema(type=genai.protos.Type.STRING, description="Star ratings as comma-separated string, e.g. '4,5'"),
                    "refundable_only":genai.protos.Schema(type=genai.protos.Type.BOOLEAN,description="Only show refundable hotels"),
                    "price_from":     genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Minimum price"),
                    "price_to":       genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Maximum price"),
                    "order_by":       genai.protos.Schema(type=genai.protos.Type.STRING, description="Sort order: RECOMENDATION, PRICE, CATEGORY, SCORE"),
                    "limit":          genai.protos.Schema(type=genai.protos.Type.INTEGER,description="Max number of results (default 10)"),
                },
                required=["search_id"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="get_hotel_details",
            description="Get extended hotel info: images, amenities, reviews and cancellation policies for a specific hotel option.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "search_id": genai.protos.Schema(type=genai.protos.Type.STRING,  description="SearchId from search_hotels"),
                    "option_id": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="OptionId from get_results"),
                },
                required=["search_id", "option_id"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="validate",
            description="Validate price and availability before booking. Always call this before book. Returns validate_option_id and config_doc_id needed for booking. IMPORTANT: rate_id must come from get_results best_rate.rate_id — call get_results first if you don't have it.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "search_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="SearchId from search_hotels"),
                    "option_id": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="OptionId from get_results"),
                    "rate_id":   genai.protos.Schema(type=genai.protos.Type.STRING,  description="RateId from get_results best_rate"),
                },
                required=["search_id", "option_id", "rate_id"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="book",
            description="Create a hotel reservation. Requires passenger info collected from the user. Booking and confirmation are handled in a single call.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "validate_option_id": genai.protos.Schema(type=genai.protos.Type.STRING, description="ValidateOptionId from validate"),
                    "config_doc_id":      genai.protos.Schema(type=genai.protos.Type.INTEGER,description="ConfigDocId from validate"),
                    "first_name":         genai.protos.Schema(type=genai.protos.Type.STRING, description="Passenger first name"),
                    "last_name":          genai.protos.Schema(type=genai.protos.Type.STRING, description="Passenger last name"),
                    "gender":             genai.protos.Schema(type=genai.protos.Type.STRING, description="'Male' or 'Female' (full word)"),
                    "document_number":    genai.protos.Schema(type=genai.protos.Type.STRING, description="Passport or ID number"),
                    "nationality":        genai.protos.Schema(type=genai.protos.Type.STRING, description="ISO 2-letter country code, e.g. MX, BR, US"),
                    "dob":                genai.protos.Schema(type=genai.protos.Type.STRING, description="Date of birth in YYYY-MM-DD format"),
                    "phone":              genai.protos.Schema(type=genai.protos.Type.STRING, description="Phone number with country code"),
                    "email":              genai.protos.Schema(type=genai.protos.Type.STRING, description="Email address"),
                },
                required=["validate_option_id", "config_doc_id", "first_name", "last_name",
                          "gender", "document_number", "nationality", "dob", "phone", "email"],
            ),
        ),
        genai.protos.FunctionDeclaration(
            name="cancel",
            description="Cancel an existing hotel reservation.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "reservation_id": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="ReservationId to cancel"),
                },
                required=["reservation_id"],
            ),
        ),
    ])
]


# ---------------------------------------------------------------------------
# Tool executor (what happens when Gemini calls a tool)
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: dict) -> str:
    """Execute a tool call from Gemini and return the result as a JSON string."""
    logger.info("Tool call: %s(%s)", name, list(args.keys()))
    try:
        result = _dispatch(name, args)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.warning("Tool %s failed: %s", name, e)
        if name == "validate":
            return json.dumps({"error": "This hotel option could not be validated (the supplier returned an error). Inform the user that this option is unavailable and ask them to choose a different hotel from the list. Do not call any other tools."})
        return json.dumps({"error": str(e)})


def _dispatch(name: str, args: dict):
    if name == "search_location":
        loc = client.search_location(args["city"])
        # Rename Id → location_id so Gemini can chain directly to search_hotels
        return {"location_id": loc["Id"], "name": loc["NameFull"]}

    if name == "search_hotels":
        search_id = client.search_hotels(
            location_id=int(args["location_id"]),  # Gemini returns floats for integers
            checkin=args["checkin"],
            checkout=args["checkout"],
            adults=int(args.get("adults", 2)),
            children=int(args.get("children", 0)),
        )
        # New search resets booking context — previous option_id and reservation_id
        # are no longer valid for this search
        if _current_session_id:
            from sessions import update_context
            update_context(_current_session_id, search_id=search_id, option_id=None, reservation_id=None)
        return {"search_id": search_id}

    if name == "get_results":
        categories = None
        if args.get("categories"):
            categories = [c.strip() for c in args["categories"].split(",")]
        return client.get_results(
            search_id=args["search_id"],
            categories=categories,
            refundable_only=args.get("refundable_only", False),
            price_from=args.get("price_from"),
            price_to=args.get("price_to"),
            order_by=args.get("order_by", "RECOMENDATION"),
            limit=int(args.get("limit", 10)),  # Gemini returns floats for integers
        )

    if name == "get_hotel_details":
        return client.get_hotel_details(args["search_id"], int(args["option_id"]))

    if name == "validate":
        result = client.validate(args["search_id"], int(args["option_id"]), args["rate_id"])
        # Save option_id so agent remembers which hotel was selected across turns
        if _current_session_id:
            from sessions import update_context
            update_context(_current_session_id, option_id=int(args["option_id"]))
        return result

    if name == "book":
        traveler = {
            "RoomNumber": 1,
            "PaxType": "Adult",
            "Gender": args["gender"],
            "FirstName": args["first_name"],
            "LastName": args["last_name"],
            "Phone": args["phone"],
            "Email": args["email"],
            "DocumentNumber": args["document_number"],
            "ConfigurationDocumentId": int(args["config_doc_id"]),
            "Nationality": args["nationality"].upper(),
            "DOB": args["dob"],
        }
        b = client.book(args["validate_option_id"], [traveler])
        # Persist reservation_id before confirm — so even if confirm fails,
        # the agent knows the reservation exists and can inform the user
        if _current_session_id:
            from sessions import update_context
            update_context(_current_session_id, reservation_id=b["reservation_id"])
        try:
            c = client.confirm(b["reservation_id"])
            confirmed = c["status"] == "Confirm"
            supplier_reference = c.get("supplier_reference")
        except Exception as e:
            logger.warning("Confirm failed for reservation %s: %s", b["reservation_id"], e)
            confirmed = False
            supplier_reference = None
        return {**b, "confirmed": confirmed, "supplier_reference": supplier_reference}

    if name == "cancel":
        return client.cancel(int(args["reservation_id"]))

    raise ValueError(f"Unknown tool: {name}")
