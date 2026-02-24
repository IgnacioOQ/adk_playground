# ADK Playground
- status: active
- type: plan
- label: [core, template]
<!-- content -->

## What is Google ADK?
- status: active
- type: documentation
<!-- content -->
The Agent Development Kit (ADK) is a flexible and modular framework developed by Google for building and deploying AI agents. While optimized for Gemini and the Google ecosystem, ADK is model-agnostic, deployment-agnostic, and designed to make agentic architectures feel more like traditional software development.

This repository serves as a playground and central nervous system for learning and experimenting with ADK concepts.

## Core Agent Categories
- status: active
- type: documentation
<!-- content -->
ADK provides distinct agent categories to build sophisticated applications:

1. **LLM Agents** (`LlmAgent`, `Agent`): These agents utilize Large Language Models (LLMs) as their core engine to understand natural language, reason, plan, generate responses, and dynamically decide how to proceed or which tools to use. They are ideal for flexible, language-centric tasks.
2. **Workflow Agents** (`SequentialAgent`, `ParallelAgent`, `LoopAgent`): These specialized agents control the execution flow of other agents in predefined, deterministic patterns (sequence, parallel, or loop) without using an LLM for the flow control itself. They are perfect for structured processes needing predictable execution.
3. **Custom Agents** (`BaseAgent`): Created by extending the `BaseAgent` directly, these allow you to implement unique operational logic, specific control flows, or specialized integrations not covered by the standard types.

## Multi-Agent Architecture
- status: active
- type: documentation
<!-- content -->
While each agent type serves a distinct purpose, complex applications frequently employ multi-agent architectures where:
- LLM Agents handle intelligent, language-based task execution.
- Workflow Agents manage the overall process flow using standard patterns.
- Custom Agents provide specialized capabilities or rules needed for unique integrations.

## Extending Capabilities
- status: active
- type: documentation
<!-- content -->
Beyond the core agent types, ADK allows significantly expanding what agents can do through:

- **AI Models**: Swap the underlying intelligence by integrating with generative AI models from Google and other providers.
- **Artifacts**: Enable agents to create and manage persistent outputs like files, code, or documents.
- **Pre-built Tools & Integrations**: Equip agents with tools to interact with the world (e.g., search, code execution).
- **Custom Tools**: Create your own task-specific tools.
- **Plugins**: Integrate complex, pre-packaged behaviors and third-party services.
- **Skills**: Use prebuilt or custom Agent Skills efficiently inside AI context limits.
- **Callbacks**: Hook into specific events during execution to add logging, monitoring, or custom side-effects.

## Installation
- status: active
- type: documentation
<!-- content -->
To install the Agent Development Kit in Python, simply run:

```bash
pip install google-adk
```

*(Note: ADK is also available for TypeScript, Go, and Java.)*

## Local Project Conventions
- status: active
- type: documentation
<!-- content -->
This playground enforces several project-specific conventions to maximize AI-agent efficiency:

- **Markdown-JSON Hybrid Schema**: All core Markdown files must follow a strict header-metadata format (described in `MD_CONVENTIONS.md`) ensuring loss-less conversion to JSON.
- **Agent Logs**: Every agent that performs a significant intervention must update `content/logs/AGENTS_LOG.md` (as per `AGENTS.md` guidelines).
- **Core Principles**: See `AGENTS.md` for human-assistant workflows, constraints, and instructions on context fine-tuning.

## Project Structure
- status: active
- type: documentation
<!-- content -->
This repository is organized to separate conversational contexts and agent code:

- `docs/`: Contains all specialized Markdown guidelines and skills (e.g., `AGENTS.md`, `MD_CONVENTIONS.md`, `MCP_GUIDELINE.md`). These files act as knowledge dependencies for the LLMs.
- `tutorial_agent/`: A functional "getting started" agent project created using the `adk create` CLI. 
  - `tutorial_agent/imports.py`: A centralized file that exports key ADK components (`Agent`, `SequentialAgent`, etc.). When building tools or exploring the framework, import ADK classes from here to maintain a clean architecture.
  - `tutorial_agent/agent.py`: The entry point containing the `root_agent` and any attached sample tools (like `get_current_time`).
  - `tutorial_agent/.env`: A local, git-ignored file containing your `GOOGLE_API_KEY`.
