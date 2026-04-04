# ADK Chatbot Skill
- status: active
- type: how-to
- label: [skill, backend, frontend]
- injection: procedural
- volatility: evolving
- last_checked: 2026-04-06
<!-- content -->

## Overview

This skill describes how to build a production-ready ADK chatbot from scratch using a **decoupled frontend/backend architecture**. The backend is a Python FastAPI service wrapping an ADK agent ecosystem. The frontend is a Next.js (TypeScript) app that communicates with it over HTTP. The agent can return plain text or structured A2UI JSON payloads that the frontend renders as rich interactive widgets.

Use this pattern when you need custom UI, complex authentication, or want to embed the chatbot into an existing web portal. For simple prototypes, `adk web` is sufficient.

---

## Prerequisites

| Tool | Min version | Check |
| :--- | :--- | :--- |
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Google API key | — | `https://aistudio.google.com/apikey` |

---

## Steps

### 1. Scaffold the backend

```bash
mkdir my_chatbot && cd my_chatbot
mkdir -p backend/agent/tools backend/mcp_servers frontend

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --only-binary=:all: pyarrow   # avoids cmake build errors
pip install google-adk fastapi "uvicorn[standard]" python-dotenv pydantic
```

Create `backend/.env`:
```
GOOGLE_API_KEY=AIzaSy...
```

### 2. Centralise ADK imports

`backend/agent/imports.py` — single source of truth for all ADK classes:

```python
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
# MCP support (add when needed)
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams, SseConnectionParams
from mcp import StdioServerParameters
```

Never scatter these imports across tool files — always import from `imports.py`.

### 3. Define the agent

`backend/agent/agent.py`:

```python
from .imports import LlmAgent

root_agent = LlmAgent(
    model="gemini-2.5-flash",   # cheapest model that supports tool use + A2UI
    name="my_chatbot_agent",
    description="One-line description of what this agent does.",
    instruction="""
You are a helpful assistant.
[Describe the agent's personality, task scope, and any A2UI output rules here.]
For plain conversational replies, respond in normal text — NOT JSON.
""",
    tools=[],   # add Python functions or McpToolset instances here
)
```

`backend/agent/__init__.py`:
```python
from .agent import root_agent
__all__ = ["root_agent"]
```

### 4. Choose agent type and tools

ADK provides three agent categories. Use the right one for each task:

| Agent type | ADK class | When to use |
| :--- | :--- | :--- |
| **LLM Agent** | `LlmAgent` | Natural language tasks, tool selection, A2UI output |
| **Sequential** | `SequentialAgent` | Fixed multi-step pipelines (research → draft → review) |
| **Parallel** | `ParallelAgent` | Independent concurrent tasks (fan-out research) |
| **Loop** | `LoopAgent` | Iterative refinement until a condition is met |

Tools can be:
- **Plain Python functions** — decorated or passed directly to `tools=[...]`
- **MCP Toolsets** — `McpToolset(connection_params=StdioConnectionParams(...))` connects to an external MCP server (filesystem, memory, APIs, custom servers)
- **Built-in tools** — `google_search`, code executor, BigQuery, Vertex AI

See `ADK_SKILL.md` and `ADK_MCP_REF.md` for detailed tool and MCP reference.

### 5. Wire the FastAPI backend

`backend/main.py` exposes two endpoints:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/chat` | POST | Single-turn: waits for full response, returns JSON |
| `/stream` | GET | Streaming: Server-Sent Events, chunks arrive progressively |
| `/health` | GET | Liveness check |

Key patterns in `main.py`:
- Use `InMemorySessionService` for local dev; replace with a persistent store for production.
- Strip markdown code fences from the LLM response before parsing A2UI JSON (LLMs often wrap JSON in ` ```json ``` `).
- Return `{ "type": "a2ui", "payload": {...} }` for A2UI responses and `{ "type": "text", "text": "..." }` for plain text.

### 6. Scaffold the frontend

```bash
cd my_chatbot/frontend
npx create-next-app@14 . --typescript --app --no-tailwind --no-eslint --src-dir --import-alias "@/*"
```

Key files:
- `src/hooks/useChat.ts` — manages `POST /chat` and `GET /stream` calls, session ID persistence, A2UI type union
- `src/components/A2UIRenderer.tsx` — switch-based component registry mapping A2UI JSON → React widgets
- `src/components/ChatWindow.tsx` — input bar, message list, streaming toggle
- `src/components/MessageBubble.tsx` — renders text or A2UI messages

Create `frontend/.env.local`:
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8080
```

For the A2UI renderer pattern and component registry, see `A2UI_REF.md`.

### 7. Run locally

**Backend** (terminal 1):
```bash
cd my_chatbot/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8080
```

Verify: `http://localhost:8080/health`

**Frontend** (terminal 2):
```bash
cd my_chatbot/frontend
npm run dev
```

Open: `http://localhost:3000`

> **Important:** always run uvicorn from inside the `backend/` directory. Running it from the project root causes `Could not import module "main"`.

### 8. Deploy to Google Cloud

#### Backend → Cloud Run

```bash
# Build and push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/my-chatbot-backend ./backend

# Deploy (us-central1 is cheapest per INFRASTRUCTURE_DEFINITIONS_REF.md)
gcloud run deploy my-chatbot-backend \
  --image gcr.io/YOUR_PROJECT/my-chatbot-backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=YOUR_KEY
```

`backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --only-binary=:all: pyarrow && pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### Backend → Vertex AI Agent Engine (ADK-native)

```python
import vertexai
from vertexai.preview import reasoning_engines
from agent.agent import root_agent

vertexai.init(project="YOUR_PROJECT", location="us-central1")
app = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)
reasoning_engines.ReasoningEngine.create(
    app,
    requirements=["google-adk", "fastapi"],
    display_name="my-chatbot",
)
```

#### Frontend → Firebase Hosting

```bash
cd frontend
npm run build
firebase deploy --only hosting
# Set NEXT_PUBLIC_BACKEND_URL=https://my-chatbot-backend-xxxx.run.app in Firebase env
```

#### Frontend → Vercel

```bash
cd frontend
vercel --prod
# Set NEXT_PUBLIC_BACKEND_URL in Vercel project environment variables
```

---

## Agent-to-UI (A2UI)

When the agent needs to return structured UI — buttons, cards, selectors, charts — it emits a JSON payload with a `components` array instead of plain text. The frontend's `A2UIRenderer` maps each component type to a native React widget. User interactions (button clicks, option selections) are sent back to the agent as plain-text messages, creating a recursive conversational UI loop.

See `A2UI_REF.md` for the full protocol, component registry, extension pattern, and implementation details.

---

## Notes

- **Model choice:** default to `gemini-2.5-flash` for all chatbots. It supports tool use, MCP, and A2UI output at the lowest cost. Use `gemini-2.5-pro` only for deep reasoning tasks.
- **`grpcio` build time:** compiles from C source on first install — allow 5-15 minutes.
- **`pyarrow`:** always install with `--only-binary=:all:` to avoid a cmake dependency.
- **Next.js config:** use `next.config.mjs` — Next.js 14 does not support `next.config.ts`.
- **MCP servers:** spawned as subprocesses by `McpToolset` — no extra terminal needed. For session-persistent state, use file-backed storage in the MCP server (see `ADK_A2UICHATBOT_REF.md` RPS example).
- **Token efficiency:** always provide a minimal `tool_filter` on `McpToolset`. Exposing unused tool schemas wastes context and increases cost.
