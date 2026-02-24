# Pipeline Step 1: Load ADK Framework Components
# We import from our centralized imports.py file to keep the code clean.
from .imports import Agent
import requests

# Pipeline Step 2: Define Tools
# Tools are functions that the LLM agent can decide to call when it needs external information or to perform an action.
def get_current_time(timezone: str) -> dict:
    """
    Returns the current time in a specified IANA timezone.
    For example, for Paris, the timezone should be 'Europe/Paris'.
    """
    try:
        response = requests.get(f"http://worldtimeapi.org/api/timezone/{timezone}")
        response.raise_for_status()
        data = response.json()
        return {"status": "success", "timezone": timezone, "datetime": data.get("datetime")}
    except Exception as e:
        return {"status": "error", "message": f"Could not fetch time for {timezone}. Error: {str(e)}"}

# Pipeline Step 3: Initialize the Agent
# We create an instance of the Agent class, configuring its identity and capabilities.
root_agent = Agent(
    model='gemini-2.5-flash', # The specific LLM model to use
    name='root_agent',        # The programmatic identifier for this agent
    description="Tells the current time in a specified location.", # Explains what this agent does (useful in multi-agent setups)
    instruction="You are a helpful assistant that tells the current time in cities. First, determine the standard IANA timezone string for the requested city (e.g., 'Europe/Paris' for Paris, 'America/New_York' for New York). Then, use the 'get_current_time' tool by passing that exact timezone string.", # The system prompt guiding the agent's behavior
    tools=[get_current_time], # The list of tools the agent is allowed to use
)
