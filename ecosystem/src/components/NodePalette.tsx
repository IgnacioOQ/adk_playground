import { useState } from 'react'
import { PALETTE_ITEMS } from '../types/agent'
import type { AgentKind } from '../types/agent'
import './NodePalette.css'

interface NodePaletteProps {
  onDragStart: (kind: AgentKind, event: React.DragEvent) => void
}

const WORKFLOW_KINDS: AgentKind[] = ['SequentialAgent', 'ParallelAgent', 'LoopAgent', 'Evaluator']
const WORKFLOW_COLOR = '#6366f1'

const TOOL_KINDS: AgentKind[] = ['Tool', 'McpToolset', 'Script']
const TOOL_COLOR = '#6b7280'

const INFO_KINDS: AgentKind[] = ['Database', 'Context']
const INFO_COLOR = '#8b5cf6'

const OUTPUT_KINDS: AgentKind[] = ['A2UIResponse']
const OUTPUT_COLOR = '#ec4899'

function paletteItem(kind: AgentKind) {
  return PALETTE_ITEMS.find((p) => p.kind === kind)!
}

export default function NodePalette({ onDragStart }: NodePaletteProps) {
  const [workflowOpen, setWorkflowOpen] = useState(false)
  const [toolsOpen, setToolsOpen] = useState(false)
  const [outputOpen, setOutputOpen] = useState(false)
  const [infoOpen, setInfoOpen] = useState(false)

  const workflowItems = WORKFLOW_KINDS.map(paletteItem)
  const toolItems = TOOL_KINDS.map(paletteItem)
  const outputItems = OUTPUT_KINDS.map(paletteItem)
  const infoItems = INFO_KINDS.map(paletteItem)

  const standaloneKinds: AgentKind[] = ['LlmAgent', 'Human']
  const standaloneItems = standaloneKinds.map(paletteItem)

  return (
    <aside className="node-palette">
      <div className="palette-title">Nodes</div>

      {/* LLM Agent */}
      {standaloneItems.slice(0, 1).map((item) => (
        <div
          key={item.kind}
          className="palette-item"
          draggable
          onDragStart={(e) => onDragStart(item.kind, e)}
          style={{ borderLeftColor: item.color }}
          title={item.description}
        >
          <span className="palette-icon">{item.icon}</span>
          <div className="palette-text">
            <div className="palette-label">{item.label}</div>
            <div className="palette-desc">{item.description}</div>
          </div>
        </div>
      ))}

      {/* Workflow Agents group */}
      <div className="palette-group">
        <button
          className="palette-group-header"
          style={{ borderLeftColor: WORKFLOW_COLOR }}
          onClick={() => setWorkflowOpen((o) => !o)}
        >
          <span className="palette-icon">🔀</span>
          <div className="palette-text">
            <div className="palette-label">Workflow Agents</div>
            <div className="palette-desc">Sequential, Parallel, Loop, Evaluator</div>
          </div>
          <span className="palette-group-chevron" style={{ transform: workflowOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}>›</span>
        </button>
        {workflowOpen && (
          <div className="palette-group-children">
            {workflowItems.map((item) => (
              <div
                key={item.kind}
                className="palette-item palette-item-child"
                draggable
                onDragStart={(e) => onDragStart(item.kind, e)}
                style={{ borderLeftColor: item.color }}
                title={item.description}
              >
                <span className="palette-icon">{item.icon}</span>
                <div className="palette-text">
                  <div className="palette-label">{item.label}</div>
                  <div className="palette-desc">{item.description}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tools group */}
      <div className="palette-group">
        <button
          className="palette-group-header"
          style={{ borderLeftColor: TOOL_COLOR }}
          onClick={() => setToolsOpen((o) => !o)}
        >
          <span className="palette-icon">🧰</span>
          <div className="palette-text">
            <div className="palette-label">Tools</div>
            <div className="palette-desc">Tool, MCP Toolset, Script</div>
          </div>
          <span className="palette-group-chevron" style={{ transform: toolsOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}>›</span>
        </button>
        {toolsOpen && (
          <div className="palette-group-children">
            {toolItems.map((item) => (
              <div
                key={item.kind}
                className="palette-item palette-item-child"
                draggable
                onDragStart={(e) => onDragStart(item.kind, e)}
                style={{ borderLeftColor: item.color }}
                title={item.description}
              >
                <span className="palette-icon">{item.icon}</span>
                <div className="palette-text">
                  <div className="palette-label">{item.label}</div>
                  <div className="palette-desc">{item.description}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Output Contracts group */}
      <div className="palette-group">
        <button
          className="palette-group-header"
          style={{ borderLeftColor: OUTPUT_COLOR }}
          onClick={() => setOutputOpen((o) => !o)}
        >
          <span className="palette-icon">🎨</span>
          <div className="palette-text">
            <div className="palette-label">Output Contracts</div>
            <div className="palette-desc">A2UI Response</div>
          </div>
          <span className="palette-group-chevron" style={{ transform: outputOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}>›</span>
        </button>
        {outputOpen && (
          <div className="palette-group-children">
            {outputItems.map((item) => (
              <div
                key={item.kind}
                className="palette-item palette-item-child"
                draggable
                onDragStart={(e) => onDragStart(item.kind, e)}
                style={{ borderLeftColor: item.color }}
                title={item.description}
              >
                <span className="palette-icon">{item.icon}</span>
                <div className="palette-text">
                  <div className="palette-label">{item.label}</div>
                  <div className="palette-desc">{item.description}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Information Sets group */}
      <div className="palette-group">
        <button
          className="palette-group-header"
          style={{ borderLeftColor: INFO_COLOR }}
          onClick={() => setInfoOpen((o) => !o)}
        >
          <span className="palette-icon">🗂️</span>
          <div className="palette-text">
            <div className="palette-label">Information Sets</div>
            <div className="palette-desc">Database, Context</div>
          </div>
          <span className="palette-group-chevron" style={{ transform: infoOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}>›</span>
        </button>
        {infoOpen && (
          <div className="palette-group-children">
            {infoItems.map((item) => (
              <div
                key={item.kind}
                className="palette-item palette-item-child"
                draggable
                onDragStart={(e) => onDragStart(item.kind, e)}
                style={{ borderLeftColor: item.color }}
                title={item.description}
              >
                <span className="palette-icon">{item.icon}</span>
                <div className="palette-text">
                  <div className="palette-label">{item.label}</div>
                  <div className="palette-desc">{item.description}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Human */}
      {standaloneItems.slice(1).map((item) => (
        <div
          key={item.kind}
          className="palette-item"
          draggable
          onDragStart={(e) => onDragStart(item.kind, e)}
          style={{ borderLeftColor: item.color }}
          title={item.description}
        >
          <span className="palette-icon">{item.icon}</span>
          <div className="palette-text">
            <div className="palette-label">{item.label}</div>
            <div className="palette-desc">{item.description}</div>
          </div>
        </div>
      ))}

      <div className="palette-hint">
        Drag nodes onto the canvas.<br />
        Connect them by dragging from a handle.<br />
        Click a node to edit its properties.
      </div>

      <div className="palette-section-title">Edge colors</div>
      <div className="palette-edge-legend">
        <div className="edge-legend-item">
          <span className="edge-line" style={{ background: '#6366f1' }} />
          <span>workflow → agent</span>
        </div>
        <div className="edge-legend-item">
          <span className="edge-line" style={{ background: '#f97316' }} />
          <span>LLM → agent</span>
        </div>
        <div className="edge-legend-item">
          <span className="edge-line edge-line-dashed" style={{ backgroundImage: 'repeating-linear-gradient(90deg,#14b8a6 0,#14b8a6 4px,transparent 4px,transparent 8px)' }} />
          <span>any → tool</span>
        </div>
        <div className="edge-legend-item">
          <span className="edge-line edge-line-dashed" style={{ backgroundImage: 'repeating-linear-gradient(90deg,#ec4899 0,#ec4899 4px,transparent 4px,transparent 8px)' }} />
          <span>LLM → A2UI response</span>
        </div>
      </div>
    </aside>
  )
}
