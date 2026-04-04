# ADK Chatbot Template Reference
- status: active
- type: reference
- label: [normative, template, backend, frontend]
- injection: directive
- volatility: stable
- last_checked: 2026-04-06
<!-- content -->

## Overview

This reference defines the canonical architecture for ADK-powered chatbots that require a **decoupled frontend/backend** deployment. Use this pattern when you need:

- Highly customized UI (beyond what Chat Cards v2 or Streamlit can offer)
- Complex authentication (OAuth, SSO, Firebase Auth, enterprise IdP)
- Embedding the chatbot into an existing web portal or product
- Full control over streaming, theming, and responsive layout

The core principle is: **the ADK agent ecosystem is the backend; a JS/TS framework is the frontend**. They communicate over HTTP or WebSocket.

---

## Architecture

```
┌─────────────────────────────────────┐       ┌──────────────────────────────────────┐
│          FRONTEND                   │       │            BACKEND                   │
│  Next.js / React (TypeScript)       │ HTTP  │  FastAPI  (Python)                   │
│                                     │──────▶│  POST /chat   → ADK runner           │
│  - Chat UI component                │◀──────│  GET  /stream → SSE streaming        │
│  - Auth (Firebase Auth / OAuth)     │       │                                      │
│  - A2UI renderer (JSON → widgets)   │       │  ADK Agent Ecosystem                 │
│  - State management (Zustand/Redux) │       │  ├── LlmAgent (root_agent)           │
│                                     │       │  ├── Tools (MCP, custom)             │
│  Hosting: Vercel / Firebase Hosting │       │  └── Sub-agents (optional)           │
└─────────────────────────────────────┘       │                                      │
                                              │  Hosting: Cloud Run / Vertex AI      │
                                              └──────────────────────────────────────┘
```

**Data flow:**
1. User types a message → React sends `POST /chat` (or opens SSE via `GET /stream`).
2. FastAPI receives the request, calls the ADK `runner.run_async(...)`.
3. ADK agent processes the query, invokes tools/sub-agents as needed.
4. Agent emits an A2UI JSON payload (or plain text) in its final response.
5. FastAPI returns the payload to the frontend.
6. Frontend A2UI renderer maps the JSON component tree to native React widgets.

---

## Local Development Setup

### Prerequisites

| Tool | Min version | Check |
| :--- | :--- | :--- |
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

### Backend Setup (first time)

```bash
cd chatbot_template/backend

# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 2. Upgrade pip (avoids build errors)
pip install --upgrade pip

# 3. Install dependencies
#    grpcio compiles from C — takes 5-15 min on first install
#    pyarrow requires a pre-built binary wheel to avoid cmake errors
pip install --only-binary=:all: pyarrow
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=AIzaSy...
```

### Backend: Run

```bash
cd chatbot_template/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8080
```

Verify it is up: `http://localhost:8080/health` → `{"status":"ok","agent":"rocky_rps_agent"}`

### Frontend Setup (first time)

```bash
cd chatbot_template/frontend

# 1. Install dependencies
npm install

# 2. Set up environment variables
cp .env.local.example .env.local
# .env.local already points to http://localhost:8080 — no edits needed for local dev
```

### Frontend: Run

```bash
cd chatbot_template/frontend
npm run dev
```

Open **http://localhost:3000**.

### Run Both at Once (convenience script)

```bash
cd chatbot_template
./dev.sh
```

Starts both servers in the background and prints their PIDs. Press `Ctrl+C` to stop both.

### Troubleshooting

