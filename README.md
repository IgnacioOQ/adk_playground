---
status: active
type: reference
description: Top-level guide to the ADK Playground repo — Google Agent Development Kit concepts, the agent projects it contains, local Markdown-JSON conventions, and the session worklog format.
label: [core, template]
injection: informational
volatility: evolving
last_checked: '2026-05-20'
---
# ADK Playground

This repository is a playground and central nervous system for learning and experimenting with Google's Agent Development Kit (ADK). It collects several self-contained agent projects — a getting-started tutorial agent, an MCP tool-integration example, a workflow-agents pipeline, a visual drag-and-drop designer, and a production chatbot template — alongside the local conventions that keep them consistent. Start here for a map of what the repo contains and how it is organized; reach for the per-project guides in the knowledge base for implementation detail.

## What is Google ADK?
The Agent Development Kit (ADK) is a flexible and modular framework developed by Google for building and deploying AI agents. While optimized for Gemini and the Google ecosystem, ADK is model-agnostic, deployment-agnostic, and designed to make agentic architectures feel more like traditional software development.

https://google.github.io/adk-docs/agents/

This repository serves as a playground and central nervous system for learning and experimenting with ADK concepts.

## Core Agent Categories
ADK provides distinct agent categories to build sophisticated applications:

1. **LLM Agents** (`LlmAgent`): These agents utilize Large Language Models (LLMs) as their core engine to understand natural language, reason, plan, generate responses, and dynamically decide how to proceed or which tools to use. They are ideal for flexible, language-centric tasks.
2. **Workflow Agents** (`SequentialAgent`, `ParallelAgent`, `LoopAgent`): These specialized agents control the execution flow of other agents in predefined, deterministic patterns (sequence, parallel, or loop) without using an LLM for the flow control itself. They are perfect for structured processes needing predictable execution.
3. **Custom Agents** (`BaseAgent`): Created by extending the `BaseAgent` directly, these allow you to implement unique operational logic, specific control flows, or specialized integrations not covered by the standard types.

## Multi-Agent Architecture
While each agent type serves a distinct purpose, complex applications frequently employ multi-agent architectures where:
- LLM Agents handle intelligent, language-based task execution.
- Workflow Agents manage the overall process flow using standard patterns.
- Custom Agents provide specialized capabilities or rules needed for unique integrations.

## Extending Capabilities
Beyond the core agent types, ADK allows significantly expanding what agents can do through:

- **AI Models**: Swap the underlying intelligence by integrating with generative AI models from Google and other providers.
- **Artifacts**: Enable agents to create and manage persistent outputs like files, code, or documents.
- **Pre-built Tools & Integrations**: Equip agents with tools to interact with the world (e.g., search, code execution).
- **Custom Tools**: Create your own task-specific tools.
- **Plugins**: Integrate complex, pre-packaged behaviors and third-party services.
- **Skills**: Use prebuilt or custom Agent Skills efficiently inside AI context limits.
- **Callbacks**: Hook into specific events during execution to add logging, monitoring, or custom side-effects.

