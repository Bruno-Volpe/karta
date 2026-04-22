from fastapi import FastAPI
from models.chat import ChatRequest, ChatResponse

app = FastAPI(title="Amelia", description="Hotel booking AI agent")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return ChatResponse(session_id=request.session_id, message="(stub)")
