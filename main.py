import logging

from fastapi import FastAPI, HTTPException

from models.chat import ChatRequest, ChatResponse
from sessions import get_session, save_session, append_message
from agent import run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Amelia", description="Hotel booking AI agent")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session = get_session(request.session_id)

    # Append user message to history
    append_message(request.session_id, "user", request.message)

    # Reload session to get updated messages
    session = get_session(request.session_id)

    try:
        response_text = run(session["messages"])
    except Exception as e:
        logger.error("Agent error for session %s: %s", request.session_id, e)
        raise HTTPException(status_code=500, detail="Agent error. Please try again.")

    # Persist assistant response
    append_message(request.session_id, "assistant", response_text)

    return ChatResponse(session_id=request.session_id, message=response_text)


@app.get("/sessions/{session_id}/history")
def get_history(session_id: str):
    session = get_session(session_id)
    return {"session_id": session_id, "messages": session["messages"], "context": session["context"]}
