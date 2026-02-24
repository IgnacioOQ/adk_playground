# Ecosystem Agent Skill — Workflow + MCP Integration Guide
- status: active
- type: agent_skill
- id: ecosystem.skill
- last_checked: 2026-02-24
- label: [guide, reference, backend, mcp, workflow]
<!-- content -->
This document describes the `ecosystem/` project — the canonical example of combining ADK **workflow agents** (for pipeline structure) with **MCP tools** (for live external capabilities). It serves as the starting point for building multi-agent _ecosystems_ that solve complex tasks by layering deterministic orchestration on top of real-world data access.

The primary example: a **web-sourced research pipeline** that fetches live internet data inside a parallel research phase, drafts a report, and iteratively refines it.

## What Is an Ecosystem Agent?
- status: active
- type: documentation
- id: ecosystem.skill.overview
- last_checked: 2026-02-24
<!-- content -->
An **ecosystem agent** is a multi-agent pipeline where:
- **Workflow agents** define the structure and execution order (Sequential, Parallel, Loop).
- **MCP tools** inject live, external capabilities (web fetch, file system, databases, APIs) into the `LlmAgent` sub-agents that do the actual work.

The two layers are orthogonal and combine cleanly:

```
WorkflowAgent (structure)
  └── LlmAgent (intelligence) + McpToolset (live capability)
```

This separation makes it straightforward to design ecosystems for arbitrary tasks by choosing:
1. The right workflow shape (how many phases, which run in parallel, which loops).
2. The right MCP servers (what external capabilities each phase needs).

## Architecture
- status: active
- type: documentation
- id: ecosystem.skill.architecture
- last_checked: 2026-02-24
<!-- content -->

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       web_research_pipeline_agent                            │
│                           (SequentialAgent)                                  │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ Phase 1: research_phase_agent  (ParallelAgent)                       │   │
│   │                                                                      │   │
│   │  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────┐ │   │
│   │  │ overview_researcher  │  │ examples_researcher  │  │limitations │ │   │
│   │  │    (LlmAgent)        │  │    (LlmAgent)        │  │_researcher │ │   │
│   │  │  + McpToolset[fetch] │  │  + McpToolset[fetch] │  │(LlmAgent)  │ │   │
│   │  │  → state["overview"] │  │  → state["examples"] │  │+McpToolset │ │   │
│   │  └──────────────────────┘  └──────────────────────┘  │→state      │ │   │
│   │                                                       │["limits"]  │ │   │
│   │                                                       └────────────┘ │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                   │                                          │
│                                   ▼ (all three output_keys now set)          │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ Phase 2: drafting_agent  (LlmAgent)                                  │   │
│   │  reads {overview} + {examples} + {limitations} from state            │   │
│   │  → state["draft"]  (with a Sources section citing fetched URLs)      │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                   │                                          │
│                                   ▼                                          │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │ Phase 3: refinement_loop_agent  (LoopAgent, max_iterations=3)        │   │
│   │                                                                      │   │
│   │   ┌─────────────────────────────────────────────────────────────┐    │   │
│   │   │ Each iteration:                                             │    │   │
│   │   │  1. reviewer_agent (LlmAgent + exit_loop tool)             │    │   │
│   │   │     reads {draft} → writes {review_notes}                  │    │   │
│   │   │     if approved → calls exit_loop() → STOP                 │    │   │
│   │   │  2. editor_agent (LlmAgent)                                │    │   │
│   │   │     reads {draft} + {review_notes} → rewrites {draft}      │    │   │
│   │   └─────────────────────────────────────────────────────────────┘    │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key difference from `workflow_agents/`:** Each parallel researcher has a live `McpToolset[fetch]` connection. They call the `fetch` tool to retrieve Wikipedia pages (or other relevant URLs) before synthesising their research angle. The final report includes a Sources section with the URLs fetched during research.

## File Structure
- status: active
- type: documentation
- id: ecosystem.skill.file_structure
- last_checked: 2026-02-24
<!-- content -->
```
ecosystem/
├── __init__.py                # Python package marker
├── .env                       # Git-ignored — contains GOOGLE_API_KEY
├── imports.py                 # Centralized ADK imports: workflow agents + MCP classes
├── agent.py                   # Full pipeline definition and root_agent
├── ADK_ECOSYSTEM_SKILL.md     # This file
└── tools/
    ├── __init__.py
    └── loop_control.py        # exit_loop tool — signals the LoopAgent to stop
```

