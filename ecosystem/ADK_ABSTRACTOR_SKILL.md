# ADK Abstractor — Visualizing Existing Systems in the ADK Designer
- status: active
- type: how-to
- id: adk.abstractor.skill
- description: Step-by-step process for abstracting any working system (chatbot, pipeline, script) into an ADK Designer JSON preset that loads directly onto the visual canvas.
- label: [agent, skill, frontend]
- injection: procedural
- volatility: evolving
- last_checked: 2026-04-06

<!-- content -->

The **ADK Abstractor** is the skill of reading a working codebase and producing an `ecosystem/presets/<name>.json` file that faithfully represents its architecture as an ADK Designer canvas. The output is both a living diagram and a migration blueprint — it shows the current system and implicitly answers "how would this look if re-built in ADK?"

## When to Use This Skill
- You have an existing chatbot, data pipeline, or script collection and want to visualize its architecture.
- You are planning a migration to Google ADK and need a canvas skeleton as a starting point.
- You want to communicate a system's design using the standardized ADK node vocabulary.

## Node Data Field Reference

Every node has a `data` object whose fields must exactly match the TypeScript interface. Wrong types (e.g. array instead of string) will crash the renderer on load.

| Node kind | Required fields | Field types |
| :--- | :--- | :--- |
| `Human` | `name`, `description`, `prompt` | all strings |
| `LlmAgent` | `name`, `model`, `description`, `instruction`, `output_key` | all strings |
| `SequentialAgent` | `name`, `description` | all strings |
| `ParallelAgent` | `name`, `description` | all strings |
| `LoopAgent` | `name`, `description`, `max_iterations` | strings + number |
| `Tool` | `name`, `description`, `code` | all strings |
| `McpToolset` | `name`, `command`, `args`, `tool_filter` | all strings — **no `description` field** |
| `Script` | `name`, `description`, `command`, `code` | all strings |
| `Evaluator` | `name`, `model`, `success_condition` | all strings |
| `Database` | `name`, `description`, `db_type`, `connection` | all strings |
| `ArtifactStore` | `name`, `description`, `service_type`, `bucket` | all strings |
| `Context` | `name`, `description`, `content` | all strings |
| `SessionState` | `name`, `description`, `keys`, `schema` | all strings |
| `Memory` | `name`, `description`, `service_type`, `collection` | all strings |
| `A2UIResponse` | `name`, `components`, `renderer` | all strings |

**Common mistakes that break preset loading:**
- `McpToolset.args` — must be a **string** (space-separated args), not an array
- `McpToolset.tool_filter` — must be a **string** (comma-separated names), not an array
- `McpToolset` has **no `description` field** — omit it
- `A2UIResponse.components` — must be a **comma-separated string** (e.g. `"text, card, button"`), not an array
- `SessionState` requires both `keys` (comma-separated key names) and `schema` (description of value shapes) — omit neither
- `Human` requires a `prompt` field — do not omit it
- `ArtifactStore` uses `service_type` (`"InMemory"` or `"GCS"`) and `bucket`, not `storage_type` / `bucket_name`
- `Memory` uses `service_type` (`"InMemory"` or `"VertexAiRag"`) and `collection`, not `memory_type`

## Abstraction Process

### Step 1 — Identify the Entry Point
Find where the system receives input from a human (chat UI, CLI, API endpoint, webhook).

→ Map to: **Human node** (`kind: "Human"`). There is exactly one per pipeline.

| Code pattern | Signals |
| :--- | :--- |
| `streamlit run app.py` chat input | Human node |
| FastAPI POST `/chat` | Human node |
| `input()` / argparse CLI | Human node |
| Cron job / scheduled trigger | No Human node — use a bare LlmAgent or SequentialAgent as root |

### Step 2 — Identify the Orchestrator
Find the component that receives the human's request, decides what to do, and coordinates responses.

→ Map to: **LlmAgent node** if it's LLM-driven, or a **workflow agent** (Sequential / Parallel / Loop) if purely deterministic.

| Code pattern | Signals |
| :--- | :--- |
| `model.generate_content(messages, tools=...)` | LlmAgent |
| Gemini / OpenAI / Anthropic API call with tool definitions | LlmAgent |
| Fixed script with no LLM decision-making | SequentialAgent |
| Multiple independent processes run concurrently | ParallelAgent |
| Retry / refinement loop | LoopAgent + Evaluator |

