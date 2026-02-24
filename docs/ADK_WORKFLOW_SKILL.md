# ADK Workflow Agents Skill — Orchestration Guide
- status: active
- type: agent_skill
- id: skill.adk_workflow
- last_checked: 2026-02-24
- label: [agent, guide, infrastructure, backend]
<!-- content -->
This document is the primary reference for building multi-agent pipelines with ADK's three **workflow agent types**: `SequentialAgent`, `ParallelAgent`, and `LoopAgent`. It covers architecture, all core classes and their import paths, state management, how tools integrate with workflow sub-agents, composition patterns, a catalogue of 24+ named workflow patterns, design principles, and troubleshooting.

Reference: https://google.github.io/adk-docs/agents/workflow-agents/

## 1. What Are Workflow Agents?
- status: active
- type: guideline
- id: skill.adk_workflow.overview
- last_checked: 2026-02-24
<!-- content -->
Workflow agents are specialized ADK agents that control the **execution flow** of other agents using **predefined, deterministic logic** — no LLM is involved in the flow control itself. Their sub-agents can be any agent type, including other workflow agents, `LlmAgent` instances, or custom `BaseAgent` subclasses.

This separation of concerns is the key insight: workflow agents handle **structure**, while `LlmAgent` sub-agents handle **intelligence**.

| Agent | Execution pattern | Core use case |
| :--- | :--- | :--- |
| `SequentialAgent` | Sub-agents run **one after another**, in order | Steps have strict dependencies — output of step N feeds step N+1 |
| `ParallelAgent` | Sub-agents run **concurrently** | Steps are fully independent and benefit from parallel execution |
| `LoopAgent` | Sub-agents run **repeatedly** until a stop signal or iteration cap | Output quality must be improved iteratively |

All workflow agents are **non-LLM** — they never call a model to decide what to run next. This makes them completely deterministic and inspectable.

## 2. Core Classes & Import Conventions
- status: active
- type: guideline
- id: skill.adk_workflow.imports
- last_checked: 2026-02-24
<!-- content -->
All workflow agent classes must be imported in the agent package's `imports.py`. Never scatter these imports across sub-agent files.

```python
# In imports.py — the single source of truth for all ADK agent classes

# Core intelligent agent — the building block that workflow agents orchestrate.
from google.adk.agents.llm_agent import LlmAgent

# Workflow orchestrators — deterministic, non-LLM flow control.
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.loop_agent import LoopAgent

# ToolContext: passed to Python tool functions that need to interact with ADK
# internals. Required for the exit_loop pattern (setting actions.escalate).
from google.adk.tools import ToolContext
```

Then in `agent.py`:
```python
from .imports import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from .tools.loop_control import exit_loop   # if using LoopAgent
```

## 3. Agent Type Deep Dive
- status: active
- type: guideline
- id: skill.adk_workflow.agent_types
- last_checked: 2026-02-24
<!-- content -->

### SequentialAgent
- status: active
- type: guideline
- id: skill.adk_workflow.agent_types.sequential
- last_checked: 2026-02-24
<!-- content -->
Runs sub-agents **strictly in order**, waiting for each to complete before starting the next. All sub-agents share the same `InvocationContext`, so session state written by step N is immediately readable by step N+1.

**Constructor:**
```python
SequentialAgent(
    name='pipeline_agent',
    description='What the full pipeline produces.',
    sub_agents=[step_a, step_b, step_c],   # executed in this order
)
```

**Constructor parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | Yes | Unique identifier for this agent |
| `description` | `str` | No | Explains what the pipeline produces; used in multi-agent contexts |
| `sub_agents` | `list[BaseAgent]` | Yes | Agents executed in list order |

**Key properties:**
- Execution is guaranteed to be in list order — no LLM decides the sequence.
- The shared `InvocationContext` means `output_key` values written by earlier steps are accessible to later steps as `{key}` placeholders in `instruction` strings.
- Best used as the **outermost orchestrator** when combining all three workflow types.
- Sub-agents can themselves be `ParallelAgent` or `LoopAgent` instances.

### ParallelAgent
- status: active
- type: guideline
- id: skill.adk_workflow.agent_types.parallel
- last_checked: 2026-02-24
<!-- content -->
Runs sub-agents **concurrently**. All branches start at approximately the same time and execute independently.

