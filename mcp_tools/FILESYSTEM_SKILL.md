# Filesystem MCP Skill — Architecture & Implementation Guide
- status: active
- type: agent_skill
- id: mcp_tools.filesystem_skill
- last_checked: 2026-02-24
- label: [guide, reference, backend]
<!-- content -->
This document describes the architecture, implementation, and usage of the `filesystem_assistant_agent` — an ADK agent that uses the **Model Context Protocol (MCP)** to manage files inside a sandboxed workspace, without writing a single hand-coded Python tool.

It serves as the canonical worked example for MCP tool integration in this repository.

## Architecture Overview
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.architecture
- last_checked: 2026-02-24
<!-- content -->
The agent follows the **ADK MCP client-server pattern**:

```
┌─────────────────────────────────────────────────────┐
│                   adk web / adk run                 │
│                                                     │
│   ┌─────────────────────────────────────────────┐   │
│   │         filesystem_assistant_agent          │   │
│   │              (LlmAgent)                     │   │
│   │                                             │   │
│   │   tools=[McpToolset]                        │   │
│   │              │                              │   │
│   │    ┌─────────▼──────────────────────┐       │   │
│   │    │         McpToolset             │       │   │
│   │    │  • Spawns MCP server process   │       │   │
│   │    │  • Discovers tools via MCP     │       │   │
│   │    │  • Adapts schemas for ADK      │       │   │
│   │    │  • Proxies LLM tool calls      │       │   │
│   │    └─────────┬──────────────────────┘       │   │
│   └──────────────│──────────────────────────────┘   │
│                  │ stdin / stdout (stdio transport)  │
│   ┌──────────────▼──────────────────────────────┐   │
│   │  npx @modelcontextprotocol/server-filesystem│   │
│   │        (MCP Server subprocess)              │   │
│   │                                             │   │
│   │  Sandboxed root: mcp_tools/workspace/       │   │
│   └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Key design decisions:**
- The MCP server runs as a child process managed entirely by `McpToolset` — you never interact with it directly.
- `tool_filter` restricts the agent to exactly four operations, preventing the LLM from invoking destructive or out-of-scope MCP capabilities.
- The workspace path is resolved to an absolute path at import time, so the agent is location-independent.

## File Structure
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.file_structure
- last_checked: 2026-02-24
<!-- content -->
```
mcp_tools/
├── __init__.py                 # Python package marker
├── .env                        # Git-ignored — contains GOOGLE_API_KEY
├── imports.py                  # Centralized ADK + MCP imports
├── agent.py                    # Root agent definition
├── FILESYSTEM_SKILL.md         # This file
└── workspace/                  # Sandboxed directory the agent can access
    └── hello.txt               # Sample file for initial exploration
```

### Role of Each File

| File | Role |
| :--- | :--- |
| `imports.py` | Single source of truth for all ADK and MCP class imports |
| `agent.py` | Defines `filesystem_assistant_agent` and wires up `McpToolset` |
| `workspace/` | The only directory the MCP server is allowed to read/write |
| `.env` | Provides `GOOGLE_API_KEY` — never commit this file |

## Implementation
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.implementation
- last_checked: 2026-02-24
<!-- content -->

### Step 1 — Centralized Imports (`imports.py`)
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.implementation.imports
- last_checked: 2026-02-24
<!-- content -->
All ADK and MCP classes are imported once and re-exported from `imports.py`. Agent files consume only from this module.

```python
# Core agent type
from google.adk.agents.llm_agent import LlmAgent

# McpToolset: the bridge between ADK and any MCP server
from google.adk.tools.mcp_tool import McpToolset

# Connection strategies
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,   # spawn a local subprocess
    SseConnectionParams,     # connect to a remote server over SSE
)

# Subprocess launch specification
from mcp import StdioServerParameters
```

This pattern means: if a module path ever changes in a future ADK release, you fix it in **one place**.

### Step 2 — Workspace Path Resolution (`agent.py`)
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.implementation.workspace_path
- last_checked: 2026-02-24
<!-- content -->
The MCP filesystem server **requires an absolute path**. We derive it at module load time relative to `agent.py`, so the agent is portable across machines and working directories:

```python
import os

WORKSPACE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "workspace")
)
```

### Step 3 — Agent & McpToolset Definition (`agent.py`)
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.implementation.agent_definition
- last_checked: 2026-02-24
<!-- content -->
```python
from .imports import LlmAgent, McpToolset, StdioConnectionParams, StdioServerParameters