## How the Two Layers Combine
- status: active
- type: documentation
- id: ecosystem.skill.combination
- last_checked: 2026-02-24
<!-- content -->

### Layer 1 — Workflow Structure (unchanged from workflow_agents)
`SequentialAgent` → `ParallelAgent` → `LlmAgent` → `LoopAgent` form the skeleton of the pipeline. No LLM is involved in deciding what runs next — the structure is fully deterministic.

### Layer 2 — MCP Capabilities (new in ecosystem)
Each of the three parallel researchers holds its own `McpToolset` instance backed by `mcp-server-fetch`. This gives the `LlmAgent` the ability to call `fetch(url)` during its turn to pull live content from the web.

```python
# MCP toolset factory — call once per agent (connections are per-agent)
def _fetch_toolset() -> McpToolset:
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command='uvx',
                args=['mcp-server-fetch'],
            ),
        ),
        tool_filter=['fetch'],
    )

# Each researcher gets its own instance
overview_researcher_agent = LlmAgent(
    name='overview_researcher_agent',
    output_key='overview',
    tools=[_fetch_toolset()],   # ← MCP fetch capability injected here
    instruction=('... fetch a Wikipedia page and summarise ...'),
)
```

### Why a factory function?
MCP connections are per-agent. If the same `McpToolset` object were shared across agents, it would use a single connection for all three parallel branches — causing contention. The `_fetch_toolset()` factory ensures each agent gets an independent connection.

## Session State Flow
- status: active
- type: documentation
- id: ecosystem.skill.state_flow
- last_checked: 2026-02-24
<!-- content -->

| After phase | Keys set in state |
| :--- | :--- |
| Phase 1 (ParallelAgent) | `overview`, `examples`, `limitations` (each includes a `Source:` URL) |
| Phase 2 (LlmAgent) | `draft` (5-section report + Sources section) |
| Phase 3 each iteration | `review_notes` (updated), `draft` (updated) |

## Extending the Ecosystem
- status: active
- type: documentation
- id: ecosystem.skill.extending
- last_checked: 2026-02-24
<!-- content -->
This project is designed as a foundation. Common extensions:

| Extension | How to add |
| :--- | :--- |
| **Save report to file** | Add an `LlmAgent` with `McpToolset(filesystem)` as a Phase 4 step in the `SequentialAgent` |
| **More research angles** | Add more `LlmAgent` branches to the `ParallelAgent` — each with its own `_fetch_toolset()` and `output_key` |
| **Deeper search** | Replace `mcp-server-fetch` with a search-capable MCP server (e.g. `mcp-server-brave-search`) for keyword queries instead of direct URL fetches |
| **Persistent memory** | Add `McpToolset(memory-server)` to agents that need to store or recall cross-session facts |
| **Different pipeline shapes** | Swap the outer `SequentialAgent` for any composition pattern from `ADK_WORKFLOW_SKILL.md` |

## Running the Agent
- status: active
- type: documentation
- id: ecosystem.skill.running
- last_checked: 2026-02-24
<!-- content -->

### Prerequisites
1. Python virtual environment activated with `google-adk` installed.
2. `GOOGLE_API_KEY` set in `ecosystem/.env` (copy from `tutorial_agent/.env`).
3. `uvx` available — install via `pip install uv` if needed. Used to spawn `mcp-server-fetch`.

### Web UI (recommended)
```bash
source .venv/bin/activate
adk web --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000), select **ecosystem** from the dropdown, then type any topic to generate a web-sourced report.

### CLI
```bash
adk run ecosystem
```

### What to expect
The ADK Web UI will show:
- Three parallel branches under `research_phase_agent`, each spawning an `mcp-server-fetch` subprocess and calling `fetch` to retrieve web content.
- `drafting_agent` starting only after all three branches complete, synthesising the fetched content into a structured report with a Sources section.
- `refinement_loop_agent` running up to 3 iterations (reviewer → editor), with the loop potentially terminating early when the reviewer calls `exit_loop`.