Set the `model` field to the actual model used (e.g., `gemini-2.5-flash`). Copy the system prompt into `instruction`.

### Step 3 — Identify and Aggregate Tools
Find every discrete callable the orchestrator can invoke: MCP tool functions, API wrappers, database queries, utility functions.

→ Map **groups of related tools** to a single **Tool node** (`kind: "Tool"`), or to a **McpToolset node** for external MCP servers.

**Aggregation rule:** Group tools by *functional responsibility*, not by individual function. One Tool node should represent a coherent capability. Too many fine-grained Tool nodes clutter the canvas and obscure the architecture.

| Aggregation heuristic | Example |
| :--- | :--- |
| Tools that query the **same dataset** → one node | `search_people`, `search_research`, `get_events` → `mcp_tools` |
| Tools that perform the **same kind of action** → one node | `scrape_events`, `scrape_people`, `scrape_research` → `update_dataset` |
| Tools from the **same MCP server** → one McpToolset node | All tools from `mcp-server-filesystem` → one McpToolset |

Enumerate the individual function names in the `code` field of a Tool node as comments — this preserves detail without cluttering the canvas:
```
# search_people(query)   — people.json
# search_research(query) — research.json
# get_events(query)      — raw_events.json
```

For a McpToolset node, list exposed tools in `tool_filter` as a comma-separated string:
```json
{
  "kind": "McpToolset",
  "name": "rps_memory_server",
  "command": "python3",
  "args": "mcp_servers/rps_memory_server.py",
  "tool_filter": "save_agent_choice, record_round, get_history, get_stats"
}
```

| Code pattern | Signals |
| :--- | :--- |
| `@tool` decorated functions on same data | Aggregate into one Tool node |
| Functions registered in an MCP tool registry | Tool node per logical group |
| `McpToolset(command=..., args=...)` | McpToolset node |

### Step 4 — Identify Data Stores
Find every persistent store the system reads from or writes to: JSON files, SQL databases, vector stores, graph stores, Google Sheets. Also find any file/blob artifact services (produced outputs, session files, documents).

Information Set nodes are split into two sub-groups: **Data Stores** (tool-facing) and **Memory** (LLM-facing). Step 4 covers Data Stores; Step 5 covers Memory.

#### 4a — External Data Stores → Database node
→ Map each to: **Database node** (`kind: "Database"`).

Set `db_type` to the technology (e.g., `"JSON Files"`, `"PostgreSQL"`, `"ChromaDB"`, `"Graph (JSON + MD)"`). Set `connection` to the path or connection string.

| Code pattern | Signals |
| :--- | :--- |
| `sqlite3.connect(...)` / SQLAlchemy engine | Database — SQL |
| ChromaDB / Pinecone / Weaviate client | Database — Vector DB |
| `open("data.json")` / `json.load(...)` | Database — JSON Files |
| Google Sheets / BigQuery client | Database — Sheets / BigQuery |

#### 4b — File / Blob Artifacts → Artifact Store node
→ Map to: **Artifact Store node** (`kind: "ArtifactStore"`) when the system produces or consumes files/blobs through an artifact service.

Set `service_type` to `"InMemory"` or `"GCS"`. Set `bucket` if GCS.

| Code pattern | Signals |
| :--- | :--- |
| `InMemoryArtifactService()` | ArtifactStore — `service_type: "InMemory"` |
| `GcsArtifactService(bucket_name=...)` | ArtifactStore — `service_type: "GCS"`, `bucket: "..."` |
| Session-scoped file uploads / downloads | ArtifactStore |

### Step 5 — Identify Injected Context and Memory
Find static or dynamic content injected into prompts, shared key-value state within a pipeline run, and cross-session semantic memory.

#### 5a — Static context → Context node
→ Map each to: **Context node** (`kind: "Context"`).

Paste a summary of the content into the `content` field.

| Code pattern | Signals |
| :--- | :--- |
| Personality `.md` file loaded into system prompt | Context |
| Hardcoded `SYSTEM_PROMPT` or `PERSONA` string | Context |
| Reference document prepended to every request | Context |

