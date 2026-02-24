"""
Centralized imports for the ADK Playground.
This file serves as a single entry point for all google-adk components used across the project docs and code.

Pipeline Step 1: Framework Component Centralization
Instead of importing from deep within `google.adk` in every file, we centralize them here.
This makes the agent code cleaner and easier to maintain.
"""
# https://google.github.io/adk-docs/agents/
# Core Agent Types: The building blocks of your ADK applications.
# BaseAgent: The foundation for creating custom agents.
# LlmAgent: Agents powered by Large Language Models (like Gemini).
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.llm_agent import LlmAgent

# Workflow Agents: Used to orchestrate other agents in specific patterns.
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent

# Common Models: The AI engines that power your LlmAgents.
try:
    from google.adk.models.google_llm import Gemini
except ImportError:
    pass # Adjust based on the exact Google GenAI wrapper used internally

# Add additional pre-built tools here as we discover them
# e.g from google.adk.tools import ...
