"""
Centralized imports for the ecosystem project.

This package demonstrates the combination of two ADK capability layers:
  1. Workflow Agents — deterministic, non-LLM orchestration of multi-step pipelines.
  2. MCP Tools       — live external capabilities (e.g. internet fetch) injected into
                       LlmAgent sub-agents inside those pipelines.

Workflow Agent Summary:
  - SequentialAgent : Runs sub_agents one after another. Shared InvocationContext lets
                      each step read the previous step's output_key values.
  - ParallelAgent   : Runs sub_agents concurrently. Each branch writes to its own
                      output_key — no automatic state sharing between branches.
  - LoopAgent       : Repeatedly runs sub_agents until escalate=True is set (via
                      ToolContext.actions) or max_iterations is reached.

MCP Tool Summary:
  - McpToolset            : ADK wrapper for an MCP server. Handles spawn, discovery,
                            schema adaptation, and call proxying.
  - StdioConnectionParams : Launch a local MCP server subprocess (stdio transport).
  - SseConnectionParams   : Connect to a remote MCP server over SSE.
  - StdioServerParameters : The shell command + args to spawn the server process.
"""

# --- Core Agent Types ---
from google.adk.agents.llm_agent import LlmAgent

# --- Workflow Agents ---
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent

# --- Tool Support ---
# ToolContext is injected into Python tool functions that interact with ADK internals,
# e.g. setting actions.escalate = True to terminate a LoopAgent.
from google.adk.tools import ToolContext

# --- MCP Tool Support ---
# McpToolset wraps an external MCP server and exposes its tools to any LlmAgent.
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    SseConnectionParams,
)
from mcp import StdioServerParameters