#### 5b — Shared in-run state → Session State node
→ Map to: **Session State node** (`kind: "SessionState"`) when agents share a key-value store within a single pipeline run.

Set `keys` to a comma-separated list of key names (e.g. `"session_id, draft, overview"`). Set `schema` to a description of each key's value shape.

| Code pattern | Signals |
| :--- | :--- |
| `agent.output_key = "result"` | SessionState — maps output between agents |
| `ctx.session.state["key"]` read/write | SessionState |
| Multiple agents referencing the same state dict | SessionState |

#### 5c — Cross-session semantic retrieval → Memory node
→ Map to: **Memory node** (`kind: "Memory"`) when the system stores and retrieves information across sessions.

Set `service_type` to `"InMemory"` or `"VertexAiRag"`. Set `collection` to the corpus name or resource ID.

| Code pattern | Signals |
| :--- | :--- |
| `InMemoryMemoryService()` | Memory — `service_type: "InMemory"` |
| `VertexAiRagMemoryService(...)` | Memory — `service_type: "VertexAiRag"` |
| Semantic search over past conversations | Memory |

### Step 6 — Identify Output Contracts
Find any agent that returns a structured JSON response consumed by a frontend renderer (A2UI components, rich UI widgets).

→ Map to: **A2UIResponse node** (`kind: "A2UIResponse"`) connected from the LlmAgent via a **response edge** (pink dashed).

Set `components` to a **comma-separated string** of A2UI component types the agent may emit (e.g., `"text, card, button, list"`). Set `renderer` to the frontend renderer name (e.g., `"React / A2UIRenderer"`). The code generator will automatically append the A2UI instruction block to the connected agent's `instruction`.

**No return edge** — the pink response edge is one-directional (output contract only).

| Code pattern | Signals |
| :--- | :--- |
| Agent instruction mentions JSON component types | A2UIResponse |
| Frontend has an `A2UIRenderer` / component registry | A2UIResponse |
| Agent returns `{"component": "card", ...}` payloads | A2UIResponse |

### Step 7 — Identify Secondary Pipelines
Many systems have a background pipeline (e.g., a scraper that refreshes data, a batch processor). These are separate from the query pipeline and do not start with a Human node.

→ Map to a second **LlmAgent** or **SequentialAgent** as the root of the secondary flow.

Connect its output tools to the same Database nodes used by the main query pipeline — shared databases link the two flows visually.

### Step 8 — Identify Loops and Evaluators
If the system retries until a condition is met (e.g., quality check, validation loop), wrap the iterating section in a **LoopAgent** and add an **Evaluator** at the end.

| Code pattern | Signals |
| :--- | :--- |
| `while not satisfied: ...` | LoopAgent |
| `for _ in range(max_retries): ...` | LoopAgent |
| Quality check / rubric evaluation at end of loop | Evaluator node |

### Step 9 — Map Edges
Every active flow connection produces **two edges**: a forward *call* edge and a reverse *response* edge. The designer creates both automatically when you draw a connection on the canvas. In preset JSON, add them explicitly.

**Forward (call) edges:**

| Connection | Edge style | `isObservation` |
| :--- | :--- | :--- |
| Human → LlmAgent | orange (`#f97316`), `type: "flow"` | `false` |
| LlmAgent → Tool / McpToolset | teal dashed (`#14b8a6`), `type: "flow"` | `false` |
| Workflow agent → sub-agent | indigo (`#6366f1`), `type: "flow"` | `false` |
| LlmAgent → A2UIResponse | pink dashed (`#ec4899`), no `type` field | `false` |
| Any node → Database / Context / SessionState / Memory / ArtifactStore | gray (`#94a3b8`), no `type` field | `true` |

**Return (response) edges** — added for every non-info forward edge **except** LlmAgent → A2UIResponse (output contract is one-directional). They are **separate directed edges** (not bidirectional arrows) that depart from a different handle on the source node so they take a visually distinct path.

**Handle convention:**
- Forward edges use `sourceHandle: "right"` → `targetHandle: "left"` — straight horizontal pass-through.
- Return edges use `sourceHandle: "bottom"` → `targetHandle: "bottom"` — curves downward as a U-shape below the nodes, clearly separated from the forward lane.

