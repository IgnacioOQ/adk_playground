# Pipeline Step 1: Load ADK Framework Components
# All ADK and MCP classes are imported from the centralized imports.py.
from .imports import LlmAgent, McpToolset, StdioConnectionParams, StdioServerParameters
import os

# Pipeline Step 2: Resolve the workspace path
# The MCP filesystem server requires an ABSOLUTE path to the directory it may access.
# We derive it relative to this file so the agent works from any working directory.
WORKSPACE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))

# Pipeline Step 3: Initialize the Agent
# The McpToolset replaces hand-written Python tool functions.
# ADK will spawn the MCP server subprocess on startup, discover its tools,
# and proxy any LLM tool calls to that server transparently.
#
# Naming conventions used here:
#   - Agent name  : <role>_agent         → "filesystem_assistant_agent"
#   - McpToolset  : one per MCP server   → connection_params describe the server
#   - tool_filter : explicit allowlist   → only expose tools the agent actually needs
root_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='filesystem_assistant_agent',
    description=(
        "An agent that can browse and manipulate files inside a sandboxed workspace "
        "directory using the MCP filesystem server."
    ),
    instruction=(
        "You are a helpful file-system assistant. You can list directories, read files, "
        "write files, and create directories — but only inside the designated workspace. "
        "Always show the user the results of your file operations in a clear, readable format. "
        "If an operation fails, explain why and suggest a fix."
    ),
    tools=[
        # McpToolset bridges ADK and the @modelcontextprotocol/server-filesystem npm package.
        # StdioConnectionParams launches the server as a local subprocess via npx.
        # tool_filter restricts which MCP-exposed tools this agent may invoke.
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx',
                    args=[
                        "-y",                                       # auto-install if missing
                        "@modelcontextprotocol/server-filesystem",  # the MCP server package
                        WORKSPACE_PATH,                             # sandboxed root directory
                    ],
                ),
            ),
            tool_filter=[
                'list_directory',
                'read_file',
                'write_file',
                'create_directory',
            ],
        )
    ],
)
