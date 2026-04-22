from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Amelia", description="Hotel booking AI agent")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # stub — será implementado na Etapa 12
    return ChatResponse(session_id=request.session_id, message="(stub)")