**Constructor:**
```python
ParallelAgent(
    name='fan_out_agent',
    description='Runs N independent tasks simultaneously.',
    sub_agents=[branch_a, branch_b, branch_c],
)
```

**Constructor parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | Yes | Unique identifier |
| `description` | `str` | No | Describes the parallel work being done |
| `sub_agents` | `list[BaseAgent]` | Yes | All agents run concurrently |

**Key properties:**
- **No automatic state sharing** between branches during execution. Each branch writes to its own `output_key` in isolation.
- Result order is **non-deterministic** — do not assume which branch finishes first.
- All branches must complete before the `ParallelAgent` returns control to its parent.
- Designed for the **fan-out** half of a fan-out/fan-in pattern; pair with a downstream `LlmAgent` or `SequentialAgent` step to merge results.
- Race conditions: if two branches write to the same `output_key`, the last writer wins. Avoid this — always give each branch a unique key.

### LoopAgent
- status: active
- type: guideline
- id: skill.adk_workflow.agent_types.loop
- last_checked: 2026-02-24
<!-- content -->
Repeatedly runs its sub-agents in order until a **termination condition** is triggered or the iteration cap is reached.

**Constructor:**
```python
LoopAgent(
    name='refinement_loop_agent',
    description='Iteratively improves output until quality is acceptable.',
    sub_agents=[evaluator_agent, improver_agent],
    max_iterations=5,   # hard safety cap — always set this
)
```

**Constructor parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | Yes | Unique identifier |
| `description` | `str` | No | Describes what the loop is refining |
| `sub_agents` | `list[BaseAgent]` | Yes | Agents run in order on each iteration |
| `max_iterations` | `int` | No | Hard cap on iterations. **Always set this** as a safety net. |

**Termination mechanisms:**

| Mechanism | How to implement |
| :--- | :--- |
| `max_iterations` | Pass an integer to the constructor. Loop stops after N full iterations regardless of agent output. |
| `escalate` flag | A sub-agent calls `tool_context.actions.escalate = True` inside a tool function. The loop stops after that sub-agent finishes. |

**Key properties:**
- Sub-agents within each iteration share session state and can read/overwrite each other's `output_key` values.
- An `output_key` that is overwritten each iteration (e.g. `"draft"`) always holds the latest version — subsequent iterations always see the freshest value.
- The `LoopAgent` itself **never** decides to stop — you must implement at least one termination mechanism.
- Always pair `max_iterations` with an `escalate`-based tool — `max_iterations` is the safety net, not the primary exit.

## 4. State Management & output_key
- status: active
- type: guideline
- id: skill.adk_workflow.state
- last_checked: 2026-02-24
<!-- content -->
State is the primary data transport between workflow steps. Understanding it is essential.

### How output_key works
- status: active
- type: guideline
- id: skill.adk_workflow.state.output_key
- last_checked: 2026-02-24
<!-- content -->
`output_key` is an `LlmAgent` parameter. After the agent finishes, ADK stores its last text response into `session.state[output_key]`.

```python
step_a = LlmAgent(
    name='step_a_agent',
    instruction='Write a haiku about Python.',
    output_key='haiku',   # last response → session.state["haiku"]
)

step_b = LlmAgent(
    name='step_b_agent',
    # {haiku} is resolved from session.state["haiku"] at runtime
    instruction='Translate this haiku into Spanish: {haiku}',
    output_key='translated_haiku',
)

pipeline = SequentialAgent(name='haiku_pipeline', sub_agents=[step_a, step_b])
```

### State namespace rules
- status: active
- type: guideline
- id: skill.adk_workflow.state.namespaces
- last_checked: 2026-02-24
<!-- content -->
ADK session state supports namespaced keys to control scope and persistence:

| Prefix | Scope | Example |
| :--- | :--- | :--- |
| *(none)* | Session — persists for the current conversation | `"draft"`, `"summary"` |
| `temp:` | Turn — discarded after the current agent invocation | `"temp:scratch"` |
| `user:` | User — persists across sessions for the same user | `"user:preferences"` |
| `app:` | App — persists across all users and sessions | `"app:config"` |

Use `temp:` keys for intermediate values that should not persist between user turns.

### State in ParallelAgent branches
- status: active
- type: guideline
- id: skill.adk_workflow.state.parallel_state
- last_checked: 2026-02-24
<!-- content -->
Parallel branches share the same `InvocationContext` but execute independently. The safe pattern is to assign each branch a unique `output_key`:

