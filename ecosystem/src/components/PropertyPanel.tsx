import type { Node, Edge } from '@xyflow/react'
import type { NodeData } from '../types/agent'
import { kindColor, kindIcon, A2UI_ALL_COMPONENTS } from '../types/agent'
import type { A2UIComponentType } from '../types/agent'
import './PropertyPanel.css'

interface PropertyPanelProps {
  node: Node<NodeData> | null
  edge: Edge | null
  onChange: (id: string, data: Partial<NodeData>) => void
  onDelete: (id: string) => void
  onEdgeChange: (id: string, patch: Partial<Edge>) => void
  onEdgeDelete: (id: string) => void
}

const HANDLES = ['top', 'right', 'bottom', 'left'] as const
type Handle = typeof HANDLES[number]

export default function PropertyPanel({ node, edge, onChange, onDelete, onEdgeChange, onEdgeDelete }: PropertyPanelProps) {
  if (!node && !edge) {
    return (
      <aside className="property-panel property-panel-empty">
        <p>Select a node or edge to edit its properties.</p>
      </aside>
    )
  }

  if (edge) {
    return <EdgePanel edge={edge} onEdgeChange={onEdgeChange} onEdgeDelete={onEdgeDelete} />
  }

  const activeNode = node!
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
        <Field label="Name">
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

        {/* ── Script ── */}
        {data.kind === 'Script' && (
          <>
            <Field label="Description">
              <input
                value={data.description}
                onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
                placeholder="What does this script do?"
              />
            </Field>
            <Field label="Command">
              <input
                value={data.command}
                onChange={(e) => update({ command: e.target.value } as Partial<NodeData>)}
                placeholder="e.g. python scripts/update_dataset.py"
              />
            </Field>
            <Field label="Code (reference)">
              <textarea
                value={data.code}
                onChange={(e) => update({ code: e.target.value } as Partial<NodeData>)}
                rows={6}
                placeholder="    # key functions or logic for reference"
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

        {/* ── Human ── */}
        {data.kind === 'Human' && (
          <>
            <Field label="Description">
              <input
                value={data.description}
                onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
                placeholder="Short description"
              />
            </Field>
            <Field label="Prompt">
              <textarea
                value={data.prompt}
                onChange={(e) => update({ prompt: e.target.value } as Partial<NodeData>)}
                rows={3}
                placeholder="Prompt shown to the human operator…"
              />
            </Field>
          </>
        )}

        {/* ── Evaluator ── */}
        {data.kind === 'Evaluator' && (
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
            <Field label="Success condition">
              <textarea
                value={data.success_condition}
                onChange={(e) => update({ success_condition: e.target.value } as Partial<NodeData>)}
                rows={5}
                placeholder="Natural-language rubric the LLM checks the output against…"
              />
            </Field>
            <p style={{ fontSize: 11, color: '#475569', lineHeight: 1.5, marginTop: 4 }}>
              Place this node as the last sub-agent inside a Loop. It will call <code>exit_loop</code> when the success condition is met, or let the loop continue up to max iterations.
            </p>
          </>
        )}

        {/* ── Database ── */}
        {data.kind === 'Database' && (
          <>
            <Field label="Description">
              <input
                value={data.description}
                onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
                placeholder="What data does this store?"
              />
            </Field>
            <Field label="DB type">
              <input
                value={data.db_type}
                onChange={(e) => update({ db_type: e.target.value } as Partial<NodeData>)}
                placeholder="e.g. PostgreSQL, Firestore, Pinecone"
              />
            </Field>
            <Field label="Connection">
              <input
                value={data.connection}
                onChange={(e) => update({ connection: e.target.value } as Partial<NodeData>)}
                placeholder="Connection string or resource ID"
              />
            </Field>
          </>
        )}

        {/* ── A2UIResponse ── */}
        {data.kind === 'A2UIResponse' && (
          <>
            <Field label="Renderer">
              <input
                value={data.renderer}
                onChange={(e) => update({ renderer: e.target.value } as Partial<NodeData>)}
                placeholder="e.g. React / A2UIRenderer"
              />
            </Field>
            <Field label="Components">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, paddingTop: 2 }}>
                {A2UI_ALL_COMPONENTS.map((c: A2UIComponentType) => {
                  const enabled = data.components.split(',').map((x) => x.trim()).includes(c)
                  return (
                    <button
                      key={c}
                      onClick={() => {
                        const current = data.components.split(',').map((x) => x.trim()).filter(Boolean)
                        const next = enabled
                          ? current.filter((x) => x !== c)
                          : [...current, c]
                        update({ components: next.join(', ') } as Partial<NodeData>)
                      }}
                      style={{
                        fontSize: 11,
                        padding: '2px 8px',
                        borderRadius: 9999,
                        cursor: 'pointer',
                        background: enabled ? '#ec489920' : 'transparent',
                        border: `1px solid ${enabled ? '#ec4899' : '#334155'}`,
                        color: enabled ? '#ec4899' : '#64748b',
                        fontFamily: 'monospace',
                      }}
                    >
                      {c}
                    </button>
                  )
                })}
              </div>
              <input
                style={{ marginTop: 6 }}
                value={data.components}
                onChange={(e) => update({ components: e.target.value } as Partial<NodeData>)}
                placeholder="or type comma-separated list"
              />
            </Field>
            <p style={{ fontSize: 11, color: '#475569', lineHeight: 1.5, marginTop: 4 }}>
              Connect this node from an LLM Agent with a <strong>response</strong> edge. The code
              generator will inject the A2UI instruction block into that agent automatically.
            </p>
          </>
        )}

        {/* ── Context ── */}
        {data.kind === 'Context' && (
          <>
            <Field label="Description">
              <input
                value={data.description}
                onChange={(e) => update({ description: e.target.value } as Partial<NodeData>)}
                placeholder="What kind of knowledge is this?"
              />
            </Field>
            <Field label="Content">
              <textarea
                value={data.content}
                onChange={(e) => update({ content: e.target.value } as Partial<NodeData>)}
                rows={6}
                placeholder="Static text, instructions, or reference data injected into the pipeline…"
              />
            </Field>
          </>
        )}
      </div>

      <div className="pp-footer">
        <button className="pp-delete-btn" onClick={() => onDelete(node!.id)}>
          Delete node
        </button>
      </div>
    </aside>
  )
}