root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='filesystem_assistant_agent',       # naming convention: <role>_agent
    description="Browses and manipulates files inside a sandboxed workspace.",
    instruction="...",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx',
                    args=[
                        "-y",                                       # auto-install if absent
                        "@modelcontextprotocol/server-filesystem",  # npm MCP server package
                        WORKSPACE_PATH,                             # absolute sandboxed root
                    ],
                ),
            ),
            tool_filter=[          # explicit allowlist — only expose what the agent needs
                'list_directory',
                'read_file',
                'write_file',
                'create_directory',
            ],
        )
    ],
)
```

**Why `tool_filter` matters**: the `@modelcontextprotocol/server-filesystem` package exposes more tools than these four (e.g. `move_file`, `delete_file`). Restricting the list keeps the LLM context small and prevents unintended destructive operations.

## Available Tools
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.available_tools
- last_checked: 2026-02-24
<!-- content -->
The agent has access to exactly four MCP-provided tools:

| Tool (MCP name) | What it does |
| :--- | :--- |
| `list_directory` | Lists files and subdirectories at a given path |
| `read_file` | Returns the text content of a file |
| `write_file` | Creates or overwrites a file with the given content |
| `create_directory` | Creates a new directory (including nested paths) |

All paths are interpreted **relative to `workspace/`** by the MCP server — the agent cannot escape the sandbox.

## Example Interactions
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.examples
- last_checked: 2026-02-24
<!-- content -->

### Example 1 — List the workspace
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.examples.list
- last_checked: 2026-02-24
<!-- content -->
**User:** What files are in the workspace?

**Agent behaviour:**
1. Calls `list_directory` with the workspace root path.
2. Receives a list of entries from the MCP server.
3. Returns a formatted list to the user.

**Expected response:**
```
The workspace contains:
- hello.txt
```

### Example 2 — Read a file
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.examples.read
- last_checked: 2026-02-24
<!-- content -->
**User:** Read hello.txt for me.

**Agent behaviour:**
1. Calls `read_file` with path `hello.txt`.
2. MCP server returns the file contents.
3. Agent displays the text.

### Example 3 — Create a new file
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.examples.write
- last_checked: 2026-02-24
<!-- content -->
**User:** Create a file called notes.txt with the content "Meeting at 3pm".

**Agent behaviour:**
1. Calls `write_file` with path `notes.txt` and the given content.
2. MCP server writes the file to `workspace/notes.txt`.
3. Agent confirms creation.

### Example 4 — Organise files into folders
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.examples.organise
- last_checked: 2026-02-24
<!-- content -->
**User:** Create a folder called "archive" and move hello.txt into it by writing a copy there.

**Agent behaviour:**
1. Calls `create_directory` with path `archive`.
2. Calls `read_file` on `hello.txt` to get its contents.
3. Calls `write_file` with path `archive/hello.txt` and the retrieved contents.
4. Reports the result.

> Note: `move_file` is excluded from `tool_filter`, so the agent recreates the file manually — a deliberate safety trade-off.

## Running the Agent
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.running
- last_checked: 2026-02-24
<!-- content -->

### Prerequisites
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.running.prerequisites
- last_checked: 2026-02-24
<!-- content -->
1. Python virtual environment activated with `google-adk` installed.
2. `GOOGLE_API_KEY` set in `mcp_tools/.env`.
3. Node.js ≥ 18 and `npx` available on `$PATH` (verify: `node --version`).

### Web UI (recommended)
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.running.web
- last_checked: 2026-02-24
<!-- content -->
```bash
# From the repository root
source .venv/bin/activate
adk web --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000), select **mcp_tools** from the agent dropdown.

The MCP server subprocess is spawned automatically on the first tool call. There is no separate server start step.

### CLI (quick test)
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.running.cli
- last_checked: 2026-02-24
<!-- content -->
```bash
adk run mcp_tools
```

### Hot-reload caveat
- status: active
- type: documentation
- id: mcp_tools.filesystem_skill.running.hot_reload
- last_checked: 2026-02-24
<!-- content -->
If you edit `agent.py` or `imports.py`, restart `adk web` to pick up the changes. The MCP server subprocess is re-spawned automatically on the next session.