```python
# Safe: each branch writes to a different key
branch_a = LlmAgent(..., output_key='result_a')
branch_b = LlmAgent(..., output_key='result_b')
branch_c = LlmAgent(..., output_key='result_c')

fan_out = ParallelAgent(name='fan_out', sub_agents=[branch_a, branch_b, branch_c])

# Fan-in: read all three keys in one subsequent LlmAgent
fan_in = LlmAgent(
    name='synthesiser_agent',
    instruction='Combine: {result_a}, {result_b}, {result_c}',
    output_key='final_result',
)
```

## 5. The exit_loop Pattern
- status: active
- type: guideline
- id: skill.adk_workflow.exit_loop
- last_checked: 2026-02-24
<!-- content -->
The standard way to terminate a `LoopAgent` from within a sub-agent is via a Python tool that sets `tool_context.actions.escalate = True`.

### Implementing exit_loop
- status: active
- type: guideline
- id: skill.adk_workflow.exit_loop.implementation
- last_checked: 2026-02-24
<!-- content -->
```python
# tools/loop_control.py
from google.adk.tools import ToolContext

def exit_loop(tool_context: ToolContext) -> dict:
    """
    Signal the enclosing LoopAgent to stop iterating.
    Call this when the current output meets the required quality standard.
    """
    tool_context.actions.escalate = True
    return {"status": "approved", "message": "Loop terminated — quality approved."}
```

### Wiring exit_loop into an LlmAgent
- status: active
- type: guideline
- id: skill.adk_workflow.exit_loop.wiring
- last_checked: 2026-02-24
<!-- content -->
```python
from .tools.loop_control import exit_loop

evaluator_agent = LlmAgent(
    name='evaluator_agent',
    tools=[exit_loop],          # gives the LLM the ability to stop the loop
    output_key='eval_notes',
    instruction=(
        'Review the current output: {draft}\n\n'
        'If quality is acceptable, call exit_loop to approve it.\n'
        'Otherwise, write a numbered list of specific improvements needed.'
    ),
)
```

### When escalate fires mid-iteration
- status: active
- type: guideline
- id: skill.adk_workflow.exit_loop.timing
- last_checked: 2026-02-24
<!-- content -->
When `escalate = True` is set by a sub-agent, the `LoopAgent` stops after that sub-agent's turn. The remaining sub-agents in the **current iteration** are skipped. The next iteration does not start.

This means: if the evaluator fires `exit_loop` first in an iteration, the improver that follows it will be skipped — the loop terminates cleanly.

## 6. Composition Patterns
- status: active
- type: guideline
- id: skill.adk_workflow.composition
- last_checked: 2026-02-24
<!-- content -->
Workflow agents are designed to be **nested**. A `SequentialAgent`'s sub-agents can include `ParallelAgent` and `LoopAgent` instances, and those can themselves contain `SequentialAgent` steps.

### Pattern A — Linear Pipeline (Sequential only)
- status: active
- type: guideline
- id: skill.adk_workflow.composition.linear
- last_checked: 2026-02-24
<!-- content -->
The simplest pattern: steps run in strict order, each reading the previous step's `output_key`.

```python
SequentialAgent(sub_agents=[step_a, step_b, step_c])
# step_a → step_b (reads {a_output}) → step_c (reads {b_output})
```

Use for: data transformation chains, code generation → review → refactor, multi-step document processing.

### Pattern B — Fan-Out / Fan-In (Parallel inside Sequential)
- status: active
- type: guideline
- id: skill.adk_workflow.composition.fan_out_fan_in
- last_checked: 2026-02-24
<!-- content -->
Independent parallel tasks feed a single synthesis step.

```python
SequentialAgent(sub_agents=[
    ParallelAgent(sub_agents=[branch_a, branch_b, branch_c]),  # fan-out
    synthesiser_agent,                                          # fan-in
])
```

Use for: multi-angle research, parallel validation, concurrent data fetching followed by aggregation.

### Pattern C — Generate then Polish (Sequential with Loop)
- status: active
- type: guideline
- id: skill.adk_workflow.composition.generate_then_polish
- last_checked: 2026-02-24
<!-- content -->
A first-pass generator feeds an iterative refinement loop.

```python
SequentialAgent(sub_agents=[
    generator_agent,                                            # produces first draft
    LoopAgent(sub_agents=[evaluator_agent, improver_agent]),    # iteratively polishes
])
```