## MCP (Model Context Protocol) Integration
ADK agents can consume external tool servers that speak the [Model Context Protocol](https://modelcontextprotocol.io/). The `McpToolset` class handles the full lifecycle:

1. **Spawn** — starts the MCP server process (stdio) or opens an SSE connection (remote).
2. **Discover** — calls `list_tools` on the server and adapts schemas to ADK format.
3. **Proxy** — routes the LLM's tool-call requests to the server transparently.

**Key classes** (all exported from each agent's `imports.py`):

| Class | Module | Purpose |
| :--- | :--- | :--- |
| `McpToolset` | `google.adk.tools.mcp_tool` | Top-level ADK wrapper for an MCP server |
| `StdioConnectionParams` | `google.adk.tools.mcp_tool.mcp_session_manager` | Launch a local MCP server subprocess |
| `SseConnectionParams` | `google.adk.tools.mcp_tool.mcp_session_manager` | Connect to a remote MCP server over SSE |
| `StdioServerParameters` | `mcp` | Shell command + args to spawn the server |

**Prerequisites for the filesystem example**: Node.js and `npx` must be available (`node --version`).

## Installation
To install the Agent Development Kit in Python, simply run:

```bash
pip install google-adk
```

(Note: ADK is also available for TypeScript, Go, and Java.)

## Local Project Conventions
This playground enforces several project-specific conventions to maximize AI-agent efficiency:

- **Markdown-JSON Hybrid Schema**: All core Markdown files must follow a strict header-metadata format (described in `MD_CONVENTIONS.md`) ensuring loss-less conversion to JSON.
- **Agent Logs**: Every agent that performs a significant intervention must update `content/logs/AGENTS_LOG.md` (as per `AGENTS.md` guidelines).
- **Core Principles**: See `AGENTS.md` for human-assistant workflows, constraints, and instructions on context fine-tuning.

## Session Worklog (`worklog.jsonl`)
Non-trivial agent sessions are recorded in `worklog.jsonl` at the repository root — a plain JSONL file with one JSON object per line, oldest first. It replaces the former `WORKLOG.md`: the worklog now lives outside the Markdown-JSON schema and the knowledge-base discovery surface (kb_mcp, search indexers, the MDDIA audit), so it is never injected as agent context and never linted as a Markdown document.

Each line is one entry conforming to `schema_version: 1`:

| Field | Type | Notes |
| :--- | :--- | :--- |
| `schema_version` | int | Schema version of the entry. Currently `1`. |
| `entry_id` | string | Unique across the file. `YYYY-MM-DD-s{N}` when `session_id` is set; plain `YYYY-MM-DD` otherwise. |
| `date` | string | ISO `YYYY-MM-DD` the session took place. |
| `session_id` | int \| null | Sequential session counter — the previous entry's `session_id` + 1. `null` if sessions are not tracked. |
| `summary` | string | One-line description of what the session accomplished. |
| `body_markdown` | string | Full narrative (Task / Outcome / Key decisions / KB changes / Follow-up) as a single Markdown blob; newlines JSON-escaped as `\n`. |

The full append protocol — deriving the next `session_id`, constructing the entry, and reading entries back — lives in `TODO_WORKFLOW.md` § Worklog (`worklog.jsonl`) — Schema & Append Protocol.

## Project Structure
This repository is organized to separate conversational contexts and agent code:

- `docs/`: Contains all specialized Markdown guidelines and skills (e.g., `AGENTS.md`, `MD_CONVENTIONS.md`, `MCP_GUIDELINE.md`). These files act as knowledge dependencies for the LLMs.
- `tutorial_agent/`: A functional "getting started" agent project created using the `adk create` CLI.
  - `tutorial_agent/imports.py`: A centralized file that exports key ADK components (`LlmAgent`, `SequentialAgent`, `McpToolset`, etc.). When building tools or exploring the framework, import ADK classes from here to maintain a clean architecture.
  - `tutorial_agent/agent.py`: The entry point containing the `root_agent` and any attached sample tools (like `get_current_time`).
  - `tutorial_agent/.env`: A local, git-ignored file containing your `GOOGLE_API_KEY`.
- `mcp_tools/`: An agent project demonstrating **MCP (Model Context Protocol)** tool integration. The agent connects to an external MCP server (the `@modelcontextprotocol/server-filesystem` npm package) via `McpToolset`, gaining file-system capabilities without any hand-written Python tool functions.
  - `mcp_tools/imports.py`: Centralized imports extended with `McpToolset`, `StdioConnectionParams`, `SseConnectionParams`, and `StdioServerParameters`.
  - `mcp_tools/agent.py`: Defines `filesystem_assistant_agent` — an `LlmAgent` whose tools array contains a single `McpToolset` that spawns and manages the MCP server subprocess.
  - `mcp_tools/workspace/`: The sandboxed directory the MCP filesystem server is allowed to access. Agents cannot read or write outside this path.
  - `mcp_tools/.env`: A local, git-ignored file containing your `GOOGLE_API_KEY`.
- `workflow_agents/`: An agent project demonstrating all **three ADK workflow agent types** working together. It implements a research-draft-refine pipeline: a `ParallelAgent` fans out to three concurrent researchers, a `SequentialAgent` chains the phases in order, and a `LoopAgent` iteratively polishes the final report.
  - `workflow_agents/imports.py`: Centralized imports for `LlmAgent`, `SequentialAgent`, `ParallelAgent`, `LoopAgent`, and `ToolContext`.
  - `workflow_agents/agent.py`: Defines the full pipeline — `research_phase_agent` (ParallelAgent) → `drafting_agent` (LlmAgent) → `refinement_loop_agent` (LoopAgent) — all orchestrated by `root_agent` (SequentialAgent).
  - `workflow_agents/tools/loop_control.py`: The `exit_loop` tool that lets the reviewer LlmAgent signal the LoopAgent to stop iterating.
  - `workflow_agents/WORKFLOW_SKILL.md`: Architecture guide and implementation reference for all three workflow agent types.
  - `workflow_agents/.env`: A local, git-ignored file containing your `GOOGLE_API_KEY`.
- `ecosystem/`: A **visual multi-agent architecture designer** — an n8n-style drag-and-drop canvas for designing ADK pipelines and exporting working Python code. Built with React 18 + Vite + React Flow.
  - Run: `cd ecosystem && npm install && npm run dev` → opens at `http://localhost:5173`.
  - Drag nodes (LlmAgent, SequentialAgent, ParallelAgent, LoopAgent, Tool, McpToolset) onto the canvas, connect them with edges, edit properties in the right panel, and click **Export Python** to download a working `agent.py`.
  - `ecosystem/src/utils/codeGenerator.ts`: Topological-sort-based Python ADK code generator.
  - For the usage guide, node reference, and extension roadmap, see `content/how-to/ADK_DESIGNER_SKILL.md` in the knowledge_base.
- `chatbot_template/`: A **production-ready ADK chatbot template** with a decoupled frontend/backend architecture. The backend is a Python FastAPI service wrapping an ADK agent; the frontend is a Next.js (TypeScript) app. Agents can return plain text or structured A2UI JSON payloads that the frontend renders as rich interactive widgets.
  - Run both services together: `./chatbot_template/dev.sh` → backend at `http://localhost:8080`, frontend at `http://localhost:3000`.
  - **Production deployment.** The frontend runs on **Firebase App Hosting** (Next.js SSR on a managed Cloud Run service, fronted by Cloud CDN); the backend runs as a separate IAM-only **Cloud Run** service. The browser never calls the backend directly — Next.js server-side proxy routes mint an OIDC ID token via the GCP metadata server and call the backend on the user's behalf. `GOOGLE_API_KEY` is mounted from Secret Manager into the backend.
  - **Deploy flow.** All production deploys are sourced from the `chatbot-template` branch (NOT `main`):
    - *Frontend:* push to `chatbot-template` → Firebase App Hosting auto-deploys.
    - *Backend:* `git checkout chatbot-template && ./chatbot_template/deploy-backend.sh` (the script refuses any other branch); it builds via Cloud Build and rolls out a new Cloud Run revision.
    - Wiring lives in `chatbot_template/firebase.json` (App Hosting backend declaration) and `chatbot_template/frontend/apphosting.yaml` (runtime config + `BACKEND_URL`). Detailed runbook in `chatbot_template/README.md`.
  - `chatbot_template/backend/`: FastAPI server with `InMemorySessionService`, `/chat` (single-turn), `/stream` (SSE), and `/health` endpoints. Copy, rename, and drop in your `agent.py` to get started.
  - `chatbot_template/frontend/`: Next.js app with `useChat` hook, `A2UIRenderer` component registry, and `ChatWindow` UI.
  - For the step-by-step development guide (scaffolding, agent wiring, A2UI integration, Cloud Run / Vertex AI / Firebase / Vercel deployment), see `content/how-to/ADK_CHATBOT_SKILL.md` in the knowledge_base.
  - For the full Agent-to-UI protocol reference (component schemas, renderer pattern, extension guide), see `content/reference/A2UI_REF.md` in the knowledge_base.
