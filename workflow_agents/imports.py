"""
Centralized imports for the workflow_agents project.
Covers all three ADK workflow agent types alongside the core LlmAgent and ToolContext.

Workflow Agent Summary:
  - SequentialAgent : Runs sub_agents one after another, in order. Shares a single
                      InvocationContext across all steps — output from one step is
                      available to the next via session state.
  - ParallelAgent   : Runs sub_agents concurrently. Independent execution branches
                      with NO automatic state sharing between branches during execution.
  - LoopAgent       : Repeatedly runs sub_agents until a termination condition is met
                      (escalate=True via ToolContext.actions, or max_iterations reached).
"""

# --- Core Agent Types ---
# https://google.github.io/adk-docs/agents/
from google.adk.agents.llm_agent import LlmAgent

# --- Workflow Agents ---
# https://google.github.io/adk-docs/agents/workflow-agents/
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent

# --- Tool Support ---
# ToolContext is passed to Python tool functions that need to interact with ADK
# internals — e.g., setting actions.escalate = True to terminate a LoopAgent.
from google.adk.tools import ToolContext
