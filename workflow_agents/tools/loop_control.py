# Loop control tools for LoopAgent sub-agents.
#
# The LoopAgent does NOT decide by itself when to stop — a sub-agent must
# explicitly signal termination by calling exit_loop(), which sets
# tool_context.actions.escalate = True.  The LoopAgent detects this flag
# after the current sub-agent finishes and stops iterating.
from google.adk.tools import ToolContext


def exit_loop(tool_context: ToolContext) -> dict:
    """
    Signal the enclosing LoopAgent to stop iterating.

    Call this tool when the current draft or output has reached an acceptable
    quality level and no further refinement is needed.  The LoopAgent will not
    start another iteration after this tool is invoked.

    Returns a confirmation dict so the LLM receives clear feedback.
    """
    tool_context.actions.escalate = True
    return {
        "status": "approved",
        "message": "Quality check passed. Loop terminated — no further iterations needed.",
    }