| Direction | Style |
| :--- | :--- |
| Tool → LlmAgent | Same color as forward, `type: "flow"`, `strokeDasharray: "4,3"`, `opacity: 0.55`, `data.isReturn: true` |
| LlmAgent → Human | Same color as forward, `type: "flow"`, `strokeDasharray: "4,3"`, `opacity: 0.55`, `data.isReturn: true` |
| sub-agent → Workflow | Same color as forward, `type: "flow"`, `strokeDasharray: "4,3"`, `opacity: 0.55`, `data.isReturn: true` |

The `isReturn: true` flag tells the `FlowEdge` renderer to use smaller, dimmer particles (r=2, opacity=0.5, slower) so the response flow is visually subordinate to the call flow (r=3.5, opacity=0.85).

**No return edges** for info edges (Database / Context / SessionState / Memory / ArtifactStore) and A2UIResponse — passive data access and output contracts are not request-response cycles.

Example forward + return edge pair:
```json
{
  "id": "e-leopold-mcp_tools",
  "source": "leopold",
  "target": "mcp_tools",
  "sourceHandle": "right",
  "targetHandle": "left",
  "type": "flow",
  "data": { "kind": "tool", "isObservation": false },
  "style": { "stroke": "#14b8a6", "strokeDasharray": "6,4" },
  "markerEnd": { "type": "arrowclosed", "color": "#14b8a6" }
},
{
  "id": "e-ret-mcp_tools-leopold",
  "source": "mcp_tools",
  "target": "leopold",
  "sourceHandle": "bottom",
  "targetHandle": "bottom",
  "type": "flow",
  "data": { "kind": "response", "isObservation": false, "isReturn": true },
  "style": { "stroke": "#14b8a6", "strokeDasharray": "4,3", "opacity": 0.55 },
  "markerEnd": { "type": "arrowclosed", "color": "#14b8a6" }
}
```

### Step 10 — Write the Preset JSON
Create `ecosystem/presets/<system_name>.json`. The `_meta` block is mandatory — it drives the Python export header and the download filename.

```json
{
  "_meta": {
    "name": "System Name",
    "description": "One-sentence description of what this preset represents.",
    "source_repo": "repo_name",
    "created": "YYYY-MM-DD"
  },
  "nodes": [ ...Node objects... ],
  "edges": [ ...Edge objects... ]
}
```

Each **node object** — `position` is required; `width`/`height` are optional initial sizes:
```json
{
  "id": "short_snake_case_id",
  "type": "LlmAgent",
  "position": { "x": 300, "y": 250 },
  "width": 200,
  "height": 100,
  "data": {
    "kind": "LlmAgent",
    "name": "agent_name",
    "model": "gemini-2.5-flash",
    "description": "...",
    "instruction": "...",
    "output_key": "response"
  }
}
```

When a preset is saved back via **Export Preset**, React Flow adds runtime fields to each node (`measured`, `selected`, `dragging`, `resizing`). These are harmless — React Flow uses them on reload and they do not affect Python export. Do not manually add them when hand-authoring a preset.

Each **active flow edge** (forward call):
```json
{
  "id": "e-source_id-target_id",
  "source": "source_id",
  "target": "target_id",
  "sourceHandle": "right",
  "targetHandle": "left",
  "type": "flow",
  "data": { "kind": "tool", "isObservation": false, "name": "", "description": "" },
  "style": { "stroke": "#14b8a6", "strokeDasharray": "6,4" },
  "markerEnd": { "type": "arrowclosed", "color": "#14b8a6" }
}
```

`name` renders as a colored pill label at the edge midpoint on the canvas. `description` is panel-only annotation.

**Handle conventions are flexible.** The designer has no fixed rule for which handle a forward vs. return edge must use — the only goal is that the two arrows between a pair of nodes take visually distinct paths. A common approach is to use mirrored handles (e.g., `left`→`left` for the forward call and `right`→`right` for the return), but any combination that avoids visual overlap works. Use the edge property panel to adjust after loading.

For information edges (to Database / Context / SessionState / Memory / ArtifactStore), omit `type: "flow"`, set `isObservation: true`, and omit `sourceHandle`/`targetHandle`.

