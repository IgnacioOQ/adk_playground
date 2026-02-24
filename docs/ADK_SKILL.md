# Google ADK Implementation Skill
- status: active
- type: agent_skill
- id: skill.adk_implementation
- last_checked: 2026-02-24
- label: [agent, guide, infrastructure]
<!-- content -->
This document serves as the primary implementation guideline and playbook for building, scaffolding, and integrating Google's Agent Development Kit (ADK) into projects. 

[ADK](https://google.github.io/adk-docs/) is a Python-first framework (with support for TS, Go, Java) designed to build model-agnostic, easily orchestratable AI agents using standard software engineering patterns instead of obscure prompting frameworks.

## 1. Creating an ADK Project From Scratch
- status: active
- type: guideline
- id: skill.adk_implementation.creating_project
- last_checked: 2026-02-24
- label: [infrastructure]
<!-- content -->
When starting a completely new, agent-first project, follow this standard initialization sequence:

1. **Virtual Environment**: Keep dependencies isolated.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install ADK**:
   ```bash
   pip install google-adk
   # Optional: Upgrade pip to avoid build errors with 'pyarrow'
   pip install --upgrade pip
   ```
3. **Scaffold Project**: Use the CLI to interactively generate the agent skeleton.
   ```bash
   adk create my_new_agent
   ```
   *Select `Google AI` (Gemini API) or `Vertex AI` backend. Opt for `gemini-2.5-flash` as a fast default.*

## 2. Integrating ADK into Existing Projects
- status: active
- type: guideline
- id: skill.adk_implementation.integrating_adk
- last_checked: 2026-02-24
- label: [infrastructure]
<!-- content -->
If a repository already has existing application code (e.g., a React frontend, an Express backend), you must integrate ADK without polluting the existing structure.

**Convention: The Isolated Agent Directory**
Do not build ADK agents in the root of an existing app. Create a dedicated folder (e.g., `ai_agents/` or `services/agent_service/`).

1. `cd ai_agents`
2. Run standard initialization (`venv`, `pip install`, `adk create`).
3. Set up a local `requirements.txt` specifically for the agent isolated from the main app's `package.json` or other setups.

## 3. Implementation Conventions & Tricks
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks
- last_checked: 2026-02-24
- label: [core]
<!-- content -->
To ensure ADK applications scale cleanly, adhere to these battle-tested conventions:

### The `imports.py` Centralization Pattern
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks.imports_py
- last_checked: 2026-02-24
<!-- content -->
**Problem**: The `google.adk` package is massive. Importing specific classes ([`LlmAgent`](https://google.github.io/adk-docs/agents/), [`SequentialAgent`](https://google.github.io/adk-docs/agents/workflows/), `BaseAgent`) across dozens of files creates brittle references.

**Solution**: Create an `imports.py` file alongside your main `agent.py`.
```python
# imports.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent
```
Then, inside `agent.py` and other files:
```python
from .imports import LlmAgent, SequentialAgent
```

### Tool Definition Separation
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks.tool_definition_separation
- last_checked: 2026-02-24
<!-- content -->
Do not define complex action functions ([Tools](https://google.github.io/adk-docs/tools/)) directly inside `agent.py`. 
1. Create a `tools/` directory.
2. Group related tools into files (e.g., `tools/time_tools.py`, `tools/db_tools.py`).
3. Import the specific functions into `agent.py` and append them to the `tools=[...]` array during Agent initialization.

### Environment & Secrets Management
- status: active
- type: guideline
- id: skill.adk_implementation.conventions_and_tricks.environment_and_secrets
- last_checked: 2026-02-24
<!-- content -->
ADK applications inherently rely on standard `.env` variables (like `GOOGLE_API_KEY`).
1. **Never commit `.env`**: Always ensure `.env` and `*.env` are in `.gitignore`.
2. **Execution Context**: The `adk web` and `adk run` commands (see [CLI documentation](https://google.github.io/adk-docs/cli/)) automatically look for the `.env` file in the folder where the agent lives (e.g., `my_new_agent/.env`).

## 4. Execution & Testing
- status: active
- type: guideline
- id: skill.adk_implementation.execution_and_testing
- last_checked: 2026-02-24
- label: [infrastructure]
<!-- content -->
[ADK comes with two built-in runners](https://google.github.io/adk-docs/cli/) that hot-reload differently:
- **CLI Runner** (`adk run <agent_folder>`): Interactive terminal.
- **Web Runner** (`adk web --port 8000` from project root): Provides a chat GUI at `localhost:8000`. 

**Critical Trick for Web Runner**: If you change the underlying Python tool implementations (e.g., changing how a function fetches data), the `adk web` background process *may not instantly hot-reload* the tool logic. You must terminate and restart the web server to guarantee new Python tool logic is picked up.
