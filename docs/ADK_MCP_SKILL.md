# ADK MCP Skill — Model Context Protocol Integration Guide
- status: active
- type: agent_skill
- id: skill.adk_mcp
- last_checked: 2026-02-24
- label: [agent, guide, infrastructure, backend]
<!-- content -->
This document is the primary reference for integrating **Model Context Protocol (MCP)** servers into ADK agents. It covers architecture, all core classes and their import paths, both integration patterns (ADK as client and ADK as server), deployment strategies, and a comprehensive tool library with 30+ real tool examples across the most important MCP servers.

Reference: https://google.github.io/adk-docs/tools-custom/mcp-tools/

## 1. What is MCP?
- status: active
- type: guideline
- id: skill.adk_mcp.overview
- last_checked: 2026-02-24
<!-- content -->
The **Model Context Protocol (MCP)** is an open standard that defines a uniform interface for LLMs to communicate with external applications, data sources, and tools. Instead of writing a custom Python function for every capability, you connect your ADK agent to an MCP server that already implements those capabilities — and the agent gains them instantly.

**Two integration directions:**

| Direction | Description |
| :--- | :--- |
| **ADK as MCP Client** | Your ADK agent consumes tools exposed by an external MCP server (most common). |
| **ADK as MCP Server** | You wrap ADK tools inside an MCP server so non-ADK clients can call them. |

This document focuses primarily on **ADK as MCP Client**, which is the pattern used in `mcp_tools/`.

## 2. Core Classes & Import Conventions
- status: active
- type: guideline
- id: skill.adk_mcp.imports
- last_checked: 2026-02-24
<!-- content -->
All MCP-related classes must be imported in the agent's `imports.py`. Never scatter these imports across tool files.

```python
# In imports.py — the single source of truth for all ADK + MCP classes

# McpToolset: the bridge between an LlmAgent and any MCP server.
# Handles connection lifecycle, tool discovery, schema adaptation, and call proxying.
from google.adk.tools.mcp_tool import McpToolset

# Connection strategies — pick one depending on where the server runs.
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,   # Launch a local MCP server as a subprocess (stdin/stdout)
    SseConnectionParams,     # Connect to a remote MCP server via HTTP / Server-Sent Events
)

# The subprocess specification used with StdioConnectionParams.
# Comes from the `mcp` package (auto-installed as a dependency of google-adk).
from mcp import StdioServerParameters

# (ADK-as-Server pattern only) Converts ADK tool schemas to MCP-compatible definitions.
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
```

Then in `agent.py`:
```python
from .imports import LlmAgent, McpToolset, StdioConnectionParams, StdioServerParameters
```

## 3. Connection Types
- status: active
- type: guideline
- id: skill.adk_mcp.connection_types
- last_checked: 2026-02-24
<!-- content -->

### StdioConnectionParams — Local Subprocess
- status: active
- type: guideline
- id: skill.adk_mcp.connection_types.stdio
- last_checked: 2026-02-24
<!-- content -->
Use this when the MCP server is a local process launched by ADK (most common for development and containerised deployments). The server communicates with ADK via stdin/stdout.

```python
McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',          # the shell command to run
            args=[
                "-y",               # auto-install package if not cached
                "@modelcontextprotocol/server-filesystem",
                "/absolute/path/to/sandboxed/directory",
            ],
            env=None,               # optional: dict of extra environment variables
        ),
        timeout=10,                 # optional: seconds to wait for server startup
    ),
    tool_filter=['list_directory', 'read_file'],
)
```

**Prerequisites**: the command (`npx`, `uvx`, a binary, etc.) must be on `$PATH`.

### SseConnectionParams — Remote HTTP Server
- status: active
- type: guideline
- id: skill.adk_mcp.connection_types.sse
- last_checked: 2026-02-24
<!-- content -->
Use this when the MCP server runs as a separate, long-lived service (e.g., a Cloud Run deployment) and communicates over HTTP with Server-Sent Events.

