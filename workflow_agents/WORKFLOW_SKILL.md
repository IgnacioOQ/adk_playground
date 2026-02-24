# Workflow Agents Skill — Architecture & Implementation Guide
- status: active
- type: agent_skill
- id: workflow_agents.workflow_skill
- last_checked: 2026-02-24
- label: [guide, reference, backend]
<!-- content -->
This document describes the architecture, implementation, and usage of the `report_pipeline_agent` — an ADK agent that uses all **three workflow agent types** (SequentialAgent, ParallelAgent, LoopAgent) to generate a polished research report on any user-supplied topic.

It is the canonical worked example for workflow agent composition in this repository.

Reference: https://google.github.io/adk-docs/agents/workflow-agents/

## What Are Workflow Agents?
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.overview
- last_checked: 2026-02-24
<!-- content -->
Workflow agents are specialized ADK agents that control the **execution flow** of other agents using predefined, deterministic logic — **without using an LLM** for the flow control itself. Their sub-agents can be any agent type, including `LlmAgent` instances.

| Agent | Execution pattern | Use when… |
| :--- | :--- | :--- |
| `SequentialAgent` | Runs sub-agents **one after another**, in order | Steps have strict dependencies — output of step N feeds step N+1 |
| `ParallelAgent` | Runs sub-agents **concurrently** | Steps are independent and can safely run at the same time |
| `LoopAgent` | Runs sub-agents **repeatedly** until a stop signal or iteration cap | Output quality must be iteratively improved |

All three types share the same constructor shape:
```python
WorkflowAgent(
    name='agent_name',
    description='what it does',
    sub_agents=[agent_a, agent_b, ...],
    # LoopAgent only:
    max_iterations=N,
)
```

## Architecture Overview
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.architecture
- last_checked: 2026-02-24
<!-- content -->
The pipeline is orchestrated by a top-level `SequentialAgent` that chains three phases in strict order:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        report_pipeline_agent                             │
│                           (SequentialAgent)                              │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │ Phase 1: research_phase_agent  (ParallelAgent)                   │   │
│   │                                                                  │   │
│   │  ┌────────────────────┐  ┌────────────────────┐  ┌───────────┐  │   │
│   │  │ overview_researcher│  │examples_researcher │  │limitations│  │   │
│   │  │    (LlmAgent)      │  │    (LlmAgent)      │  │researcher │  │   │
│   │  │  → state["overview"]  → state["examples"]  │  │(LlmAgent) │  │   │
│   │  └────────────────────┘  └────────────────────┘  │ →state    │  │   │
│   │                                                   │["limits"] │  │   │
│   │                                                   └───────────┘  │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                   │                                      │
│                                   ▼ (all three state keys now set)       │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │ Phase 2: drafting_agent  (LlmAgent)                              │   │
│   │  reads {overview} + {examples} + {limitations} from state        │   │
│   │  → state["draft"]                                                │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                   │                                      │
│                                   ▼                                      │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │ Phase 3: refinement_loop_agent  (LoopAgent, max_iterations=3)    │   │
│   │                                                                  │   │
│   │   ┌─────────────────────────────────────────────────────────┐    │   │
│   │   │ Each iteration:                                         │    │   │
│   │   │  1. reviewer_agent (LlmAgent)                           │    │   │
│   │   │     reads {draft} → writes {review_notes}               │    │   │
│   │   │     if approved → calls exit_loop() → STOP              │    │   │
│   │   │  2. editor_agent (LlmAgent)                             │    │   │
│   │   │     reads {draft} + {review_notes} → rewrites {draft}   │    │   │
│   │   └─────────────────────────────────────────────────────────┘    │   │
│   └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Session state at each transition:**

| After phase | Keys set in state |
| :--- | :--- |
| Phase 1 (ParallelAgent) | `overview`, `examples`, `limitations` |
| Phase 2 (LlmAgent) | `draft` |
| Phase 3 each iteration | `review_notes` (updated), `draft` (updated) |

## File Structure
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.file_structure
- last_checked: 2026-02-24
<!-- content -->
```
workflow_agents/
├── __init__.py                # Python package marker
├── .env                       # Git-ignored — contains GOOGLE_API_KEY
├── imports.py                 # Centralized ADK workflow + LlmAgent imports
├── agent.py                   # All agent definitions and root_agent
├── WORKFLOW_SKILL.md          # This file
└── tools/
    ├── __init__.py
    └── loop_control.py        # exit_loop tool — signals the LoopAgent to stop
```

