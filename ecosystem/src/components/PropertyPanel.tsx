import type { Node } from '@xyflow/react'
import type { NodeData } from '../types/agent'
import { kindColor, kindIcon } from '../types/agent'
import './PropertyPanel.css'

interface PropertyPanelProps {
  node: Node<NodeData> | null
  onChange: (id: string, data: Partial<NodeData>) => void
  onDelete: (id: string) => void
}

export default function PropertyPanel({ node, onChange, onDelete }: PropertyPanelProps) {
  if (!node) {
    return (
      <aside className="property-panel property-panel-empty">
        <p>Select a node to edit its properties.</p>
      </aside>
    )
  }

  const activeNode = node  // capture after null guard — TypeScript narrows in closures via const
  const { data } = activeNode
  const color = kindColor(data.kind)
  const icon = kindIcon(data.kind)

  function update(patch: Partial<NodeData>) {
    onChange(activeNode.id, patch)
  }

  return (
    <aside className="property-panel">
      <div className="pp-header" style={{ borderLeftColor: color }}>
        <span className="pp-icon">{icon}</span>
        <div>
          <div className="pp-kind">{data.kind}</div>
          <div className="pp-name">{data.name}</div>
        </div>
      </div>

      <div className="pp-fields">
        {/* ── Common name / label field ── */}
        <Field label={data.kind === 'ObservationSet' ? 'Label' : 'Name'}>
          <input
            value={data.name}
            onChange={(e) => update({ name: e.target.value } as Partial<NodeData>)}
          />
        </Field>

        {/* ── LlmAgent ── */}
        {data.kind === 'LlmAgent' && (
          <>
            <Field label="Model">
              <select
                value={data.model}
                onChange={(e) => update({ model: e.target.value } as Partial<NodeData>)}
              >
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash</option>
              </select>
            </Field>
            <Field label="Description">
              <input
                value={data.description}
                onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
                placeholder="Short description"
              />
            </Field>
            <Field label="Output key">
              <input
                value={data.output_key}
                onChange={(e) => update({ output_key: e.target.value } as Partial<NodeData>)}
                placeholder="e.g. overview"
              />
            </Field>
            <Field label="Instruction">
              <textarea
                value={data.instruction}
                onChange={(e) => update({ instruction: e.target.value } as Partial<NodeData>)}
                rows={6}
                placeholder="System prompt / instruction for this agent…"
              />
            </Field>
          </>
        )}

        {/* ── SequentialAgent / ParallelAgent ── */}
        {(data.kind === 'SequentialAgent' || data.kind === 'ParallelAgent') && (
          <Field label="Description">
            <input
              value={data.description}
              onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
              placeholder="Short description"
            />
          </Field>
        )}

        {/* ── LoopAgent ── */}
        {data.kind === 'LoopAgent' && (
          <>
            <Field label="Description">
              <input
                value={data.description}
                onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
                placeholder="Short description"
              />
            </Field>
            <Field label="Max iterations">
              <input
                type="number"
                min={1}
                max={20}
                value={data.max_iterations}
                onChange={(e) =>
                  update({ max_iterations: parseInt(e.target.value) || 1 } as Partial<NodeData>)
                }
              />
            </Field>
          </>
        )}

        {/* ── Tool ── */}
        {data.kind === 'Tool' && (
          <>
            <Field label="Description">
              <input
                value={data.description}
                onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
                placeholder="What does this tool do?"
              />
            </Field>
            <Field label="Function body">
              <textarea
                value={data.code}
                onChange={(e) => update({ code: e.target.value } as Partial<NodeData>)}
                rows={8}
                placeholder="    # Python code inside the def block"
                className="pp-code"
              />
            </Field>
          </>
        )}

        {/* ── McpToolset ── */}
        {data.kind === 'McpToolset' && (
          <>
            <Field label="Command">
              <input
                value={data.command}
                onChange={(e) => update({ command: e.target.value } as Partial<NodeData>)}
                placeholder="e.g. mcp-server-fetch"
              />
            </Field>
            <Field label="Args (space-separated)">
              <input
                value={data.args}
                onChange={(e) => update({ args: e.target.value } as Partial<NodeData>)}
                placeholder="e.g. --port 8080"
              />
            </Field>
            <Field label="Tool filter (comma-separated)">
              <input
                value={data.tool_filter}
                onChange={(e) => update({ tool_filter: e.target.value } as Partial<NodeData>)}
                placeholder="e.g. fetch, search (empty = all)"
              />
            </Field>
          </>
        )}

        {/* ── ObservationSet ── */}
        {data.kind === 'ObservationSet' && (
          <>
            <Field label="For agent">
              <input
                value={data.for_agent}
                onChange={(e) => update({ for_agent: e.target.value } as Partial<NodeData>)}
                placeholder="Name of the LLM agent this scope belongs to"
              />
            </Field>
            <Field label="Frame color">
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <input
                  type="color"
                  value={data.color as string}
                  onChange={(e) => update({ color: e.target.value } as Partial<NodeData>)}
                  style={{ width: 36, height: 28, padding: 2, cursor: 'pointer' }}
                />
                <span style={{ fontSize: 11, color: '#64748b' }}>{data.color as string}</span>
              </div>
            </Field>
            <p style={{ fontSize: 11, color: '#475569', lineHeight: 1.5, marginTop: 4 }}>
              Drag this frame behind the nodes that are visible to the named agent. Resize by selecting and dragging the corners.
            </p>
          </>
        )}
      </div>

      <div className="pp-footer">
        <button className="pp-delete-btn" onClick={() => onDelete(node.id)}>
          Delete node
        </button>
      </div>
    </aside>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="pp-field">
      <label className="pp-field-label">{label}</label>
      {children}
    </div>
  )
}