```python
McpToolset(
    connection_params=SseConnectionParams(
        url="https://your-mcp-server.example.com/sse",
        headers={"Authorization": "Bearer YOUR_TOKEN"},  # optional auth
    ),
    tool_filter=['search', 'fetch'],
)
```

**When to use SSE vs Stdio:**

| Criterion | StdioConnectionParams | SseConnectionParams |
| :--- | :--- | :--- |
| Server location | Same machine or container | Remote network service |
| Latency | Low (IPC) | Higher (network round-trip) |
| Scalability | 1 process per agent instance | Shared across many agents |
| Auth | OS-level process isolation | HTTP headers / OAuth |
| Typical use | Dev, Docker, single-tenant | Cloud, multi-tenant |

## 4. McpToolset Configuration
- status: active
- type: guideline
- id: skill.adk_mcp.toolset_config
- last_checked: 2026-02-24
<!-- content -->
`McpToolset` accepts the following parameters:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `connection_params` | `StdioConnectionParams` or `SseConnectionParams` | Yes | How to reach the MCP server |
| `tool_filter` | `list[str]` | No | Allowlist of MCP tool names to expose. If omitted, **all** server tools are exposed. |

**Always provide `tool_filter`** — MCP servers can expose dozens of tools. Exposing all of them wastes LLM context tokens and increases the risk of the agent invoking destructive operations.

```python
# Minimal, safe McpToolset definition
McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(command='npx', args=["-y", "some-mcp-server"])
    ),
    tool_filter=['safe_tool_a', 'safe_tool_b'],
)
```

## 5. Integration Patterns
- status: active
- type: guideline
- id: skill.adk_mcp.patterns
- last_checked: 2026-02-24
<!-- content -->

### Pattern A — ADK as MCP Client (Standard)
- status: active
- type: guideline
- id: skill.adk_mcp.patterns.client
- last_checked: 2026-02-24
<!-- content -->
The agent's `tools` list contains one or more `McpToolset` instances. This is the pattern used in `mcp_tools/agent.py`.

```python
root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='my_assistant_agent',
    instruction="...",
    tools=[
        McpToolset(connection_params=StdioConnectionParams(...), tool_filter=[...]),
        McpToolset(connection_params=SseConnectionParams(...), tool_filter=[...]),
        my_python_tool_function,   # plain ADK tools can coexist with McpToolsets
    ],
)
```

Multiple `McpToolset` instances are fully supported — each connects to a different MCP server.

### Pattern B — ADK as MCP Server
- status: active
- type: guideline
- id: skill.adk_mcp.patterns.server
- last_checked: 2026-02-24
<!-- content -->
Wrap your ADK tools inside a standard MCP server so non-ADK clients can call them. Requires the `mcp` package directly.

```python
import mcp.server.lowlevel
import mcp.server.stdio
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

app = mcp.server.lowlevel.Server("my-adk-mcp-server")

@app.list_tools()
async def list_tools():
    # Expose your ADK tool's schema in MCP format
    return [adk_to_mcp_tool_type(my_adk_tool)]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    # Execute the ADK tool and return the result
    result = await my_adk_tool.run_async(args=arguments, tool_context=None)
    return [mcp.types.TextContent(type="text", text=str(result))]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
```

### Pattern C — Non-`adk web` Async Usage
- status: active
- type: guideline
- id: skill.adk_mcp.patterns.async
- last_checked: 2026-02-24
<!-- content -->
When running ADK outside `adk web` (e.g., in a custom async script or test), you must manage the `McpToolset` lifecycle manually to ensure connections are properly closed.

```python
async def run():
    toolset = McpToolset(connection_params=StdioConnectionParams(...))
    agent = LlmAgent(model='gemini-2.5-flash', name='agent', tools=[toolset])
    runner = Runner(agent=agent, app_name='app', session_service=InMemorySessionService())
    # ... run the agent ...
    await toolset.close()   # always clean up
```

