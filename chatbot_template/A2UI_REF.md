# A2UI Protocol — Agent-to-UI Reference
- status: active
- type: reference
- label: [normative, frontend, backend]
- injection: informational
- volatility: evolving
- last_checked: 2026-04-06
<!-- content -->

## Overview

**A2UI (Agent-to-UI)** is an open protocol (Apache 2.0, created by Google) that allows AI agents to generate rich, interactive user interfaces as structured JSON. Instead of returning plain text, the agent returns a declarative component tree. The frontend maps that tree to its own native widgets — no HTML, no JavaScript execution, no UI injection risk.

**Key property:** the agent describes *what* the UI should express; the frontend decides *how* to render it. The same A2UI JSON payload can render in React, Flutter, SwiftUI, Angular, or Google Chat Cards v2.

---

## Decoupled Frontend/Backend Architecture

A2UI is most powerful in a **decoupled deployment** where the agent and the UI are separate services:

```
┌─────────────────────────────────────┐       ┌──────────────────────────────────────┐
│          FRONTEND                   │ HTTP  │            BACKEND                   │
│  Next.js / React (TypeScript)       │──────▶│  FastAPI (Python)                    │
│                                     │◀──────│  └── ADK runner → root_agent         │
│  A2UIRenderer (JSON → widgets)      │       │       └── Tools / MCP servers        │
│  useChat (session, POST, SSE)       │       │                                      │
└─────────────────────────────────────┘       └──────────────────────────────────────┘
```

**Data flow per turn:**
1. User submits a message → frontend `POST /chat` (or `GET /stream` for SSE)
2. FastAPI passes the message to the ADK runner
3. Agent processes, calls tools/MCP servers as needed
4. Agent returns either plain text or an A2UI JSON payload
5. Backend strips any markdown code fences and classifies the response (`type: "text"` or `type: "a2ui"`)
6. Frontend renders: plain text in a chat bubble, A2UI payload through `A2UIRenderer`
7. User interacts with a widget → action string sent back as a new message → loop continues

---

## A2UI JSON Schema

Every A2UI response is a JSON object with a top-level `components` array. Each element has a `type` field and type-specific properties.

```json
{
  "components": [
    { "type": "text", "value": "Here are your results:" },
    {
      "type": "card",
      "title": "Result #1",
      "subtitle": "High confidence",
      "body": [
        { "type": "text", "value": "Details about result 1." },
        { "type": "button", "label": "View More", "action": "view_result_1" }
      ]
    },
    { "type": "list", "items": ["Item A", "Item B", "Item C"] }
  ]
}
```

---

## Component Registry

The registry lives in two places: the TypeScript type union in `useChat.ts` and the `switch` statement in `A2UIRenderer.tsx`. Both must be updated when adding a new component type.

### Current registered types

| Type | Schema | Action fired on interaction | Notes |
| :--- | :--- | :--- | :--- |
| `text` | `{ "type": "text", "value": "..." }` | — | Plain paragraph |
| `button` | `{ "type": "button", "label": "...", "action": "..." }` | `action` string | Generic CTA |
| `card` | `{ "type": "card", "title": "...", "subtitle": "...", "body": [...] }` | — | Nested components in `body` |
| `list` | `{ "type": "list", "items": ["...", ...] }` | — | Unordered list |
| `rps_selector` | `{ "type": "rps_selector", "prompt": "..." }` | `selected_rps_rock` / `selected_rps_paper` / `selected_rps_scissors` | 🪨📄✂️ pick buttons |
| `sealed_box` | `{ "type": "sealed_box", "label": "..." }` | — | 🔒 dashed box — hidden agent choice |

### TypeScript union (`src/hooks/useChat.ts`)

```typescript
export type A2UIComponent =
  | { type: "text"; value: string }
  | { type: "button"; label: string; action: string }
  | { type: "card"; title: string; subtitle?: string; body: A2UIComponent[] }
  | { type: "list"; items: string[] }
  | { type: "rps_selector"; prompt?: string }
  | { type: "sealed_box"; label?: string };
```

### Renderer (`src/components/A2UIRenderer.tsx`)

```typescript
function ComponentNode({ component, onAction }) {
  switch (component.type) {
    case "text":         return <p>{component.value}</p>;
    case "button":       return <button onClick={() => onAction?.(component.action)}>{component.label}</button>;
    case "card":         return <div className="a2ui-card">...</div>;
    case "list":         return <ul>{component.items.map(i => <li>{i}</li>)}</ul>;
    case "rps_selector": return <div className="rps-selector-grid">🪨📄✂️ buttons</div>;
    case "sealed_box":   return <div className="a2ui-sealed-box">🔒 {component.label}</div>;
    default:             return null;
  }
}
```

---

## Instructing the Agent

The agent must be told about the component registry in its `instruction` field. Include every supported type with a compact schema description:

```python
instruction="""
When your response contains structured data or requires user input, return a
JSON object with a top-level 'components' array. Supported types:

  text         → { "type": "text", "value": "<string>" }
  button       → { "type": "button", "label": "<string>", "action": "<string>" }
  card         → { "type": "card", "title": "<string>", "subtitle": "<string>", "body": [...] }
  list         → { "type": "list", "items": ["<string>", ...] }
  rps_selector → { "type": "rps_selector", "prompt": "<string>" }
  sealed_box   → { "type": "sealed_box", "label": "<string>" }

For plain conversational replies, respond in normal text — NOT JSON.
"""
```