// ── Edge property panel ────────────────────────────────────────────────────────

function EdgePanel({ edge, onEdgeChange, onEdgeDelete }: {
  edge: Edge
  onEdgeChange: (id: string, patch: Partial<Edge>) => void
  onEdgeDelete: (id: string) => void
}) {
  const kind = (edge.data?.kind as string) ?? 'connection'
  const isReturn = !!(edge.data?.isReturn)
  const color = (edge.style?.stroke as string) ?? '#94a3b8'
  const label = isReturn ? 'Response' : kind.charAt(0).toUpperCase() + kind.slice(1).replace('_', ' ')

  return (
    <aside className="property-panel">
      <div className="pp-header" style={{ borderLeftColor: color }}>
        <span className="pp-icon">{isReturn ? '↩' : '→'}</span>
        <div>
          <div className="pp-kind">Edge</div>
          <div className="pp-name">{label}</div>
        </div>
      </div>

      <div className="pp-fields">
        <Field label="Name">
          <input
            value={(edge.data?.name as string) ?? ''}
            onChange={(e) => onEdgeChange(edge.id, { data: { ...edge.data, name: e.target.value } })}
            placeholder="Label shown on the canvas"
          />
        </Field>
        <Field label="Description">
          <textarea
            rows={3}
            value={(edge.data?.description as string) ?? ''}
            onChange={(e) => onEdgeChange(edge.id, { data: { ...edge.data, description: e.target.value } })}
            placeholder="What does this connection represent?"
          />
        </Field>
        <Field label="From handle">
          <HandlePicker
            value={(edge.sourceHandle as Handle) ?? 'right'}
            onChange={(h) => onEdgeChange(edge.id, { sourceHandle: h })}
            color={color}
          />
        </Field>
        <Field label="To handle">
          <HandlePicker
            value={(edge.targetHandle as Handle) ?? 'left'}
            onChange={(h) => onEdgeChange(edge.id, { targetHandle: h })}
            color={color}
          />
        </Field>
      </div>

      <div className="pp-footer">
        <button className="pp-delete-btn" onClick={() => onEdgeDelete(edge.id)}>
          Delete edge
        </button>
      </div>
    </aside>
  )
}

// ── Handle picker — mini node diagram with 4 clickable sides ─────────────────

function HandlePicker({ value, onChange, color }: {
  value: Handle
  onChange: (h: Handle) => void
  color: string
}) {
  return (
    <div className="pp-handle-picker">
      {HANDLES.map((h) => (
        <button
          key={h}
          className={`pp-handle-btn pp-handle-btn-${h}${value === h ? ' pp-handle-btn-active' : ''}`}
          style={value === h ? { borderColor: color, color } : undefined}
          onClick={() => onChange(h)}
          title={h}
        >
          {h[0].toUpperCase()}
        </button>
      ))}
      <div className="pp-handle-node" style={{ borderColor: color }} />
    </div>
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