| Error | Cause | Fix |
| :--- | :--- | :--- |
| `zsh: command not found: uvicorn` | venv not activated | `source .venv/bin/activate` |
| `error: command 'cmake' failed` | pyarrow building from source | `pip install --only-binary=:all: pyarrow` |
| `grpcio` takes very long | Compiling from C source | Wait 5-15 min; check CPU with `top -o cpu` |
| `.git/index.lock: File exists` | Interrupted git operation | `rm .git/index.lock` |
| `400 API_KEY_INVALID` | Stale process, key not reloaded | Restart uvicorn (`Ctrl+C` then re-run) |
| CORS error in browser | Frontend origin not allowed | Check `allow_origins` in `main.py` |
| A2UI JSON renders as raw text | LLM wraps JSON in markdown code fences (` ```json ``` `) | Strip fences in `_parse_response` before `json.loads` — already handled in `main.py` |
| `next.config.ts` not supported | Next.js 14 doesn't support `.ts` config | Rename to `next.config.mjs` and remove TypeScript types |
| `/ 200` but browser shows nothing | Next.js still compiling on first load | Wait for `✓ Compiled /` in terminal, then refresh |
| `Could not import module "main"` | uvicorn run from wrong directory | Must run from `backend/`: `cd chatbot_template/backend && uvicorn main:app ...` |

### Rotating the API Key

1. Go to `https://aistudio.google.com/apikey`
2. Delete the old key → **Create API key** → copy the new value
3. Update `backend/.env`:
   ```bash
   echo "GOOGLE_API_KEY=AIzaSy..." > chatbot_template/backend/.env
   ```
4. Restart the backend (`Ctrl+C` → `uvicorn main:app --reload --port 8080`)

---

## Backend: FastAPI + ADK

### Project Structure

```
chatbot_template/
├── dev.sh                          # starts both servers with one command
├── backend/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py          # root_agent (Rocky RPS agent)
│   │   ├── imports.py        # centralized ADK + McpToolset imports
│   │   └── tools/            # custom tool functions (future use)
│   ├── mcp_servers/
│   │   ├── __init__.py
│   │   ├── rps_memory_server.py   # FastMCP server — session game history
│   │   └── data/                  # per-session JSON files (git-ignored)
│   ├── main.py               # FastAPI app — /chat, /stream, /health
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                  # GOOGLE_API_KEY (git-ignored)
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ChatWindow.tsx
    │   │   ├── MessageBubble.tsx
    │   │   └── A2UIRenderer.tsx   # maps A2UI JSON → React components
    │   ├── hooks/
    │   │   └── useChat.ts         # manages API calls, SSE stream, A2UI types
    │   └── app/
    │       ├── page.tsx
    │       ├── layout.tsx
    │       └── globals.css
    ├── package.json
    ├── next.config.mjs        # use .mjs — Next.js 14 does not support .ts config
    └── .env.local             # NEXT_PUBLIC_BACKEND_URL (git-ignored)
```

### `backend/agent/imports.py`

```python
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams, SseConnectionParams
from mcp import StdioServerParameters
```

### `backend/agent/agent.py`

The current implementation is **Rocky 🥊**, a Rock-Paper-Scissors agent wired to the RPS memory MCP server.

```python
import os
from .imports import LlmAgent, McpToolset, StdioConnectionParams, StdioServerParameters

_MCP_SERVER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "rps_memory_server.py")
)

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="rocky_rps_agent",
    description="Rocky — a competitive but friendly Rock-Paper-Scissors champion.",
    instruction="""
You are Rocky 🥊, a competitive but friendly Rock-Paper-Scissors champion.
Your ONLY job is to play Rock-Paper-Scissors with the user.

ROUND FLOW:
1. Call save_agent_choice(session_id, choice) immediately — pick randomly.
2. Return A2UI JSON with sealed_box + rps_selector components.
3. When user sends selected_rps_<choice>, call record_round(session_id, player_choice).
4. Call get_stats and return a reveal message with result and score.

Emoji map: 🪨 rock  📄 paper  ✂️ scissors
Trash-talk on wins. Be gracious on losses. Demand rematches on draws.
Use get_history / get_stats if user asks for past rounds or score.
For plain chat, respond in plain text — NOT JSON.
""",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="python3",
                    args=[_MCP_SERVER],
                ),
            ),
            tool_filter=["save_agent_choice", "record_round", "get_history", "get_stats"],
        )
    ],
)
```