## The Three Workflow Agents in Detail
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.agent_types
- last_checked: 2026-02-24
<!-- content -->

### SequentialAgent
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.agent_types.sequential
- last_checked: 2026-02-24
<!-- content -->
Runs sub-agents **strictly in order**, one at a time. All sub-agents share the same `InvocationContext`, meaning session state written by step N is immediately readable by step N+1.

```python
root_agent = SequentialAgent(
    name='report_pipeline_agent',
    description='Full research-draft-refine pipeline.',
    sub_agents=[
        research_phase_agent,   # step 1
        drafting_agent,         # step 2 — can read step 1's output_key values
        refinement_loop_agent,  # step 3 — can read step 2's output_key values
    ],
)
```

**Key properties:**
- Execution is **deterministic** — sub-agents always run in the same order.
- No LLM is used to decide what to run next; it is purely positional.
- Ideal as the **outermost orchestrator** in a multi-phase pipeline.

**State passing pattern** — use `output_key` on each sub-agent, then reference it with `{key}` placeholders in downstream agents' `instruction` strings:

```python
step_a = LlmAgent(..., output_key='result_a')
step_b = LlmAgent(..., instruction='Use this: {result_a}', output_key='result_b')
pipeline = SequentialAgent(name='pipe', sub_agents=[step_a, step_b])
```

### ParallelAgent
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.agent_types.parallel
- last_checked: 2026-02-24
<!-- content -->
Runs sub-agents **concurrently**. All branches start at approximately the same time and run independently.

```python
research_phase_agent = ParallelAgent(
    name='research_phase_agent',
    description='Three independent research angles run simultaneously.',
    sub_agents=[
        overview_researcher_agent,      # → state["overview"]
        examples_researcher_agent,      # → state["examples"]
        limitations_researcher_agent,   # → state["limitations"]
    ],
)
```

**Key properties:**
- **No automatic state sharing** between branches during execution. Each branch writes to its own `output_key` in isolation.
- Result order is **non-deterministic** — do not rely on which branch finishes first.
- Best used when sub-tasks are fully independent (fan-out pattern).
- Combine with a downstream `SequentialAgent` step (fan-in) to merge the parallel outputs.

**Fan-out / fan-in pattern:**
```
SequentialAgent
  └─ ParallelAgent (fan-out: A, B, C run concurrently → state["a"], ["b"], ["c"])
  └─ LlmAgent     (fan-in: instruction reads {a}, {b}, {c} and synthesises them)
```

### LoopAgent
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.agent_types.loop
- last_checked: 2026-02-24
<!-- content -->
Repeatedly runs its sub-agents in order until a **termination condition** is met.

```python
refinement_loop_agent = LoopAgent(
    name='refinement_loop_agent',
    description='Reviewer–editor loop until quality is approved.',
    sub_agents=[reviewer_agent, editor_agent],
    max_iterations=3,   # hard safety cap
)
```

**Termination mechanisms** — you MUST implement at least one:

| Mechanism | How it works |
| :--- | :--- |
| `max_iterations` | Hard cap — the loop always stops after N full iterations |
| `escalate` flag | A sub-agent calls `tool_context.actions.escalate = True` inside a tool — preferred termination path |

**The `exit_loop` tool pattern:**
```python
# tools/loop_control.py
from google.adk.tools import ToolContext

def exit_loop(tool_context: ToolContext) -> dict:
    """Call this to approve the output and stop the loop."""
    tool_context.actions.escalate = True
    return {"status": "approved"}
```

```python
# In the reviewer LlmAgent:
reviewer_agent = LlmAgent(
    ...,
    tools=[exit_loop],   # LLM can now invoke exit_loop when satisfied
    instruction=(
        'Review the draft. '
        'If quality is acceptable, call exit_loop. '
        'Otherwise, write improvement notes.'
    ),
)
```

**Key properties:**
- Sub-agents within each iteration share the same session state and can read/overwrite each other's `output_key` values.
- The `editor_agent` writes back to `output_key='draft'` — this **overwrites** the previous draft in state, so the next iteration's reviewer sees the freshest version.
- Always set `max_iterations` as a safety cap in case the reviewer never calls `exit_loop`.

