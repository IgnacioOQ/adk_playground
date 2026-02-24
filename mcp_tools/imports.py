"""
Centralized imports for the mcp_tools agent.
Extends the base ADK imports with MCP (Model Context Protocol) tooling.

MCP Connection Types:
  - StdioConnectionParams  : Launch a local MCP server as a subprocess (stdin/stdout).
                             Use for local dev, containers, and bundled servers.
  - SseConnectionParams    : Connect to a remote MCP server via Server-Sent Events.
                             Use for cloud or network-hosted MCP servers.

The StdioServerParameters object carries the shell command and args that ADK
will use to spawn the MCP server process (e.g. via `npx`).
"""

# --- Core Agent Types ---
# https://google.github.io/adk-docs/agents/
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent

# --- MCP Tooling ---
# McpToolset  : Wraps an MCP server connection. Handles tool discovery,
#               schema adaptation, and call proxying on behalf of the LlmAgent.
# https://google.github.io/adk-docs/tools-custom/mcp-tools/
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    SseConnectionParams,
)

# StdioServerParameters: The command + args used to launch a stdio MCP server.
# Imported from the `mcp` package (installed as a dependency of google-adk).
from mcp import StdioServerParameters
