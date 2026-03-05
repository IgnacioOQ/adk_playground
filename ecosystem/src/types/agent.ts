export type AgentKind =
  | 'LlmAgent'
  | 'SequentialAgent'
  | 'ParallelAgent'
  | 'LoopAgent'
  | 'Tool'
  | 'McpToolset'
  | 'ObservationSet'

export type EdgeKind = 'sub_agent' | 'delegate' | 'tool'

// ─── Per-node data shapes ────────────────────────────────────────────────────

export interface LlmAgentData extends Record<string, unknown> {
  kind: 'LlmAgent'
  name: string
  model: string
  description: string
  instruction: string
  output_key: string
}

export interface SequentialAgentData extends Record<string, unknown> {
  kind: 'SequentialAgent'
  name: string
  description: string
}

export interface ParallelAgentData extends Record<string, unknown> {
  kind: 'ParallelAgent'
  name: string
  description: string
}

export interface LoopAgentData extends Record<string, unknown> {
  kind: 'LoopAgent'
  name: string
  description: string
  max_iterations: number
}

export interface ToolData extends Record<string, unknown> {
  kind: 'Tool'
  name: string
  description: string
  /** Python function body — will be wrapped in a def block */
  code: string
}

export interface McpToolsetData extends Record<string, unknown> {
  kind: 'McpToolset'
  name: string
  /** Shell command to start the server, e.g. "mcp-server-fetch" */
  command: string
  /** Space-separated CLI args */
  args: string
  /** Comma-separated tool names to expose, empty = all */
  tool_filter: string
}

export interface ObservationSetData extends Record<string, unknown> {
  kind: 'ObservationSet'
  /** Display label shown on the frame */
  name: string
  /** Name of the LlmAgent this scope belongs to */
  for_agent: string
  /** Color accent for the frame border */
  color: string
}

export type NodeData =
  | LlmAgentData
  | SequentialAgentData
  | ParallelAgentData
  | LoopAgentData
  | ToolData
  | McpToolsetData
  | ObservationSetData

// ─── Palette entry (what shows up in the left sidebar) ───────────────────────

export interface PaletteItem {
  kind: AgentKind
  label: string
  description: string
  color: string
  icon: string
}

export const PALETTE_ITEMS: PaletteItem[] = [
  {
    kind: 'LlmAgent',
    label: 'LLM Agent',
    description: 'Intelligent agent powered by an LLM',
    color: '#3b82f6',
    icon: '🤖',
  },
  {
    kind: 'SequentialAgent',
    label: 'Sequential',
    description: 'Runs sub-agents one after another',
    color: '#22c55e',
    icon: '➡️',
  },
  {
    kind: 'ParallelAgent',
    label: 'Parallel',
    description: 'Runs sub-agents concurrently',
    color: '#a855f7',
    icon: '⚡',
  },
  {
    kind: 'LoopAgent',
    label: 'Loop',
    description: 'Repeats sub-agents until exit or max iterations',
    color: '#f97316',
    icon: '🔄',
  },
  {
    kind: 'Tool',
    label: 'Tool',
    description: 'Custom Python function tool',
    color: '#6b7280',
    icon: '🔧',
  },
  {
    kind: 'McpToolset',
    label: 'MCP Toolset',
    description: 'External MCP server integration',
    color: '#14b8a6',
    icon: '🔌',
  },
  {
    kind: 'ObservationSet',
    label: 'Observation Set',
    description: 'Visual scope: nodes available to an LLM agent',
    color: '#e879f9',
    icon: '👁️',
  },
]

// ─── Default data for each kind ──────────────────────────────────────────────

export function defaultData(kind: AgentKind): NodeData {
  switch (kind) {
    case 'LlmAgent':
      return {
        kind,
        name: 'my_agent',
        model: 'gemini-2.5-flash',
        description: '',
        instruction: 'You are a helpful assistant.',
        output_key: '',
      }
    case 'SequentialAgent':
      return { kind, name: 'sequential_agent', description: '' }
    case 'ParallelAgent':
      return { kind, name: 'parallel_agent', description: '' }
    case 'LoopAgent':
      return { kind, name: 'loop_agent', description: '', max_iterations: 3 }
    case 'Tool':
      return {
        kind,
        name: 'my_tool',
        description: '',
        code: '    # implement tool logic here\n    return {}',
      }
    case 'McpToolset':
      return {
        kind,
        name: 'mcp_toolset',
        command: 'mcp-server-fetch',
        args: '',
        tool_filter: '',
      }
    case 'ObservationSet':
      return {
        kind,
        name: 'Observation Set',
        for_agent: '',
        color: '#e879f9',
      }
  }
}

// ─── Color helper ────────────────────────────────────────────────────────────

export function kindColor(kind: AgentKind): string {
  return PALETTE_ITEMS.find((p) => p.kind === kind)?.color ?? '#6b7280'
}

export function kindIcon(kind: AgentKind): string {
  return PALETTE_ITEMS.find((p) => p.kind === kind)?.icon ?? '?'
}

// ─── Edge color lookup ────────────────────────────────────────────────────────
// Determines edge appearance based on source and target node kinds.

export type EdgeStyle = {
  color: string
  dashed: boolean
  animated: boolean
  kind: EdgeKind
}

const TOOL_KINDS: AgentKind[] = ['Tool', 'McpToolset']
const WORKFLOW_KINDS: AgentKind[] = ['SequentialAgent', 'ParallelAgent', 'LoopAgent']

export function edgeStyle(sourceKind?: AgentKind, targetKind?: AgentKind): EdgeStyle {
  if (targetKind && TOOL_KINDS.includes(targetKind)) {
    // Any → Tool/MCP: teal dashed
    return { color: '#14b8a6', dashed: true, animated: false, kind: 'tool' }
  }
  if (sourceKind === 'LlmAgent') {
    // LLM → agent (workflow or another LLM): orange solid
    return { color: '#f97316', dashed: false, animated: false, kind: 'delegate' }
  }
  if (sourceKind && WORKFLOW_KINDS.includes(sourceKind)) {
    // Workflow → sub-agent: indigo animated
    return { color: '#6366f1', dashed: false, animated: true, kind: 'sub_agent' }
  }
  // Fallback
  return { color: '#94a3b8', dashed: false, animated: false, kind: 'sub_agent' }
}
