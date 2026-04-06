# ADK Agent Designer — Visual Architecture Tool
- status: active
- type: how-to
- id: ecosystem.designer.skill
- description: Visual ADK multi-agent pipeline designer built with React Flow: drag-and-drop node canvas, edge types, property panel, and Python agent.py export.
- last_checked: 2026-04-06
- label: [skill, frontend]
<!-- content -->
The `ecosystem/` project is a **visual multi-agent architecture designer** built with React + React Flow. It lets you design ADK multi-agent pipelines by dragging and connecting nodes on a canvas, then exporting a working `agent.py` file.

Think of it as a local, ADK-specific version of [n8n](https://n8n.io/).

## Running the Designer
```bash
cd ecosystem
npm install        # first time only
npm run dev        # opens http://localhost:5173
```

For a production build:
```bash
npm run build      # outputs to ecosystem/dist/
npm run preview    # serves the build locally
```

## Information Flow Model
Every pipeline on the canvas is a directed graph of **information flow** — data moves from node to node, being transformed at each step. Edges represent the path information travels, not just which agent controls which.

### Single-turn flow (default)
The canonical shape is linear:

```
👤 Human → [agents / tools] → Output
```

The **Human node is the entry point**: it represents the user's request entering the system. Information flows forward through LLM agents, tools, and workflow orchestrators until a final output is produced. The Human node appears **once** per pipeline.

### Looping pipeline
When the task requires iteration — e.g., "keep refining until the output is good enough" — the pipeline is wrapped in a `LoopAgent`:

```
👤 Human → LoopAgent ┐
                     ├─ [processing agents]
                     └─ ✅ Evaluator  ──(exit_loop if satisfied)──► Output
```

The `LoopAgent` re-runs its sub-agents on each iteration. The **Evaluator node** sits at the end of the loop and checks the current output against a success condition. If satisfied, it calls `exit_loop` and the pipeline terminates. If not, the loop continues up to `max_iterations`.

### Stop conditions
Stop conditions are expressed as properties of the **Evaluator node**:

| Field | Meaning |
| :--- | :--- |
| `success_condition` | Natural-language rubric the LLM evaluator checks against (e.g., *"The answer is factually correct and under 200 words"*) |
| `model` | Which LLM judges the output |

`max_iterations` on the parent `LoopAgent` acts as the hard upper bound regardless of the success condition.

### Flow visualization
Active flow edges render **animated particles** (3 glowing dots) traveling in the direction of the arrow, making the information path visible at a glance.

- **Particle speed** is controlled by `data.speed` on each edge (seconds per traversal, default 2.5). This field is reserved for future latency/speed analysis.
- **Stuck nodes** — any non-Human, non-information node with no outgoing edges — are highlighted with a pulsing amber ring. This flags dead-ends in the pipeline where flow enters but cannot continue.
- **Information Set edges** (Database, Context) carry data/reference rather than active flow. They render as plain edges with no particles, visually distinguishing passive data from active processing.

### Edge semantics
Edges always carry information in the direction of the arrow. Color indicates the relationship:

| Color | Style | Meaning |
| :--- | :--- | :--- |
| Indigo | Solid, animated | Workflow agent → sub-agent (orchestration + data) |
| Orange | Solid | LLM agent → delegated agent |
| Teal | Dashed | Any agent → tool (function call) |
| Pink | Dashed | LLM agent → A2UI Response (output contract) |
| Gray | Plain, no particles | Any node → Information Set (Database or Context) |

## Node Types
### Active flow nodes
These nodes participate in information flow and connect with animated particle edges.

| Node | Palette group | Color | ADK Class | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| 👤 Human / User | (standalone) | Yellow | — | Entry point: the user's request entering the pipeline. Appears once. |
| 🤖 LLM Agent | (standalone) | Blue | `LlmAgent` | Intelligent agent driven by an LLM |
| ➡️ Sequential | Workflow Agents | Green | `SequentialAgent` | Runs sub-agents one after another |
| ⚡ Parallel | Workflow Agents | Purple | `ParallelAgent` | Runs sub-agents concurrently |
| 🔄 Loop | Workflow Agents | Orange | `LoopAgent` | Iterates sub-agents until exit signal or max iterations |
| ✅ Evaluator | Workflow Agents | Emerald | `LlmAgent` + `exit_loop` | Checks output against a success condition; exits loop when satisfied. Always place last inside a Loop. |
| 🔧 Tool | Tools | Gray | Python function | Custom callable tool for an LlmAgent |
| 🔌 MCP Toolset | Tools | Teal | `McpToolset` | Connects an external MCP server to an LlmAgent |

### Output contract nodes
These nodes sit at the **output boundary** of the pipeline and define the response format expected by the frontend. They do not generate Python agent code themselves; instead they modify the instruction of the connected LLM agent.

| Node | Palette group | Color | Purpose |
| :--- | :--- | :--- | :--- |
| 🎨 A2UI Response | Output Contracts | Pink | Declares that a connected LLM Agent returns structured A2UI JSON. Configures which component types are enabled and which renderer will consume them. |

Connect an `A2UIResponse` node from an `LlmAgent` using a **response edge** (pink dashed). The code generator will automatically append the correct A2UI instruction block to that agent's `instruction`, listing only the component types enabled on the node.

### Information Set nodes
These nodes represent passive data sources. Their edges carry no flow particles and they do not trigger stuck-node warnings. They are of a fundamentally different nature from active flow nodes.

| Node | Palette group | Color | Purpose |
| :--- | :--- | :--- | :--- |
| 🗄️ Database | Information Sets | Violet | Persistent data store (SQL, NoSQL, vector DB, etc.) connected to the pipeline |
| 📋 Context | Information Sets | Cyan | Static or dynamic knowledge injected into the pipeline (instructions, reference data, documents) |

## How to Use
### Palette groups
The left sidebar organises nodes into collapsible groups. Click a group header to expand it:

| Group | Contents |
| :--- | :--- |
| (standalone) | LLM Agent, Human / User |
| 🔀 Workflow Agents | Sequential, Parallel, Loop, Evaluator |
| 🧰 Tools | Tool, MCP Toolset |
| 🎨 Output Contracts | A2UI Response |
| 🗂️ Information Sets | Database, Context |

### Building a pipeline
1. **Drag** a node from the left palette onto the canvas.
2. **Connect** nodes by dragging from any handle to another node's handle.
3. **Click** any node to open its properties in the right panel.
4. **Edit** fields: name, model, instruction, output_key, max_iterations, success_condition, DB type, content, etc.
5. All nodes are **resizable**: select a node and drag the corner/edge handles.

### Edge types
- **Sub-agent edge** (indigo, animated + particles): workflow agent → child agents.
- **Delegate edge** (orange, particles): LLM agent → another agent.
- **Tool edge** (teal dashed, particles): any agent → Tool or MCP Toolset.
- **Response edge** (pink dashed): LLM agent → A2UI Response (output contract).
- **Information edge** (gray, no particles): any agent → Database or Context.

Every active flow connection also produces a **return edge** — a separate dashed arrow running in the opposite direction via the `bottom` handle on both nodes, representing the response or result flowing back. Both directions carry animated particles at the same speed and brightness.

### Editing edges
Click any edge to open it in the right property panel. You can edit:
- **Name** — short label rendered as a pill at the edge midpoint on the canvas.
- **Description** — longer annotation stored on the edge, visible only in the panel.
- **From handle** / **To handle** — which side of the node the edge departs from / arrives at (`top`, `right`, `bottom`, `left`). Change these to untangle messy crossings. The handle picker shows a mini node diagram with four buttons.

### Stuck node indicator
Any non-Human, non-information node with no outgoing edges is flagged with a **pulsing amber ring**. This means the pipeline has a dead-end at that node — flow enters but cannot continue. Connect an outgoing edge to clear the warning.

### Saving & loading (browser)
- **Save** stores the current canvas as JSON in `localStorage`.
- **Load** restores the last saved design from `localStorage`.

### Preset files
Preset files are named JSON files in `ecosystem/presets/`. They carry a `_meta` block plus the full `nodes` and `edges` arrays — including every node's pixel position, size, and all edge handle assignments.

```json
{
  "_meta": {
    "name": "My Pipeline",
    "description": "One-sentence summary.",
    "source_repo": "my_repo",
    "created": "2026-03-28"
  },
  "nodes": [ ... ],
  "edges": [ ... ]
}
```

**Loading a preset:** Click **Load File** → select the `.json` file. The canvas is replaced with the saved layout.

**Saving a layout back to a preset:** After loading a preset and arranging nodes and edges to your liking, click **Export Preset**. The browser downloads a `.json` named after `_meta.name`, containing the current canvas state (positions, sizes, handle assignments, edge labels) with the original `_meta` intact. Replace the file in `ecosystem/presets/` to persist the layout.

The round-trip is: **Load File** → edit on canvas → **Export Preset** → overwrite the file.

### Exporting Python
Click **Export Python** in the toolbar — the browser downloads an `agent.py` file. When a preset with `_meta` is loaded, the file header includes the preset name, description, and source repo as a module docstring. The generator:
1. Emits a module docstring from `_meta` (name, description, source repo, date).
2. Topologically sorts nodes (leaves first).
3. Emits tool function defs and MCP toolset factories.
4. Emits agent instantiations in dependency order.
5. Assigns `root_agent` to the top-level workflow agent.
6. Generates only the imports needed for the node types used.
7. For any `LlmAgent` with a **response** edge to an `A2UIResponse` node, appends the A2UI instruction block (listing only the enabled component types) to that agent's `instruction` field automatically.

## File Structure
```
ecosystem/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── ADK_DESIGNER_SKILL.md              ← this file
└── src/
    ├── main.tsx                       ← React entry point
    ├── App.tsx                        ← Layout: palette | canvas | properties
    ├── App.css                        ← Global styles incl. stuck-node animation
    ├── index.css
    ├── types/
    │   └── agent.ts                   ← AgentKind, NodeData unions, palette items, helpers
    ├── edges/
    │   └── FlowEdge.tsx               ← Custom edge: animated particles for active flow
    ├── nodes/                         ← One React Flow custom node per type
    │   ├── BaseNode.tsx / .css        ← Shared node shell + NodeResizer
    │   ├── LlmAgentNode.tsx
    │   ├── SequentialAgentNode.tsx
    │   ├── ParallelAgentNode.tsx
    │   ├── LoopAgentNode.tsx
    │   ├── ToolNode.tsx
    │   ├── McpToolsetNode.tsx
    │   ├── HumanNode.tsx
    │   ├── EvaluatorNode.tsx
    │   ├── DatabaseNode.tsx
    │   ├── ContextNode.tsx
    │   └── A2UIResponseNode.tsx       ← Output contract: A2UI component registry + renderer
    ├── components/
    │   ├── NodePalette.tsx / .css     ← Left drag-and-drop sidebar (collapsible groups)
    │   ├── PropertyPanel.tsx / .css   ← Right property editor
    │   └── Toolbar.tsx / .css         ← Top action bar
    └── utils/
        └── codeGenerator.ts           ← Graph → Python ADK code
```

## Extending the Designer
| Extension | How to add |
| :--- | :--- |
| **New active node type** | Add to `AgentKind` in `types/agent.ts`, create a component in `nodes/`, add to `PALETTE_ITEMS`, handle in `codeGenerator.ts` |
| **New information node type** | Same as above, plus add the kind to `INFO_KINDS` in `App.tsx` so its edges skip particles |
| **New output contract node type** | Same as above, plus add the kind to `TERMINAL_KINDS` in `App.tsx` so it doesn't trigger stuck-node warnings |
| **New A2UI component type** | Add to `A2UI_ALL_COMPONENTS` in `types/agent.ts`; add its schema string in `codeGenerator.ts` → `schemas` map |
| **New model option** | Add to the `<select>` in `PropertyPanel.tsx` |
| **Edge latency / speed** | Set `data.speed` (seconds) on an edge — `FlowEdge.tsx` reads it to control particle travel time |
| **Persist to file** | Use **Export Preset** — saves full layout as a `.json` preset file |
| **Load existing agent.py** | Write a Python → graph JSON parser (reverse of `codeGenerator.ts`) |
| **Auto-layout** | Integrate `@dagrejs/dagre` to arrange nodes automatically after import |