## Implementation Walkthrough
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.implementation
- last_checked: 2026-02-24
<!-- content -->

### Imports (`imports.py`)
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.implementation.imports
- last_checked: 2026-02-24
<!-- content -->
```python
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.tools import ToolContext  # needed for exit_loop tool
```

### Naming Conventions
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.implementation.naming
- last_checked: 2026-02-24
<!-- content -->
| Element | Convention | Example |
| :--- | :--- | :--- |
| All agent variables | `<role>_agent` | `drafting_agent`, `reviewer_agent` |
| Workflow orchestrators | `<pipeline_name>_agent` | `report_pipeline_agent`, `research_phase_agent` |
| `output_key` values | `snake_case` noun | `"overview"`, `"draft"`, `"review_notes"` |
| State placeholder in instructions | `{output_key}` | `{draft}`, `{review_notes}` |
| Loop control tool | `exit_loop` | always this name — it is self-documenting |

### output_key & State Flow
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.implementation.output_key
- last_checked: 2026-02-24
<!-- content -->
`output_key` is an `LlmAgent` parameter. When set, ADK stores the agent's last text response into `session.state[output_key]` after it finishes.

Any downstream agent in the same `InvocationContext` can read this value via a `{key}` placeholder in its `instruction` string. ADK resolves placeholders at runtime, just before calling the LLM.

```
LlmAgent(output_key="draft")   →  session.state["draft"] = "<agent's last response>"

LlmAgent(instruction="Revise: {draft}")
                               →  instruction becomes "Revise: <previous draft text>"
```

## Example Interactions
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.examples
- last_checked: 2026-02-24
<!-- content -->

### Example 1 — Generate a report on a technology topic
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.examples.technology
- last_checked: 2026-02-24
<!-- content -->
**User:** Write me a research report on transformer neural networks.

**Pipeline execution:**
1. `research_phase_agent` fans out — three LlmAgents research overview, examples, and limitations **concurrently**.
2. `drafting_agent` synthesises the three outputs into a structured 5-section draft.
3. `refinement_loop_agent` runs up to 3 iterations: reviewer critiques → editor improves → reviewer re-evaluates. When satisfied, reviewer calls `exit_loop` and the loop terminates.
4. The final `draft` in session state is returned to the user.

### Example 2 — Scientific topic with many limitations
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.examples.science
- last_checked: 2026-02-24
<!-- content -->
**User:** Write a report on CRISPR gene editing.

**Expected loop behaviour:** The first draft may have weak coverage of ethical debates. The `reviewer_agent` will note this. The `editor_agent` expands the Challenges section. On the next iteration, the reviewer approves and calls `exit_loop` after iteration 2.

### Example 3 — Short topic, fast approval
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.examples.short
- last_checked: 2026-02-24
<!-- content -->
**User:** Write a report on the TCP/IP protocol.

**Expected loop behaviour:** A well-defined technical topic with clear structure. The `reviewer_agent` may approve on the **first iteration**, calling `exit_loop` immediately. The loop runs only once.

## Running the Agent
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.running
- last_checked: 2026-02-24
<!-- content -->

### Prerequisites
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.running.prerequisites
- last_checked: 2026-02-24
<!-- content -->
1. Python virtual environment activated with `google-adk` installed.
2. `GOOGLE_API_KEY` set in `workflow_agents/.env`.

### Web UI (recommended)
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.running.web
- last_checked: 2026-02-24
<!-- content -->
```bash
source .venv/bin/activate
adk web --port 8000
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000), select **workflow_agents** from the dropdown, then type any topic to generate a report.

### CLI
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.running.cli
- last_checked: 2026-02-24
<!-- content -->
```bash
adk run workflow_agents
```

### What to expect in the ADK Web UI
- status: active
- type: documentation
- id: workflow_agents.workflow_skill.running.ui_behaviour
- last_checked: 2026-02-24
<!-- content -->
The ADK Web UI shows each sub-agent's execution as a nested trace. You will see:
- Three parallel branches under `research_phase_agent` running simultaneously.
- `drafting_agent` start only after all three parallel branches complete.
- `refinement_loop_agent` showing multiple iterations (each with a `reviewer_agent` and `editor_agent` turn).
- The loop ending early if the `reviewer_agent` calls `exit_loop`.