## 6. MCP Tool Library — 30+ Tool Reference
- status: active
- type: guideline
- id: skill.adk_mcp.tool_library
- last_checked: 2026-02-24
<!-- content -->
The following tables catalogue the most important tools across the most widely used MCP servers. Tool names are the exact strings to use in `tool_filter`.

### Filesystem Server (`@modelcontextprotocol/server-filesystem`)
- status: active
- type: guideline
- id: skill.adk_mcp.tool_library.filesystem
- last_checked: 2026-02-24
<!-- content -->
Install: `npx -y @modelcontextprotocol/server-filesystem <absolute_path>`

Provides secure file-system access, sandboxed to the directories you pass as arguments.

| # | Tool name | Description |
| :- | :--- | :--- |
| 1 | `read_text_file` | Reads a file's full text content. Supports optional `head` / `tail` to limit output lines. |
| 2 | `read_media_file` | Reads an image or audio file and returns it as base64-encoded data with its MIME type. |
| 3 | `read_multiple_files` | Reads several files in a single call. Failures on individual files do not abort the batch. |
| 4 | `write_file` | Creates or fully overwrites a file with the provided content. |
| 5 | `edit_file` | Applies targeted find-and-replace edits to a file. Supports a `dryRun` flag to preview changes. |
| 6 | `list_directory` | Lists the immediate contents of a directory, prefixing entries with `[FILE]` or `[DIR]`. |
| 7 | `list_directory_with_sizes` | Like `list_directory` but includes file sizes. Supports sorting by name or size. |
| 8 | `create_directory` | Creates a directory (and any missing parent directories). |
| 9 | `move_file` | Moves or renames a file or directory. |
| 10 | `search_files` | Recursively searches for files matching a glob or text pattern inside the sandboxed root. |
| 11 | `directory_tree` | Returns the entire directory hierarchy as a nested JSON structure. |
| 12 | `get_file_info` | Returns metadata for a path: size, created/modified timestamps, type, and permissions. |
| 13 | `list_allowed_directories` | Lists all top-level directories the server is permitted to access (as configured at startup). |

### Git Server (`@modelcontextprotocol/server-git` via `uvx mcp-server-git`)
- status: active
- type: guideline
- id: skill.adk_mcp.tool_library.git
- last_checked: 2026-02-24
<!-- content -->
Install: `uvx mcp-server-git --repository <path>`

Provides read and write access to a local Git repository. All tools accept `repo_path` as their first argument.

| # | Tool name | Description |
| :- | :--- | :--- |
| 14 | `git_status` | Shows the working tree status (staged, unstaged, and untracked changes). |
| 15 | `git_diff_unstaged` | Shows all changes in the working directory that have not yet been staged. |
| 16 | `git_diff_staged` | Shows changes that are staged and ready to be committed. |
| 17 | `git_diff` | Shows the diff between two branches, tags, or commit SHAs. |
| 18 | `git_log` | Returns the commit history with optional filters for date range and max entry count. |
| 19 | `git_show` | Shows the full content and metadata of a specific commit by SHA. |
| 20 | `git_add` | Stages one or more files for the next commit. |
| 21 | `git_commit` | Creates a commit with the staged changes and a given message. |
| 22 | `git_reset` | Unstages all currently staged changes. |
| 23 | `git_create_branch` | Creates a new branch, optionally based on a specific existing branch. |
| 24 | `git_checkout` | Switches the working directory to a different branch. |
| 25 | `git_branch` | Lists local or remote branches, with optional filters by content. |

### Memory Server (`@modelcontextprotocol/server-memory`)
- status: active
- type: guideline
- id: skill.adk_mcp.tool_library.memory
- last_checked: 2026-02-24
<!-- content -->
Install: `npx -y @modelcontextprotocol/server-memory`

