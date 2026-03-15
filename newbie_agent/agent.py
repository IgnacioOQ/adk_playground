from google.adk.agents.llm_agent import Agent
from google.adk.tools import google_search

# Mock tool implementation
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": "10:30 AM"}

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
    tools=[get_current_time],
)

google_search_agent = Agent(
    # A unique name for the agent.
    name="basic_search_agent",
    # The Large Language Model (LLM) that agent will use.
    # Please fill in the latest model id that supports live from
    # https://google.github.io/adk-docs/get-started/streaming/quickstart-streaming/#supported-models
    model="gemini-2.5-flash-native-audio-preview-12-2025",
    # A short description of the agent's purpose.
    description="Agent to answer questions using Google Search.",
    # Instructions to set the agent's behavior.
   #instruction="You are an expert researcher. You believe conspiracy theories that make sense.",
    instruction="You are a describer. Every 5 seconds, if what you are seeing changed significantly, describe what you are seeing.",
    # Add google_search tool to perform grounding with Google search.
    tools=[google_search]

)

root_agent = google_search_agent