# Pipeline Step 1: Load ADK Framework Components
# We import from our centralized imports.py file to keep the code clean.
from .imports import LlmAgent
from datetime import datetime
import zoneinfo

# Pipeline Step 2: Define Tools
# Tools are functions that the LLM agent can decide to call when it needs external information or to perform an action.
def get_current_time(timezone: str) -> dict:
    """
    Returns the current time in a specified IANA timezone.
    For example, for Paris, the timezone should be 'Europe/Paris'.
    """
    try:
        tz = zoneinfo.ZoneInfo(timezone)
        current_time = datetime.now(tz)
        return {"status": "success", "timezone": timezone, "datetime": current_time.isoformat()}
    except zoneinfo.ZoneInfoNotFoundError:
        return {"status": "error", "message": f"Could not find timezone: {timezone}. Please provide a valid IANA timezone string."}
    except Exception as e:
        return {"status": "error", "message": f"An error occurred: {str(e)}"}

# Pipeline Step 3: Initialize the Agent
# We create an instance of the LlmAgent class, configuring its identity and capabilities.
root_agent = LlmAgent(
    model='gemini-2.5-flash', # The specific LLM model to use
    name='root_agent',        # The programmatic identifier for this agent
    description="Tells the current time in a specified location.", # Explains what this agent does (useful in multi-agent setups)
    instruction="You are a helpful assistant that tells the current time in cities. First, determine the standard IANA timezone string for the requested city (e.g., 'Europe/Paris' for Paris, 'America/New_York' for New York). Then, use the 'get_current_time' tool by passing that exact timezone string.", # The system prompt guiding the agent's behavior
    tools=[get_current_time], # The list of tools the agent is allowed to use
)