### `backend/mcp_servers/rps_memory_server.py`

A **FastMCP** server that persists game state to per-session JSON files under `mcp_servers/data/`. Launched as a stdio subprocess by `McpToolset` — no extra terminal needed.

```python
from pathlib import Path
from mcp.server.fastmcp import FastMCP

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
mcp = FastMCP("rps-memory")

def _load(session_id):
    path = DATA_DIR / f"{session_id}.json"
    return json.loads(path.read_text()) if path.exists() else {"rounds": [], "pending_choice": None}

def _save(session_id, data):
    (DATA_DIR / f"{session_id}.json").write_text(json.dumps(data, indent=2))

@mcp.tool()
def save_agent_choice(session_id: str, choice: str) -> str:
    """Lock in the agent's choice before the player picks."""
    data = _load(session_id)
    data["pending_choice"] = choice.lower()
    _save(session_id, data)
    return "Choice saved."

@mcp.tool()
def record_round(session_id: str, player_choice: str) -> dict:
    """Evaluate the round and persist the result."""
    data = _load(session_id)
    agent = data["pending_choice"]
    player = player_choice.lower()
    result = "draw" if player == agent else ("player_wins" if BEATS[player] == agent else "agent_wins")
    entry = {"round": len(data["rounds"]) + 1, "player_choice": player, "agent_choice": agent, "result": result}
    data["rounds"].append(entry)
    data["pending_choice"] = None
    _save(session_id, data)
    return entry

@mcp.tool()
def get_history(session_id: str) -> list:
    """Return all past rounds for this session."""
    return _load(session_id)["rounds"]

@mcp.tool()
def get_stats(session_id: str) -> dict:
    """Return win/loss/draw counts."""
    rounds = _load(session_id)["rounds"]
    stats = {"player_wins": 0, "agent_wins": 0, "draws": 0, "total": len(rounds)}
    for r in rounds:
        stats[r["result"]] += 1
    return stats

if __name__ == "__main__":
    mcp.run()
```

### `backend/main.py`

```python
import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent.agent import root_agent

app = FastAPI()

# --- CORS: tighten origins in production ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # replace with your frontend domain in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
APP_NAME = "chatbot_template"

# ---------------------------------------------------------------------------
# POST /chat  — single-turn, returns full response as JSON
# ---------------------------------------------------------------------------
@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message: str = body.get("message", "").strip()
    session_id: str = body.get("session_id", "default")

    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    await session_service.create_session(
        app_name=APP_NAME, user_id=session_id, session_id=session_id
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    response_text = ""
    async for event in runner.run_async(
        user_id=session_id, session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text

    # Try to detect A2UI JSON embedded in the response
    try:
        payload = json.loads(response_text)
        return JSONResponse({"type": "a2ui", "payload": payload})
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"type": "text", "text": response_text})


# ---------------------------------------------------------------------------
# GET /stream  — streaming via Server-Sent Events (SSE)
# ---------------------------------------------------------------------------
@app.get("/stream")
async def stream(message: str, session_id: str = "default"):
    await session_service.create_session(
        app_name=APP_NAME, user_id=session_id, session_id=session_id
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=message)],
    )

    async def event_generator():
        async for event in runner.run_async(
            user_id=session_id, session_id=session_id, new_message=content
        ):
            if event.content and event.content.parts:
                chunk = event.content.parts[0].text
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### `backend/requirements.txt`

```
google-adk>=1.0.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-dotenv>=1.0.0
```

---

## Frontend: Next.js (TypeScript)

### `frontend/src/hooks/useChat.ts`

Manages API calls, SSE streaming, session persistence, and A2UI types.

```typescript
"use client";
import { useState, useCallback, useRef } from "react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080";

