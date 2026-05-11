import os
import json
import time
import uuid
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


# Stage-level latency instrumentation — see content/how-to/LLM_LATENCY_SKILL.md.
# Emitted to stdout so Cloud Run / Cloud Logging captures them. Grep with
# `gcloud run services logs read ... | grep '\[LATENCY\]'`.
@contextmanager
def log_latency(stage: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[LATENCY] {stage}: {elapsed_ms:.1f}ms", flush=True)

load_dotenv()

# ---------------------------------------------------------------------------
# Lazy agent import — ADK requires GOOGLE_API_KEY to be set before import
# ---------------------------------------------------------------------------
from agent import root_agent

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
APP_NAME = "chatbot_template"
session_service = InMemorySessionService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Backend ready. root_agent:", root_agent.name)
    yield


app = FastAPI(title="ADK Chatbot Backend", lifespan=lifespan)

# CORS origins are read from ALLOWED_ORIGINS (comma-separated). In production
# the backend is deployed IAM-only and is reached exclusively via the Next.js
# server-side proxy in the frontend, which means no browser ever performs a
# cross-origin request against this service. ALLOWED_ORIGINS is therefore
# expected to be empty (or unset) in production. For local dev set
# ALLOWED_ORIGINS=http://localhost:3000 in backend/.env.
_allowed = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_runner(session_id: str) -> Runner:
    return Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )


async def _ensure_session(session_id: str) -> None:
    """Create session if it doesn't already exist."""
    try:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=session_id,
            session_id=session_id,
        )
    except Exception:
        pass  # session already exists


def _parse_response(text: str) -> dict:
    """Try to detect an A2UI JSON payload; fall back to plain text."""
    stripped = text.strip()

    # Strip markdown code fences the LLM may add (```json ... ``` or ``` ... ```)
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove opening fence (```json or ```)
        lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
            if "components" in payload:
                return {"type": "a2ui", "payload": payload}
        except json.JSONDecodeError:
            pass
    return {"type": "text", "text": text}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # auto-generated if not provided


# ---------------------------------------------------------------------------
# POST /chat  — single-turn, returns full response as JSON
# ---------------------------------------------------------------------------

@app.post("/chat")
async def chat(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    session_id = body.session_id or str(uuid.uuid4())

    with log_latency("ensure_session"):
        await _ensure_session(session_id)

    with log_latency("make_runner"):
        runner = _make_runner(session_id)

    content = types.Content(
        role="user",
        parts=[types.Part(text=body.message)],
    )

    response_text = ""
    with log_latency("chat:runner_run"):
        async for event in runner.run_async(
            user_id=session_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text or ""

    return JSONResponse(
        content={"session_id": session_id, **_parse_response(response_text)}
    )


# ---------------------------------------------------------------------------
# GET /stream  — streaming via Server-Sent Events (SSE)
# ---------------------------------------------------------------------------

@app.get("/stream")
async def stream(
    message: str = Query(..., description="User message"),
    session_id: str = Query(default=None, description="Session ID"),
):
    if not message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    session_id = session_id or str(uuid.uuid4())

    with log_latency("ensure_session"):
        await _ensure_session(session_id)

    with log_latency("make_runner"):
        runner = _make_runner(session_id)

    content = types.Content(
        role="user",
        parts=[types.Part(text=message)],
    )

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        # Track time-to-first-chunk separately from total stream time — the
        # first matters for perceived latency, the second for end-to-end cost.
        t0 = time.perf_counter()
        first_chunk_logged = False

        async for event in runner.run_async(
            user_id=session_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                chunk = event.content.parts[0].text or ""
                if chunk:
                    if not first_chunk_logged:
                        elapsed_ms = (time.perf_counter() - t0) * 1000
                        print(f"[LATENCY] stream:time_to_first_chunk: {elapsed_ms:.1f}ms", flush=True)
                        first_chunk_logged = True
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"

        total_ms = (time.perf_counter() - t0) * 1000
        print(f"[LATENCY] stream:total: {total_ms:.1f}ms", flush=True)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "agent": root_agent.name}
