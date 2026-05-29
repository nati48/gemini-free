"""
FastAPI server that exposes the unofficial Gemini web client as an API-key gated HTTP API.

Endpoints:
  POST /v1/chat         - simple prompt -> reply
  POST /v1/chat/openai  - OpenAI-style chat/completions (so existing tools work)
  GET  /health          - is the client ready?

Auth:
  Send header `Authorization: Bearer <GEMINI_FREE_API_KEY>` on every call.
"""

from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .client import GeminiFree

load_dotenv()

API_KEY = os.getenv("GEMINI_FREE_API_KEY", "")
if not API_KEY or API_KEY == "change-me-to-a-long-random-string":
    print("⚠️  GEMINI_FREE_API_KEY is not set. Generating a random one for this run.")
    API_KEY = secrets.token_urlsafe(32)
    print(f"    Use this in the Authorization header: Bearer {API_KEY}")


def require_api_key(authorization: Optional[str] = Header(None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # warm up the client on startup so the first request isn't slow
    try:
        await GeminiFree.get()
        print("✅ Gemini client ready")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Could not init Gemini client on startup: {exc}")
    yield


app = FastAPI(title="Gemini Free API", version="0.1.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt to send to Gemini")
    model: Optional[str] = Field(None, description="e.g. 'flash', 'pro', or full enum name")
    files: Optional[list[str]] = Field(None, description="Optional file paths to attach")


class ChatResponse(BaseModel):
    model: str
    text: str
    thoughts: Optional[str] = None
    images: list[str] = []
    web_images: list[str] = []


@app.get("/health")
async def health() -> dict:
    try:
        await GeminiFree.get()
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc)}


@app.post("/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest) -> ChatResponse:
    gemini = await GeminiFree.get()
    result = await gemini.ask(req.prompt, model=req.model, files=req.files)
    return ChatResponse(**result)


# ---------- OpenAI-compatible shim ----------

class OpenAIMessage(BaseModel):
    role: str
    content: str


class OpenAIChatRequest(BaseModel):
    model: Optional[str] = "gemini-flash"
    messages: list[OpenAIMessage]
    temperature: Optional[float] = None  # ignored, here for compat
    stream: Optional[bool] = False  # ignored


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def openai_compat(req: OpenAIChatRequest) -> dict:
    """Bare-minimum OpenAI-compatible endpoint so existing tools can point at us."""
    # Flatten the messages into a single prompt; system goes first.
    parts: list[str] = []
    for msg in req.messages:
        if msg.role == "system":
            parts.append(f"[SYSTEM]\n{msg.content}")
        elif msg.role == "user":
            parts.append(f"[USER]\n{msg.content}")
        elif msg.role == "assistant":
            parts.append(f"[ASSISTANT]\n{msg.content}")
    prompt = "\n\n".join(parts)

    gemini = await GeminiFree.get()
    result = await gemini.ask(prompt, model=req.model)

    return {
        "id": f"chatcmpl-{secrets.token_hex(8)}",
        "object": "chat.completion",
        "model": result["model"],
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result["text"]},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