Provides a persistent, session-spanning knowledge graph. Entities (nodes) and relations (edges) are stored across turns, giving the agent long-term memory.

| # | Tool name | Description |
| :- | :--- | :--- |
| 26 | `create_entities` | Adds new named entities to the knowledge graph, each with a type and a list of observations. |
| 27 | `create_relations` | Creates directed relationships between existing entities (e.g., `user` → `owns` → `project`). |
| 28 | `add_observations` | Appends new facts/observations to an entity that already exists in the graph. |
| 29 | `search_nodes` | Searches the graph for entities matching a natural-language query. |
| 30 | `open_nodes` | Retrieves specific entities by name, returning their full observation lists. |
| 31 | `read_graph` | Dumps the entire knowledge graph — all entities and all relations. |
| 32 | `delete_entities` | Removes entities (and all their associated relations) from the graph. |
| 33 | `delete_observations` | Removes specific observations from an entity without deleting the entity itself. |
| 34 | `delete_relations` | Removes specific directed relationships from the graph. |

### Fetch Server (`@modelcontextprotocol/server-fetch`)
- status: active
- type: guideline
- id: skill.adk_mcp.tool_library.fetch
- last_checked: 2026-02-24
<!-- content -->
Install: `uvx mcp-server-fetch`

Retrieves web content and converts it to a format optimised for LLM consumption (Markdown).

| # | Tool name | Description |
| :- | :--- | :--- |
| 35 | `fetch` | Fetches a URL and returns its content as Markdown (HTML stripped). Supports `max_length` and `start_index` for pagination through large pages. |

### Google Maps Server (`@modelcontextprotocol/server-google-maps`)
- status: active
- type: guideline
- id: skill.adk_mcp.tool_library.google_maps
- last_checked: 2026-02-24
<!-- content -->
Install: `npx -y @modelcontextprotocol/server-google-maps`
Requires: `GOOGLE_MAPS_API_KEY` in environment.

| # | Tool name | Description |
| :- | :--- | :--- |
| 36 | `maps_geocode` | Converts a street address into geographic coordinates (latitude/longitude). |
| 37 | `maps_reverse_geocode` | Converts coordinates into a human-readable address. |
| 38 | `maps_search_places` | Searches for places (businesses, landmarks) matching a text query near a location. |
| 39 | `maps_get_place_details` | Returns detailed information about a specific place (hours, phone, rating, reviews). |
| 40 | `maps_get_directions` | Returns turn-by-turn directions between an origin and destination, supporting driving, walking, transit, and cycling modes. |
| 41 | `maps_distance_matrix` | Computes travel time and distance between multiple origins and destinations in a single call. |
| 42 | `maps_elevation` | Returns the elevation above sea level for one or more geographic coordinates. |

## 7. Multi-Server Agent Example
- status: active
- type: guideline
- id: skill.adk_mcp.multi_server_example
- last_checked: 2026-02-24
<!-- content -->
An agent can combine multiple `McpToolset` instances alongside plain Python tools:

```python
import os
from .imports import (
    LlmAgent, McpToolset, StdioConnectionParams, SseConnectionParams, StdioServerParameters
)

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))

root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='research_assistant_agent',
    description="Researches topics, reads files, and persists findings to memory.",
    instruction=(
        "You have three capability sets: "
        "1) filesystem — read and write files in the workspace; "
        "2) web fetch — retrieve and summarise any URL; "
        "3) memory — persist important facts across sessions as a knowledge graph. "
        "Use them together to complete research tasks."
    ),
    tools=[
        # Tool set 1: file system (local subprocess)
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx',
                    args=["-y", "@modelcontextprotocol/server-filesystem", WORKSPACE],
                ),
            ),
            tool_filter=['list_directory', 'read_text_file', 'write_file', 'create_directory'],
        ),
        # Tool set 2: web fetch (local subprocess via uvx)
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='uvx', args=['mcp-server-fetch'],
                ),
            ),
            tool_filter=['fetch'],
        ),
        # Tool set 3: persistent memory (local subprocess)
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx', args=["-y", "@modelcontextprotocol/server-memory"],
                ),
            ),
            tool_filter=['create_entities', 'add_observations', 'search_nodes', 'open_nodes'],
        ),
    ],
)
```

