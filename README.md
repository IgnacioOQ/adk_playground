# ADK Playground
- status: active
- type: plan
- label: [core, template]
<!-- content -->

## What is Google ADK?
- status: active
- type: documentation
<!-- content -->
The Agent Development Kit (ADK) is a flexible and modular framework developed by Google for building and deploying AI agents. While optimized for Gemini and the Google ecosystem, ADK is model-agnostic, deployment-agnostic, and designed to make agentic architectures feel more like traditional software development.

https://google.github.io/adk-docs/agents/

This repository serves as a playground and central nervous system for learning and experimenting with ADK concepts.

## Core Agent Categories
- status: active
- type: documentation
<!-- content -->
ADK provides distinct agent categories to build sophisticated applications:

1. **LLM Agents** (`LlmAgent`): These agents utilize Large Language Models (LLMs) as their core engine to understand natural language, reason, plan, generate responses, and dynamically decide how to proceed or which tools to use. They are ideal for flexible, language-centric tasks.
2. **Workflow Agents** (`SequentialAgent`, `ParallelAgent`, `LoopAgent`): These specialized agents control the execution flow of other agents in predefined, deterministic patterns (sequence, parallel, or loop) without using an LLM for the flow control itself. They are perfect for structured processes needing predictable execution.
3. **Custom Agents** (`BaseAgent`): Created by extending the `BaseAgent` directly, these allow you to implement unique operational logic, specific control flows, or specialized integrations not covered by the standard types.

## Multi-Agent Architecture
- status: active
- type: documentation
<!-- content -->
While each agent type serves a distinct purpose, complex applications frequently employ multi-agent architectures where:
- LLM Agents handle intelligent, language-based task execution.
- Workflow Agents manage the overall process flow using standard patterns.
- Custom Agents provide specialized capabilities or rules needed for unique integrations.

## Extending Capabilities
- status: active
- type: documentation
<!-- content -->
Beyond the core agent types, ADK allows significantly expanding what agents can do through:

- **AI Models**: Swap the underlying intelligence by integrating with generative AI models from Google and other providers.
- **Artifacts**: Enable agents to create and manage persistent outputs like files, code, or documents.
- **Pre-built Tools & Integrations**: Equip agents with tools to interact with the world (e.g., search, code execution).
- **Custom Tools**: Create your own task-specific tools.
- **Plugins**: Integrate complex, pre-packaged behaviors and third-party services.
- **Skills**: Use prebuilt or custom Agent Skills efficiently inside AI context limits.
- **Callbacks**: Hook into specific events during execution to add logging, monitoring, or custom side-effects.

## MCP (Model Context Protocol) Integration
- status: active
- type: documentation
<!-- content -->
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
- status: active
- type: documentation
<!-- content -->
To install the Agent Development Kit in Python, simply run:

```bash
pip install google-adk
```

*(Note: ADK is also available for TypeScript, Go, and Java.)*

## Local Project Conventions
- status: active
- type: documentation
<!-- content -->
This playground enforces several project-specific conventions to maximize AI-agent efficiency:

- **Markdown-JSON Hybrid Schema**: All core Markdown files must follow a strict header-metadata format (described in `MD_CONVENTIONS.md`) ensuring loss-less conversion to JSON.
- **Agent Logs**: Every agent that performs a significant intervention must update `content/logs/AGENTS_LOG.md` (as per `AGENTS.md` guidelines).
- **Core Principles**: See `AGENTS.md` for human-assistant workflows, constraints, and instructions on context fine-tuning.

## Project Structure
- status: active
- type: documentation
<!-- content -->
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
- `ecosystem/`: An agent project that **combines workflow agents with MCP tools** in a single pipeline. It extends `workflow_agents/` by giving each parallel researcher live internet access via the `mcp-server-fetch` MCP server. The result is a web-sourced research report with real cited URLs.
  - `ecosystem/imports.py`: Centralized imports covering both workflow agent classes (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) and MCP classes (`McpToolset`, `StdioConnectionParams`, `StdioServerParameters`).
  - `ecosystem/agent.py`: Defines `web_research_pipeline_agent` — a `SequentialAgent` where the `ParallelAgent` research phase has `McpToolset[fetch]`-equipped researchers, followed by drafting and a `LoopAgent` refinement loop.
  - `ecosystem/tools/loop_control.py`: The `exit_loop` tool (same pattern as `workflow_agents/`).
  - `ecosystem/ADK_ECOSYSTEM_SKILL.md`: Architecture guide, combination patterns, state flow, and extension roadmap for building more complex ecosystems.