Use for: report writing, code generation, essay drafting, content creation.

### Pattern D — Full Pipeline (Parallel + Sequential + Loop)
- status: active
- type: guideline
- id: skill.adk_workflow.composition.full_pipeline
- last_checked: 2026-02-24
<!-- content -->
The complete three-phase pattern used in `workflow_agents/agent.py`:

```python
SequentialAgent(sub_agents=[
    ParallelAgent(sub_agents=[researcher_a, researcher_b, researcher_c]),  # concurrent research
    drafting_agent,                                                         # synthesis
    LoopAgent(sub_agents=[reviewer_agent, editor_agent], max_iterations=3), # quality loop
])
```

Use for: research-to-report pipelines, multi-source document creation, complex content workflows.

### Pattern E — Nested Sequential inside Parallel
- status: active
- type: guideline
- id: skill.adk_workflow.composition.nested_sequential_in_parallel
- last_checked: 2026-02-24
<!-- content -->
Run independent multi-step pipelines concurrently.

```python
ParallelAgent(sub_agents=[
    SequentialAgent(sub_agents=[fetch_a, process_a]),   # pipeline 1
    SequentialAgent(sub_agents=[fetch_b, process_b]),   # pipeline 2
])
```

Use for: processing multiple independent data sources that each require their own multi-step transformation.

### Pattern F — Loop over a Sequential Block
- status: active
- type: guideline
- id: skill.adk_workflow.composition.loop_over_sequential
- last_checked: 2026-02-24
<!-- content -->
Repeat a multi-step process until a condition is met.

```python
LoopAgent(
    sub_agents=[
        SequentialAgent(sub_agents=[fetch_agent, validate_agent, transform_agent]),
        checker_agent,   # calls exit_loop when done
    ],
    max_iterations=10,
)
```

Use for: retry pipelines with multi-step attempts, iterative search-and-process workflows, crawling with pagination.

## 7. Tools within Workflow Pipelines
- status: active
- type: guideline
- id: skill.adk_workflow.tools
- last_checked: 2026-02-24
<!-- content -->
Workflow agents (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) do **not** accept a `tools` parameter — they have no LLM and cannot call tools directly. Tools are always attached to **`LlmAgent` sub-agents** within the pipeline.

```
WorkflowAgent
  └── sub_agents=[LlmAgent(tools=[tool_a, tool_b]), ...]
                  ▲
                  only LlmAgent sub-agents can have tools
```

### Python Tool Functions
- status: active
- type: guideline
- id: skill.adk_workflow.tools.python
- last_checked: 2026-02-24
<!-- content -->
A plain Python function with type annotations is the simplest tool type. Pass it directly in the `tools` list of any `LlmAgent` sub-agent.

```python
from datetime import datetime
import zoneinfo

def get_current_time(timezone: str) -> dict:
    """Returns the current time in an IANA timezone (e.g. 'Europe/Paris')."""
    tz = zoneinfo.ZoneInfo(timezone)
    return {"datetime": datetime.now(tz).isoformat(), "timezone": timezone}

# Attach to any LlmAgent in the pipeline
time_agent = LlmAgent(
    name='time_lookup_agent',
    model='gemini-2.5-flash',
    output_key='current_time',
    tools=[get_current_time],
    instruction='Look up the current time in {city_timezone} and report it.',
)
```

ADK automatically generates a JSON schema from the function's docstring and type annotations. The LLM calls the function by name when it decides to.

### ToolContext — Accessing Pipeline State from a Tool
- status: active
- type: guideline
- id: skill.adk_workflow.tools.tool_context
- last_checked: 2026-02-24
<!-- content -->
When a tool function accepts a `ToolContext` argument, ADK injects it automatically. `ToolContext` gives a tool direct access to the live session state and ADK action flags.

```python
from google.adk.tools import ToolContext

def save_result(label: str, value: str, tool_context: ToolContext) -> dict:
    """Saves a key-value pair directly into session state."""
    tool_context.state[f"saved_{label}"] = value
    return {"status": "saved", "key": f"saved_{label}"}
```

**Key `ToolContext` capabilities available inside tool functions:**

