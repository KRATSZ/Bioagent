from __future__ import annotations

from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .graph import build_graph, GraphState
from .intent import parse_intent, Intent


class ChatRequest(BaseModel):
    text: str
    dry_run: bool = False


class ChatResponse(BaseModel):
    text: str


class IntentRequest(BaseModel):
    text: str


class IntentResponse(Intent):
    pass


app = FastAPI(title="Momentum LLM Control API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
graph_app, momentum = build_graph()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        out = graph_app.invoke(GraphState(user_input=payload.text, dry_run=payload.dry_run))
        return ChatResponse(text=out.result or "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat error: {e}")


@app.post("/intent", response_model=IntentResponse)
def inspect_intent(payload: IntentRequest) -> IntentResponse:
    try:
        intent = parse_intent(payload.text)
        return IntentResponse(**intent.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"intent error: {e}")