export type A2UIComponent =
  | { type: "text"; value: string }
  | { type: "button"; label: string; action: string }
  | { type: "card"; title: string; subtitle?: string; body: A2UIComponent[] }
  | { type: "list"; items: string[] }
  | { type: "rps_selector"; prompt?: string }     // RPS pick widget
  | { type: "sealed_box"; label?: string };        // hidden agent choice indicator

export type Message = {
  id: string;
  role: "user" | "assistant";
  type: "text" | "a2ui";
  content: string | { components: A2UIComponent[] };
};

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const sessionIdRef = useRef<string | null>(null);  // persists session across turns

  // sendMessage    — POST /chat, single-turn
  // sendMessageStream — GET /stream, SSE streaming
  // A2UI button/widget actions call sendMessage(action) to re-enter the agent loop
}
```

### `frontend/src/components/A2UIRenderer.tsx`

Maps A2UI JSON component tree to React widgets. Add new `case` blocks here to register new component types.

```typescript
"use client";
import type { A2UIComponent } from "@/hooks/useChat";

// Component registry — extend this switch as new A2UI types are added
switch (component.type) {
  case "text":       // plain paragraph
  case "button":     // action button → fires onAction(action)
  case "card":       // titled card with optional subtitle and nested body
  case "list":       // unordered list of strings
  case "rps_selector":  // 🪨📄✂️ pick buttons → fires onAction("selected_rps_<choice>")
  case "sealed_box":    // 🔒 dashed box — agent's choice locked in, not revealed yet
}
```

---

## A2UI Protocol

A2UI (Agent-to-UI) is an open protocol (Apache 2.0, by Google) where the agent returns a **declarative JSON component tree** instead of HTML or plain text. The frontend maps component types to its own native widgets — no arbitrary code execution.

### Principles

| Property | Description |
| :--- | :--- |
| **Declarative** | JSON data, not HTML/JS. Agent only references trusted component types. |
| **Framework-agnostic** | Same JSON renders in React, Flutter, SwiftUI, Angular, or Chat Cards v2. |
| **LLM-friendly** | Flat list of components with ID references, optimized for streaming. |
| **Recursive** | User interaction fires a System Event back to the agent → agent generates a new A2UI response → UI evolves without a predefined nav tree. |

### Minimal A2UI Response Schema

```json
{
  "components": [
    { "type": "text", "value": "Here are your results:" },
    {
      "type": "card",
      "title": "Result #1",
      "subtitle": "High confidence",
      "body": [
        { "type": "text", "value": "Details about result 1." },
        { "type": "button", "label": "View More", "action": "view_result_1" }
      ]
    },
    { "type": "list", "items": ["Item A", "Item B", "Item C"] }
  ]
}
```

### Registered Component Types

| Type | Schema | Action fired | Notes |
| :--- | :--- | :--- | :--- |
| `text` | `{ "type": "text", "value": "..." }` | — | Plain paragraph |
| `button` | `{ "type": "button", "label": "...", "action": "..." }` | `action` string | Generic CTA |
| `card` | `{ "type": "card", "title": "...", "subtitle": "...", "body": [...] }` | — | Nested components in `body` |
| `list` | `{ "type": "list", "items": ["...", ...] }` | — | Unordered list |
| `rps_selector` | `{ "type": "rps_selector", "prompt": "..." }` | `selected_rps_rock` / `selected_rps_paper` / `selected_rps_scissors` | 🪨📄✂️ pick buttons |
| `sealed_box` | `{ "type": "sealed_box", "label": "..." }` | — | 🔒 dashed box — agent's hidden choice |

### Instructing the Agent to Emit A2UI

Add this section to the agent's `instruction` field:

```python
instruction="""
When returning structured data or requesting user input, format your response
as a JSON object with a top-level 'components' array. Supported types:
  - text          : { "type": "text", "value": "<string>" }
  - button        : { "type": "button", "label": "<string>", "action": "<string>" }
  - card          : { "type": "card", "title": "<string>", "subtitle": "<string>", "body": [...] }
  - list          : { "type": "list", "items": ["<string>", ...] }
  - rps_selector  : { "type": "rps_selector", "prompt": "<string>" }
  - sealed_box    : { "type": "sealed_box", "label": "<string>" }
For plain conversational replies, respond in normal text — NOT JSON.
"""
```

### Code Fence Stripping

The LLM often wraps JSON in markdown code fences (` ```json ... ``` `) even when instructed not to. `_parse_response` in `main.py` strips the fences before calling `json.loads`:

```python
if stripped.startswith("```"):
    lines = stripped.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    stripped = "\n".join(lines).strip()