---

## Code Fence Stripping

LLMs frequently wrap JSON in markdown code fences (` ```json ... ``` `) even when explicitly instructed not to. The backend must strip fences before calling `json.loads`. This is implemented in `_parse_response` in `main.py`:

```python
def _parse_response(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
            if "components" in payload:
                return {"type": "a2ui", "payload": payload}
        except json.JSONDecodeError:
            pass
    return {"type": "text", "text": text}
```

---

## Recursive UI Logic

A2UI interactions are re-entered into the agent loop as plain-text messages. This creates a **recursive conversational UI** — the interface evolves dynamically without a predefined navigation tree:

```
Agent returns rps_selector
  → User clicks 🪨 Rock
    → Frontend sends "selected_rps_rock"
      → Agent calls MCP tool, evaluates round, returns result card
        → User clicks "Play again"
          → Frontend sends "play_again"
            → Agent starts next round ...
```

In `ChatWindow.tsx`, all A2UI actions are wired to `sendMessage`:
```typescript
const handleAction = (action: string) => sendMessage(action);
```

---

## Streaming vs Single-turn

| Mode | Endpoint | When to use |
| :--- | :--- | :--- |
| **Single-turn** | `POST /chat` | Tool-heavy agents (MCP calls block until complete anyway) |
| **Streaming (SSE)** | `GET /stream` | Long-form conversational agents where progressive text display improves UX |

For agents that make MCP tool calls (like the RPS game), streaming adds little value — the meaningful output only arrives after all tool calls complete. Streaming is most useful for pure conversational LLM agents generating long text responses.

---

## Extending the Registry

The registry is fully extensible. Any JSON-describable UI can be added as a new component type. **The extension pattern is always the same:**

1. Add TypeScript type to the union in `useChat.ts`
2. Add `case` to the `switch` in `A2UIRenderer.tsx`
3. Add entry to the agent `instruction`

### Example: chart component (Recharts)

Install:
```bash
npm install recharts
```

Add type (`useChat.ts`):
```typescript
| { type: "chart"; chart_type: "bar" | "line" | "pie"; title?: string; data: { label: string; value: number }[] }
```

Add renderer case (`A2UIRenderer.tsx`):
```typescript
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
         LineChart, Line, PieChart, Pie, Cell } from "recharts";

case "chart": {
  const { chart_type, title, data } = component;
  return (
    <div className="a2ui-chart">
      {title && <p className="chart-title">{title}</p>}
      <ResponsiveContainer width="100%" height={220}>
        {chart_type === "bar" ? (
          <BarChart data={data}>
            <XAxis dataKey="label" /><YAxis /><Tooltip />
            <Bar dataKey="value" fill="#0070f3" radius={[4,4,0,0]} />
          </BarChart>
        ) : chart_type === "line" ? (
          <LineChart data={data}>
            <XAxis dataKey="label" /><YAxis /><Tooltip />
            <Line type="monotone" dataKey="value" stroke="#0070f3" strokeWidth={2} dot={false} />
          </LineChart>
        ) : (
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={80} label>
              {data.map((_, i) => <Cell key={i} fill={["#0070f3","#00b4d8","#90e0ef","#caf0f8"][i % 4]} />)}
            </Pie>
            <Tooltip />
          </PieChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
```

Add to agent instruction:
```python
- chart : { "type": "chart", "chart_type": "bar"|"line"|"pie",
            "title": "<string>",
            "data": [{"label": "<string>", "value": <number>}, ...] }
Use chart when displaying numerical comparisons, trends, or distributions.
```

Agent emits:
```json
{
  "components": [
    { "type": "text", "value": "Q1 Sales:" },
    { "type": "chart", "chart_type": "bar", "title": "Sales Q1",
      "data": [{"label": "Jan", "value": 120}, {"label": "Feb", "value": 95}] }
  ]
}
```

Other component types that follow the same pattern: maps (`react-leaflet`), tables, calendars, file upload widgets, image carousels.

---

## MCP Servers and Session State

When the agent needs persistent state across turns (e.g., game history, user preferences), use a **FastMCP server** as a subprocess:

```python
# backend/mcp_servers/my_memory_server.py
from mcp.server.fastmcp import FastMCP
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
mcp = FastMCP("my-memory")

@mcp.tool()
def save_data(session_id: str, key: str, value: str) -> str:
    """Save a key-value pair for this session."""
    ...

@mcp.tool()
def get_data(session_id: str, key: str) -> str:
    """Retrieve a value for this session."""
    ...

if __name__ == "__main__":
    mcp.run()
```

Wire it to the agent with `StdioConnectionParams` — the subprocess is spawned automatically on first tool call, no extra terminal needed:

```python
McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python3",
            args=["/absolute/path/to/my_memory_server.py"],
        ),
    ),
    tool_filter=["save_data", "get_data"],
)
```

Use **file-backed storage** (`json` files per session) so state persists across multiple tool calls within the same FastAPI process lifetime.

---

## Key External References

| Resource | URL |
| :--- | :--- |
| A2UI Official Site | `https://a2ui.org` |
| A2UI GitHub | `https://github.com/google/A2UI` |
| A2UI Chat App Quickstart | `https://developers.google.com/workspace/add-ons/chat/quickstart-a2ui-agent` |
| Recharts | `https://recharts.org` |
| FastAPI Docs | `https://fastapi.tiangolo.com` |
| ADK Documentation | `https://google.github.io/adk-docs/` |