| Attribute / Method | Type | Description |
| :--- | :--- | :--- |
| `tool_context.state` | `dict`-like | Read and write session state directly — same store that `output_key` writes to |
| `tool_context.actions.escalate` | `bool` | Set to `True` to signal the enclosing `LoopAgent` to stop (the `exit_loop` pattern) |
| `tool_context.actions.transfer_to_agent` | `str` | Transfer control to a named agent (advanced multi-agent routing) |
| `tool_context.list_artifacts()` | `list` | List files stored as ADK artifacts in the current session |
| `tool_context.load_artifact(filename)` | `Part` | Read an ADK artifact (e.g. an uploaded file) |
| `tool_context.save_artifact(filename, part)` | `None` | Persist a file or blob as an ADK artifact |

### MCP Tools inside Workflow Pipelines
- status: active
- type: guideline
- id: skill.adk_workflow.tools.mcp
- last_checked: 2026-02-24
<!-- content -->
`McpToolset` can be attached to any `LlmAgent` sub-agent within a workflow pipeline, exactly as it is in a standalone agent. The `LlmAgent` manages its own MCP connection independently of the workflow orchestration.

```python
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
import os

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), "workspace"))

# LlmAgent inside a SequentialAgent that uses MCP filesystem tools
file_writer_agent = LlmAgent(
    name='file_writer_agent',
    model='gemini-2.5-flash',
    output_key='saved_filename',
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx',
                    args=["-y", "@modelcontextprotocol/server-filesystem", WORKSPACE],
                ),
            ),
            tool_filter=['write_file', 'create_directory'],
        )
    ],
    instruction=(
        'Save the following report to a file called report.md in the workspace:\n\n{draft}'
    ),
)

pipeline = SequentialAgent(
    name='write_pipeline_agent',
    sub_agents=[drafting_agent, file_writer_agent],   # draft first, then save
)
```

### Mixing Tool Types
- status: active
- type: guideline
- id: skill.adk_workflow.tools.mixing
- last_checked: 2026-02-24
<!-- content -->
A single `LlmAgent` sub-agent can hold any mix of tool types simultaneously — Python functions, `ToolContext` tools, and `McpToolset` instances are all valid entries in the same `tools` list:

```python
researcher_agent = LlmAgent(
    name='researcher_agent',
    model='gemini-2.5-flash',
    output_key='research_result',
    tools=[
        get_current_time,           # plain Python function
        save_result,                # ToolContext function
        McpToolset(                 # MCP server toolset
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='uvx', args=['mcp-server-fetch']
                )
            ),
            tool_filter=['fetch'],
        ),
    ],
    instruction='Research the topic "{topic}" and save a summary.',
)
```

### Tools vs. Sub-agents — When to Use Each
- status: active
- type: guideline
- id: skill.adk_workflow.tools.vs_sub_agents
- last_checked: 2026-02-24
<!-- content -->
| Capability | Use a **tool** | Use a **sub-agent** |
| :--- | :--- | :--- |
| Calling an external API or system | ✓ | — |
| Reading/writing files or databases | ✓ | — |
| Simple, deterministic computation | ✓ | — |
| A task that requires its own LLM reasoning turn | — | ✓ |
| A step whose output feeds a later step via `output_key` | — | ✓ |
| Controlling loop termination (`escalate`) | ✓ | — |
| Running a parallel or sequential sub-pipeline | — | ✓ |

The rule of thumb: if it needs to *think*, make it a sub-agent; if it needs to *act* (I/O, compute, control flow signals), make it a tool.

## 8. Workflow Pattern Library
- status: active
- type: guideline
- id: skill.adk_workflow.pattern_library
- last_checked: 2026-02-24
<!-- content -->
The following catalogue lists 24 named workflow patterns, organized by primary workflow agent type. Use it as a quick-reference when designing new pipelines.

### SequentialAgent Patterns
- status: active
- type: guideline
- id: skill.adk_workflow.pattern_library.sequential
- last_checked: 2026-02-24
<!-- content -->

| # | Pattern name | Structure | Description |
| :- | :--- | :--- | :--- |
| 1 | **Linear Transform** | `Seq(A → B → C)` | Each step transforms the previous step's output. Classic data pipeline. |
| 2 | **Code Pipeline** | `Seq(writer → reviewer → refactorer)` | LLM writes code, second LLM reviews it, third LLM applies the review notes. |
| 3 | **Translate & Validate** | `Seq(translator → grammar_checker → formatter)` | Multi-step document translation with quality gates. |
| 4 | **Structured Extraction** | `Seq(extractor → validator → normaliser)` | Parse raw input, validate schema, normalise to a target format. |
| 5 | **Multi-step Reasoning** | `Seq(planner → executor → summariser)` | Break a task into a plan, execute each step, then summarise the results. |
| 6 | **ETL Pipeline** | `Seq(ingest → clean → enrich → load)` | Classic extract-transform-load with each phase as a separate LlmAgent. |

