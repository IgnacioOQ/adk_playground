export type AgentKind =
  | 'LlmAgent'
  | 'SequentialAgent'
  | 'ParallelAgent'
  | 'LoopAgent'
  | 'Tool'
  | 'McpToolset'
  | 'Script'
  | 'Database'
  | 'Context'
  | 'Human'
  | 'Evaluator'
  | 'A2UIResponse'

export type EdgeKind = 'sub_agent' | 'delegate' | 'tool' | 'response'

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

export interface EvaluatorData extends Record<string, unknown> {
  kind: 'Evaluator'
  name: string
  model: string
  /** Natural-language rubric the LLM checks the output against */
  success_condition: string
}

export interface HumanData extends Record<string, unknown> {
  kind: 'Human'
  name: string
  description: string
  /** Prompt shown to the human operator */
  prompt: string
}

export interface DatabaseData extends Record<string, unknown> {
  kind: 'Database'
  name: string
  description: string
  /** e.g. PostgreSQL, Firestore, BigQuery, Pinecone */
  db_type: string
  /** Connection string, resource ID, or config reference */
  connection: string
}

export interface ContextData extends Record<string, unknown> {
  kind: 'Context'
  name: string
  description: string
  /** The contextual content or knowledge passed into the pipeline */
  content: string
}

export type A2UIComponentType = 'text' | 'button' | 'card' | 'list' | 'rps_selector' | 'sealed_box'

export const A2UI_ALL_COMPONENTS: A2UIComponentType[] = ['text', 'button', 'card', 'list', 'rps_selector', 'sealed_box']

export interface A2UIResponseData extends Record<string, unknown> {
  kind: 'A2UIResponse'
  name: string
  /** Comma-separated list of enabled component types */
  components: string
  /** Target renderer, e.g. "React / A2UIRenderer" */
  renderer: string
}

export interface ScriptData extends Record<string, unknown> {
  kind: 'Script'
  name: string
  description: string
  /** Path or command used to invoke the script */
  command: string
  /** Python or shell code body for reference */
  code: string
}

export type NodeData =
  | LlmAgentData
  | SequentialAgentData
  | ParallelAgentData
  | LoopAgentData
  | ToolData
  | McpToolsetData
  | ScriptData
  | DatabaseData
  | ContextData
  | HumanData
  | EvaluatorData
  | A2UIResponseData

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
    kind: 'Script',
    label: 'Script',
    description: 'Standalone script — runs independently, not called by an LLM',
    color: '#f59e0b',
    icon: '📜',
  },
  {
    kind: 'Database',
    label: 'Database',
    description: 'Persistent data store connected to the pipeline',
    color: '#8b5cf6',
    icon: '🗄️',
  },
  {
    kind: 'Context',
    label: 'Context',
    description: 'Static or dynamic knowledge injected into the pipeline',
    color: '#06b6d4',
    icon: '📋',
  },
  {
    kind: 'Human',
    label: 'Human / User',
    description: 'Human-in-the-loop interaction point',
    color: '#eab308',
    icon: '👤',
  },
  {
    kind: 'Evaluator',
    label: 'Evaluator',
    description: 'Checks output against a success condition; exits loop when satisfied',
    color: '#10b981',
    icon: '✅',
  },
  {
    kind: 'A2UIResponse',
    label: 'A2UI Response',
    description: 'Agent-to-UI structured JSON output contract',
    color: '#ec4899',
    icon: '🎨',
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
    case 'Script':
      return {
        kind,
        name: 'my_script',
        description: '',
        command: 'python scripts/my_script.py',
        code: '    # script logic here',
      }
    case 'Database':
      return {
        kind,
        name: 'my_database',
        description: '',
        db_type: 'PostgreSQL',
        connection: '',
      }
    case 'Context':
      return {
        kind,
        name: 'my_context',
        description: '',
        content: '',
      }
    case 'Human':
      return {
        kind,
        name: 'human_input',
        description: '',
        prompt: 'Please provide your input:',
      }
    case 'Evaluator':
      return {
        kind,
        name: 'evaluator',
        model: 'gemini-2.5-flash',
        success_condition: 'The output fully and correctly addresses the original request.',
      }
    case 'A2UIResponse':
      return {
        kind,
        name: 'a2ui_response',
        components: 'text, button, card, list',
        renderer: 'React / A2UIRenderer',
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
  if (targetKind === 'A2UIResponse') {
    // Any → A2UIResponse: pink dashed
    return { color: '#ec4899', dashed: true, animated: false, kind: 'response' }
  }
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
