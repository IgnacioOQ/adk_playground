# Google ADK Implementation Skill
- status: active
- type: agent_skill
- id: skill.adk_implementation
- last_checked: 2026-02-24
- label: [agent, guide, infrastructure]
<!-- content -->
This document serves as the primary implementation guideline and playbook for building, scaffolding, and integrating Google's Agent Development Kit (ADK) into projects. 

[ADK](https://google.github.io/adk-docs/) is a Python-first framework (with support for TS, Go, Java) designed to build model-agnostic, easily orchestratable AI agents using standard software engineering patterns instead of obscure prompting frameworks.

## 0. ADK Skill Map
- status: active
- type: guideline
- id: skill.adk_implementation.skill_map
- last_checked: 2026-02-24
<!-- content -->
The ADK knowledge base is split across several specialized files. Use this map to navigate to the right document.

**Core skill documents** (in `docs/`):

| Skill file | Coverage | When to read it |
| :--- | :--- | :--- |
| **`ADK_SKILL.md`** *(this file)* | Project scaffolding, `imports.py` convention, execution & testing, MCP quick-start | Starting a new project or reviewing foundational conventions |
| **`ADK_TOOLS_SKILL.md`** | All tool types: built-in (`google_search`, code executor), native ADK toolsets (BigQuery, Vertex AI), MCP integrations (GitHub, Stripe, MongoDB, Notion…), observability plugins — 24 tools catalogued | Adding any tool capability to an agent |
| **`ADK_MCP_SKILL.md`** | MCP architecture deep-dive: `McpToolset`, stdio vs. SSE vs. StreamableHTTP, ADK-as-client vs. ADK-as-server, 30+ MCP tool reference | Connecting to an MCP server or understanding MCP internals |
| **`ADK_WORKFLOW_SKILL.md`** | Workflow agents: `SequentialAgent`, `ParallelAgent`, `LoopAgent`, state management, `exit_loop` pattern, 24 composition patterns, design principles | Building deterministic multi-step pipelines |

**Project-level skill files** (live alongside each subproject's code):

| Skill file | Project | What it demonstrates |
| :--- | :--- | :--- |
| `mcp_tools/FILESYSTEM_SKILL.md` | `mcp_tools/` | Filesystem MCP server, sandboxed workspace, `McpToolset` lifecycle |
| `workflow_agents/WORKFLOW_SKILL.md` | `workflow_agents/` | Research-draft-refine pipeline using all three workflow agent types |
| `ecosystem/ADK_ECOSYSTEM_SKILL.md` | `ecosystem/` | Combined workflow agents + `google_search` tool pipeline |

**Reading order for new users:** `ADK_SKILL.md` → `ADK_TOOLS_SKILL.md` → `ADK_MCP_SKILL.md` → `ADK_WORKFLOW_SKILL.md`

## 1. Creating an ADK Project From Scratch
- status: active
- type: guideline
- id: skill.adk_implementation.creating_project
- last_checked: 2026-02-24
- label: [infrastructure]
<!-- content -->
When starting a completely new, agent-first project, follow this standard initialization sequence:

1. **Virtual Environment**: Keep dependencies isolated.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install ADK**:
   ```bash
   pip install google-adk
   # Optional: Upgrade pip to avoid build errors with 'pyarrow'
   pip install --upgrade pip
   ```
3. **Scaffold Project**: Use the CLI to interactively generate the agent skeleton.
   ```bash
   adk create my_new_agent
   ```
   *Select `Google AI` (Gemini API) or `Vertex AI` backend. Opt for `gemini-2.5-flash` as a fast default.*

## 2. Integrating ADK into Existing Projects
- status: active
- type: guideline
- id: skill.adk_implementation.integrating_adk
- last_checked: 2026-02-24
- label: [infrastructure]
<!-- content -->
If a repository already has existing application code (e.g., a React frontend, an Express backend), you must integrate ADK without polluting the existing structure.

**Convention: The Isolated Agent Directory**
Do not build ADK agents in the root of an existing app. Create a dedicated folder (e.g., `ai_agents/` or `services/agent_service/`).

1. `cd ai_agents`
2. Run standard initialization (`venv`, `pip install`, `adk create`).
3. Set up a local `requirements.txt` specifically for the agent isolated from the main app's `package.json` or other setups.

## 3. Implementation Conventions & Tricks
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks
- last_checked: 2026-02-24
- label: [core]
<!-- content -->
To ensure ADK applications scale cleanly, adhere to these battle-tested conventions:

### The `imports.py` Centralization Pattern
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks.imports_py
- last_checked: 2026-02-24
<!-- content -->
**Problem**: The `google.adk` package is massive. Importing specific classes ([`LlmAgent`](https://google.github.io/adk-docs/agents/), [`SequentialAgent`](https://google.github.io/adk-docs/agents/workflows/), `BaseAgent`) across dozens of files creates brittle references.

**Solution**: Create an `imports.py` file alongside your main `agent.py`.
```python
# imports.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent
```
Then, inside `agent.py` and other files:
```python
from .imports import LlmAgent, SequentialAgent
```

### Tool Definition Separation
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks.tool_definition_separation
- last_checked: 2026-02-24
<!-- content -->
Do not define complex action functions ([Tools](https://google.github.io/adk-docs/tools/)) directly inside `agent.py`. 
1. Create a `tools/` directory.
2. Group related tools into files (e.g., `tools/time_tools.py`, `tools/db_tools.py`).
3. Import the specific functions into `agent.py` and append them to the `tools=[...]` array during Agent initialization.

### Environment & Secrets Management
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks.environment_and_secrets
- last_checked: 2026-02-24
<!-- content -->
ADK applications inherently rely on standard `.env` variables (like `GOOGLE_API_KEY`).
1. **Never commit `.env`**: Always ensure `.env` and `*.env` are in `.gitignore`.
2. **Execution Context**: The `adk web` and `adk run` commands (see [CLI documentation](https://google.github.io/adk-docs/cli/)) automatically look for the `.env` file in the folder where the agent lives (e.g., `my_new_agent/.env`).

## 4. Execution & Testing
- status: active
- type: guideline
- id: skill.adk_implementation.execution_and_testing
- last_checked: 2026-02-24
- label: [infrastructure]
<!-- content -->
[ADK comes with two built-in runners](https://google.github.io/adk-docs/cli/) that hot-reload differently:
- **CLI Runner** (`adk run <agent_folder>`): Interactive terminal.
- **Web Runner** (`adk web --port 8000` from project root): Provides a chat GUI at `localhost:8000`. 

**Critical Trick for Web Runner**: If you change the underlying Python tool implementations (e.g., changing how a function fetches data), the `adk web` background process *may not instantly hot-reload* the tool logic. You must terminate and restart the web server to guarantee new Python tool logic is picked up.

## 5. MCP (Model Context Protocol) Tool Integration
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools
- last_checked: 2026-02-24
- label: [infrastructure, core]
<!-- content -->
ADK agents can delegate tool execution to external **MCP servers** — processes that expose capabilities (file I/O, database queries, web search, etc.) over a standard protocol. The `McpToolset` class acts as the bridge.

Reference: https://google.github.io/adk-docs/tools-custom/mcp-tools/

### Architecture: Client-Server Pattern
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools.architecture
- last_checked: 2026-02-24
<!-- content -->
```
LlmAgent
  └── tools=[McpToolset]
              │  (manages lifecycle)
              ▼
        MCP Server process
        (e.g. npx @modelcontextprotocol/server-filesystem)
```
`McpToolset` handles five responsibilities automatically:
1. **Spawn / Connect** — starts a stdio subprocess or opens an SSE connection.
2. **Discover** — calls `list_tools` and fetches schemas from the server.
3. **Adapt** — converts MCP tool schemas into ADK-compatible tool definitions.
4. **Expose** — makes the adapted tools available to the `LlmAgent`.
5. **Proxy** — routes the LLM's tool-call requests to the server and returns results.

### Import Conventions
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools.imports
- last_checked: 2026-02-24
<!-- content -->
Add the following block to the agent's `imports.py` (do **not** scatter these across files):

```python
# MCP Tooling
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,  # Local subprocess (stdin/stdout)
    SseConnectionParams,    # Remote server (Server-Sent Events)
)
from mcp import StdioServerParameters  # Shell command + args for stdio servers
```

Then in `agent.py`:
```python
from .imports import LlmAgent, McpToolset, StdioConnectionParams, StdioServerParameters
```

### Connection Parameter Types
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools.connection_types
- last_checked: 2026-02-24
<!-- content -->
| Class | When to use |
| :--- | :--- |
| `StdioConnectionParams` | Local dev, Docker containers, bundled MCP servers launched via `npx` or a binary |
| `SseConnectionParams` | Remote or cloud-hosted MCP servers reachable over HTTP/SSE |

**Stdio example** (local filesystem server via npm):
```python
McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=[
                "-y",                                       # auto-install package if missing
                "@modelcontextprotocol/server-filesystem",  # the MCP server npm package
                "/absolute/path/to/workspace",             # sandboxed root — MUST be absolute
            ],
        ),
    ),
    tool_filter=['list_directory', 'read_file', 'write_file', 'create_directory'],
)
```

### Naming Conventions
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools.naming
- last_checked: 2026-02-24
<!-- content -->
Follow these conventions to keep multi-agent and multi-tool architectures readable:

| Element | Convention | Example |
| :--- | :--- | :--- |
| Agent variable | `<role>_agent` | `filesystem_assistant_agent` |
| `McpToolset` | one instance per MCP server | — |
| `tool_filter` values | exact MCP tool names (snake_case) | `'read_file'`, `'list_directory'` |
| Workspace path constant | `WORKSPACE_PATH` (module-level) | `WORKSPACE_PATH = os.path.abspath(...)` |

### Tool Filter Best Practice
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools.tool_filter
- last_checked: 2026-02-24
<!-- content -->
Always provide an explicit `tool_filter` list. MCP servers can expose many tools; exposing all of them:
- Increases token usage (all schemas go into the LLM context).
- Widens the attack surface (the LLM could invoke destructive operations unintentionally).

Only list the tools the agent actually needs for its stated purpose.

### Deployment Note
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools.deployment
- last_checked: 2026-02-24
<!-- content -->
For cloud deployments (Cloud Run, GKE, Vertex AI Agent Engine), `McpToolset` and the agent **must be defined synchronously** in `agent.py`. Async factory patterns are not supported in those environments.

### Prerequisites
- status: active
- type: guideline
- id: skill.adk_implementation.mcp_tools.prerequisites
- last_checked: 2026-02-24
<!-- content -->
For npm-based MCP servers (like `@modelcontextprotocol/server-filesystem`):
- Node.js and `npx` must be installed and on `$PATH`.
- Verify with `node --version` and `npx --version` before running `adk web` or `adk run`.