### ParallelAgent Patterns
- status: active
- type: guideline
- id: skill.adk_workflow.pattern_library.parallel
- last_checked: 2026-02-24
<!-- content -->

| # | Pattern name | Structure | Description |
| :- | :--- | :--- | :--- |
| 7 | **Multi-angle Research** | `Par(overview, examples, limitations) → Seq synthesiser` | Three researchers write independent briefs; one agent merges them. |
| 8 | **Multi-language Translation** | `Par(translate_es, translate_fr, translate_de)` | Translate the same content into several languages simultaneously. |
| 9 | **Ensemble Evaluation** | `Par(evaluator_1, evaluator_2, evaluator_3) → Seq voter` | Multiple independent judges score an output; a downstream agent picks the winner. |
| 10 | **Parallel Validation** | `Par(schema_check, security_check, style_check)` | Run independent checks on the same input concurrently; a final agent aggregates failures. |
| 11 | **Concurrent Summarisation** | `Par(summarise_doc_a, summarise_doc_b, summarise_doc_c)` | Summarise multiple documents simultaneously before combining them. |
| 12 | **A/B Content Generation** | `Par(variant_a_agent, variant_b_agent) → Seq selector` | Generate two versions of content in parallel; a selector agent picks the better one. |

### LoopAgent Patterns
- status: active
- type: guideline
- id: skill.adk_workflow.pattern_library.loop
- last_checked: 2026-02-24
<!-- content -->

| # | Pattern name | Structure | Description |
| :- | :--- | :--- | :--- |
| 13 | **Critique-Refine** | `Loop(critic → refiner)` | Critic evaluates output and calls `exit_loop` if approved; refiner improves it otherwise. |
| 14 | **Test-Fix Loop** | `Loop(test_runner → code_fixer)` | Run tests, fix failures, repeat until all tests pass or iteration cap is hit. |
| 15 | **Search-Validate Loop** | `Loop(searcher → validator)` | Search for information, validate it meets requirements, exit when found. |
| 16 | **Negotiation Loop** | `Loop(proposal_agent → counter_agent)` | Simulate iterative negotiation between two agents until agreement is reached. |
| 17 | **Data Quality Loop** | `Loop(quality_checker → data_cleaner)` | Check data quality, clean issues, repeat until quality threshold is met. |
| 18 | **Self-Consistency Check** | `Loop(generator → verifier)` | Generate an answer, verify it is self-consistent, re-generate if not. |

### Composite Patterns
- status: active
- type: guideline
- id: skill.adk_workflow.pattern_library.composite
- last_checked: 2026-02-24
<!-- content -->

| # | Pattern name | Structure | Description |
| :- | :--- | :--- | :--- |
| 19 | **Research Pipeline** | `Seq(Par(researchers...) → synthesiser → Loop(reviewer → editor))` | Gather in parallel, draft, then iteratively refine. The `workflow_agents/` project example. |
| 20 | **Code Generation Pipeline** | `Seq(Par(spec_writer, test_writer) → coder → Loop(tester → fixer))` | Specs and tests are written in parallel; the coder implements; a test-fix loop validates. |
| 21 | **Document Audit Pipeline** | `Seq(Par(section_extractors...) → aggregator → Loop(auditor → corrector))` | Extract sections in parallel, merge, then iteratively audit and fix. |
| 22 | **Multi-Source RAG** | `Seq(Par(fetcher_a, fetcher_b, fetcher_c) → reranker → answer_agent)` | Fetch from multiple sources simultaneously, rerank by relevance, then answer. |
| 23 | **Parallel Pipelines** | `Par(Seq(A1 → A2), Seq(B1 → B2))` | Two fully independent multi-step pipelines running concurrently. |
| 24 | **Iterative Multi-Branch** | `Loop(Par(branch_a, branch_b) → merger)` | Each iteration runs parallel branches and merges them; loop exits when the merged result is satisfactory. |

## 9. Design Principles
- status: active
- type: guideline
- id: skill.adk_workflow.design_principles
- last_checked: 2026-02-24
<!-- content -->