For the A2UIResponse edge, omit `type: "flow"`, set `isObservation: false`, use pink (`#ec4899`), and omit the return edge.

### Step 11 — Load, Arrange, and Save Back
When hand-authoring a preset, positions are approximate — fine-tune layout in the designer:

1. Run the designer: `cd ecosystem && npm run dev`
2. Click **Load File** → select `ecosystem/presets/<name>.json`.
3. Arrange nodes by dragging. Resize by selecting and dragging corners.
4. Click any edge to open it in the property panel. Change **From handle** / **To handle** to separate forward and return paths visually.
5. Add **Name** labels to edges where the relationship needs annotation.
6. Click **Export Preset** — downloads `<name>.json` with all current positions, sizes, handle assignments, and `_meta` intact. React Flow runtime fields (`measured`, `selected`, etc.) are included automatically.
7. Replace `ecosystem/presets/<name>.json` with the downloaded file.

**The round-trip: Load File → arrange → Export Preset → overwrite the file.**

Do not use **Save** (localStorage) for canonical layouts — it does not carry `_meta` and is not portable between machines.

### Step 12 — Export Python
Click **Export Python** to download `agent.py`. When a preset is loaded, the file begins with a module docstring generated from `_meta`:

```python
"""
MCMP Chatbot
============
Visual abstraction of the MCMP Chatbot...

Source: mcmp_chatbot
Generated: 2026-03-28 by ADK Agent Designer
"""
```

The generator then emits imports, tool functions, MCP toolsets, and agent definitions in topological order — only the node types actually present in the canvas are imported.

## Layout Conventions
Consistent layouts make presets readable at a glance:

| Zone | X range | Y range | Contents |
| :--- | :--- | :--- | :--- |
| Entry | 0–150 | any | Human node, pipeline roots |
| Orchestrators | 250–450 | any | LlmAgent, workflow agents |
| Tools | 550–750 | spread vertically | Tool, McpToolset |
| Data | 900–1100 | aligned with tools | Database, ArtifactStore, Context, SessionState, Memory |
| Output contracts | 250–450 | below orchestrator | A2UIResponse |
| Secondary pipelines | any | +600–700 from primary | Separate flows (scrapers, etc.) |

Space nodes at least 120px apart vertically to avoid overlap. Tools that feed the same database should cluster at similar Y values.

## Quick Reference: Code → Node Type

| Source code element | ADK Designer node |
| :--- | :--- |
| Chat UI / user input | Human |
| LLM API call + tool dispatch | LlmAgent |
| Fixed sequential script | SequentialAgent |
| Parallel async workers | ParallelAgent |
| Retry / refinement loop | LoopAgent |
| Quality / rubric check | Evaluator |
| `@tool` function / MCP tool | Tool |
| `McpToolset(command=...)` | McpToolset |
| JSON / SQL / vector DB | Database |
| `InMemoryArtifactService` / `GcsArtifactService` | ArtifactStore |
| Personality file / system prompt fragment | Context |
| `session.state` / `output_key` shared across agents | SessionState |
| `InMemoryMemoryService` / `VertexAiRagMemoryService` | Memory |
| Agent returns A2UI JSON for frontend renderer | A2UIResponse |

## Reference Presets
`ecosystem/presets/mcmp_chatbot.json` — abstracts the `mcmp_chatbot` repo:
- **Query pipeline**: Human ↔ Leopold (LlmAgent) ↔ `mcp_tools` (Tool, aggregates search_people / search_research / get_events / search_graph) → 2 databases
- **Scraper**: `update_dataset` (Script node, aggregates all scraper functions) → same databases — no LLM orchestrator
- Demonstrates tool aggregation by functional group, return edges as separate directed arrows, and orphaned Script nodes for script-driven pipelines.

`ecosystem/presets/chatbot_template.json` — abstracts the `chatbot_template` repo:
- **Pipeline**: Human ↔ Chatty (LlmAgent) ↔ `rps_memory_server` (McpToolset, stdio subprocess)
- **Output contract**: Chatty → A2UIResponse (text, sealed_box, rps_selector)
- **Info nodes**: Context (Chatty personality), SessionState (InMemorySessionService)
- Demonstrates McpToolset with `tool_filter`, A2UIResponse output contract, and SessionState for session ID threading.