```

---

## Authentication

For complex auth or portal embedding, decouple auth from the agent:

| Scenario | Recommended approach |
| :--- | :--- |
| Firebase Auth (email / Google sign-in) | Firebase SDK on frontend → ID token in `Authorization: Bearer` header → FastAPI verifies with `firebase-admin` |
| Enterprise SSO / OAuth 2.0 | NextAuth.js on frontend → JWT forwarded to backend |
| Internal portal (GCP-native) | Cloud IAP in front of Cloud Run → no custom auth code needed |
| Public chatbot | Rate-limit by IP at the Cloud Run / Vercel edge level |

### FastAPI token verification (Firebase example)

```python
from fastapi import Depends, HTTPException, Header
from firebase_admin import auth, credentials, initialize_app

initialize_app(credentials.ApplicationDefault())

async def verify_token(authorization: str = Header(...)) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/chat")
async def chat(request: Request, user: dict = Depends(verify_token)):
    ...
```

---

## Deployment

### Backend → Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/chatbot-backend ./backend

# Deploy to Cloud Run (us-central1 per cost policy)
gcloud run deploy chatbot-backend \
  --image gcr.io/YOUR_PROJECT/chatbot-backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=YOUR_KEY
```

### Backend → Vertex AI Agent Engine (ADK-native)

```python
import vertexai
from vertexai.preview import reasoning_engines
from agent.agent import root_agent

vertexai.init(project="YOUR_PROJECT", location="us-central1")

app = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)

remote_app = reasoning_engines.ReasoningEngine.create(
    app,
    requirements=["google-adk", "fastapi"],
    display_name="chatbot-template",
)
```

### Frontend → Vercel

```bash
cd frontend
vercel --prod
# Set NEXT_PUBLIC_BACKEND_URL=https://chatbot-backend-xxxx.run.app in Vercel env vars
```

### Frontend → Firebase Hosting

```bash
cd frontend
npm run build        # Next.js static export or SSR via Cloud Run
firebase deploy --only hosting
```

---

## Environment Variables

| Variable | Location | Description |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | `backend/.env` / Cloud Run secret | Gemini API key |
| `GOOGLE_CLOUD_PROJECT` | Cloud Run env | GCP project for Vertex AI billing |
| `NEXT_PUBLIC_BACKEND_URL` | `frontend/.env.local` / Vercel | FastAPI backend URL |
| `FIREBASE_PROJECT_ID` | `backend/.env` | Firebase project (if using Auth) |

---

## Key External References

| Resource | URL |
| :--- | :--- |
| ADK Documentation | `https://google.github.io/adk-docs/` |
| A2UI Official Site | `https://a2ui.org` |
| A2UI GitHub | `https://github.com/google/A2UI` |
| FastAPI Docs | `https://fastapi.tiangolo.com` |
| Cloud Run Quickstart | `https://cloud.google.com/run/docs/quickstarts` |
| Vertex AI Agent Engine | `https://cloud.google.com/vertex-ai/docs/reasoning-engines/overview` |
| Firebase Hosting | `https://firebase.google.com/docs/hosting` |
| NextAuth.js | `https://next-auth.js.org` |