### Naming Conventions
- status: active
- type: guideline
- id: skill.adk_workflow.design_principles.naming
- last_checked: 2026-02-24
<!-- content -->
| Element | Convention | Example |
| :--- | :--- | :--- |
| All agent variables | `<role>_agent` | `drafting_agent`, `reviewer_agent` |
| Workflow orchestrators | `<pipeline_name>_agent` | `report_pipeline_agent`, `research_phase_agent` |
| `output_key` values | `snake_case` noun describing the content | `"draft"`, `"review_notes"`, `"overview"` |
| State placeholders in instructions | `{output_key}` | `{draft}`, `{review_notes}` |
| Loop exit tool | `exit_loop` | Always this exact name — it is self-documenting |
| Temp state keys | `temp:<name>` | `temp:scratch_notes` |

### output_key Best Practices
- status: active
- type: guideline
- id: skill.adk_workflow.design_principles.output_key
- last_checked: 2026-02-24
<!-- content -->
- **Every `LlmAgent` that produces data for downstream steps must have an `output_key`.**
- Use distinct keys across parallel branches to avoid overwrite races.
- In a `LoopAgent`, the improver agent should write back to the **same key** as the initial value (e.g. always `"draft"`) so each iteration's evaluator sees the latest version.
- Use `temp:` prefix for scratch keys that only live within one pipeline run.

### LoopAgent Safety Rules
- status: active
- type: guideline
- id: skill.adk_workflow.design_principles.loop_safety
- last_checked: 2026-02-24
<!-- content -->
- **Always set `max_iterations`** — an LLM that fails to call `exit_loop` will otherwise loop forever.
- The `exit_loop` tool is the preferred termination path; `max_iterations` is the safety net.
- Keep `max_iterations` low (3–5) for quality-loop patterns. Increase only for search/retry patterns where more attempts are genuinely useful.
- The evaluator sub-agent should be the **first** sub-agent in the `sub_agents` list so it can exit early without running the improver on an already-good result.

### Instruction Design for Workflow Agents
- status: active
- type: guideline
- id: skill.adk_workflow.design_principles.instructions
- last_checked: 2026-02-24
<!-- content -->
- **Be explicit about scope**: each sub-agent's instruction should describe only its own task, not the full pipeline.
- **Reference state with `{key}` placeholders**: ADK resolves these at runtime from session state.
- **Give clear exit criteria to evaluators**: vague instructions produce inconsistent `exit_loop` calls. Specify a checklist the LLM must verify before calling the tool.
- **Keep parallel branch instructions independent**: branches must not assume knowledge of other branches' outputs since they run concurrently.

## 10. Troubleshooting
- status: active
- type: guideline
- id: skill.adk_workflow.troubleshooting
- last_checked: 2026-02-24
<!-- content -->

| Symptom | Likely cause | Fix |
| :--- | :--- | :--- |
| `{key}` placeholder is empty or literal text | `output_key` not set on the upstream agent, or agents are in different `InvocationContext` scopes | Ensure the upstream `LlmAgent` has `output_key='key'` and both agents are sub-agents of the same workflow orchestrator |
| `ParallelAgent` branch overwrites another branch's value | Two branches share the same `output_key` | Give each parallel branch a unique `output_key` |
| `LoopAgent` runs `max_iterations` every time | Evaluator never calls `exit_loop` | Check the evaluator's instruction — make the approval criteria explicit; add a `print`/log inside `exit_loop` to confirm it is being invoked |
| `LoopAgent` exits on the first iteration | Evaluator calls `exit_loop` even for poor output | Tighten the evaluator's instruction; add a minimum quality checklist |
| Sub-agents run in the wrong order inside `SequentialAgent` | Agents listed in wrong order in `sub_agents` | The list is positional — reorder it. There is no dependency graph; order is always list order |
| `ParallelAgent` is slower than expected | Sub-agents are not truly independent (e.g. they share a rate-limited LLM API key) | Rate limits apply per key, not per agent. Use exponential-backoff retries or reduce parallelism |
| State from one session leaks into another | Using non-`temp:` keys for ephemeral intermediate values | Prefix intermediate keys with `temp:` so ADK discards them after the turn |
| `LoopAgent` does not call the improver after exit_loop fires | Expected — when escalate is set, remaining sub-agents in the current iteration are skipped | This is correct behaviour. If you need the improver to always run, put the evaluator last in `sub_agents` |