## 8. Deployment Patterns
- status: active
- type: guideline
- id: skill.adk_mcp.deployment
- last_checked: 2026-02-24
<!-- content -->

### Pattern 1 — Self-Contained Stdio (Development / Docker)
- status: active
- type: guideline
- id: skill.adk_mcp.deployment.stdio
- last_checked: 2026-02-24
<!-- content -->
The MCP server is bundled inside the same container as the ADK agent and spawned as a subprocess.

- Use `StdioConnectionParams`.
- Include the runtime (Node.js, Python `uvx`, etc.) in the container image.
- Best for single-tenant workloads and local development.

### Pattern 2 — Remote HTTP/SSE Server (Cloud Run / Vertex AI)
- status: active
- type: guideline
- id: skill.adk_mcp.deployment.sse
- last_checked: 2026-02-24
<!-- content -->
The MCP server runs as an independent, scalable Cloud Run service. Many agent instances share one server.

- Use `SseConnectionParams` with the service URL.
- Deploy in stateless mode for horizontal scaling.
- Secure with `Authorization` headers or mTLS.
- Deploy the ADK agent with: `adk deploy cloud_run --project=<id> --region=<region> --service_name=<name>`

### Pattern 3 — Kubernetes Sidecar
- status: active
- type: guideline
- id: skill.adk_mcp.deployment.sidecar
- last_checked: 2026-02-24
<!-- content -->
The MCP server runs as a **sidecar container** in the same Kubernetes pod as the ADK agent.

- Both containers share a network namespace; use `localhost` as the MCP server URL.
- Use `SseConnectionParams(url="http://localhost:<port>/sse")`.
- Provides isolation without the overhead of a separate network service.

## 9. Security Best Practices
- status: active
- type: guideline
- id: skill.adk_mcp.security
- last_checked: 2026-02-24
<!-- content -->
| Risk | Mitigation |
| :--- | :--- |
| LLM calls destructive tools | Always use `tool_filter` — only expose exactly what the agent needs. |
| Path traversal attacks | Pass only absolute, pre-validated paths to the filesystem server at startup. |
| Credential leakage | Pass API keys via environment variables or secret managers, never hard-code. |
| Injection via tool output | Sanitise MCP tool output before using it in further prompts or system messages. |
| Remote server spoofing | Validate TLS certificates; use `Authorization` headers or mTLS for SSE connections. |
| Over-permissive filesystem | Sandbox to the smallest necessary directory; prefer read-only `tool_filter` sets where writes are not needed. |

## 10. Troubleshooting
- status: active
- type: guideline
- id: skill.adk_mcp.troubleshooting
- last_checked: 2026-02-24
<!-- content -->

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| `McpToolset` raises on startup | `npx` / `uvx` not on `$PATH` | Install Node.js (`brew install node`) or `uv` (`pip install uv`) and verify with `which npx` |
| No tools discovered | Wrong package name or server crashed | Run the server command manually to check output: `npx -y @modelcontextprotocol/server-filesystem /tmp` |
| Tool call returns permission error | Path outside allowed directories | Ensure `WORKSPACE_PATH` is a subdirectory of the path passed to the server at startup |
| `adk web` shows no tools after edit | Hot-reload did not pick up changes | Kill and restart `adk web` — tool logic changes require a full restart |
| SSE connection refused | Remote server not running or wrong URL | Test with `curl <url>/sse`; check Cloud Run logs |
| Memory leak on long runs | `McpToolset` not closed in async usage | Call `await toolset.close()` in your cleanup path (Pattern C) |
