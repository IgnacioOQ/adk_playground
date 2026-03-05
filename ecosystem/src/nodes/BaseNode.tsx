import { Handle, Position } from '@xyflow/react'
import type { ReactNode } from 'react'
import { kindColor, kindIcon } from '../types/agent'
import type { AgentKind } from '../types/agent'
import './BaseNode.css'

interface BaseNodeProps {
  kind: AgentKind
  name: string
  selected?: boolean
  children?: ReactNode
}

export default function BaseNode({ kind, name, selected = false, children }: BaseNodeProps) {
  const color = kindColor(kind)
  const icon = kindIcon(kind)

  return (
    <div
      className="base-node"
      style={{
        borderColor: selected ? '#fff' : color,
        boxShadow: selected ? `0 0 0 2px ${color}` : `0 0 0 1px ${color}40`,
      }}
    >
      {/* Four handles — one per side. connectionMode="loose" in App allows any-to-any. */}
      <Handle type="source" position={Position.Top}    id="top"    className="node-handle node-handle-top"    style={{ background: color }} />
      <Handle type="source" position={Position.Bottom} id="bottom" className="node-handle node-handle-bottom" style={{ background: color }} />
      <Handle type="source" position={Position.Left}   id="left"   className="node-handle node-handle-left"   style={{ background: color }} />
      <Handle type="source" position={Position.Right}  id="right"  className="node-handle node-handle-right"  style={{ background: color }} />

      <div className="base-node-header" style={{ background: color }}>
        <span className="base-node-icon">{icon}</span>
        <span className="base-node-kind">{kind}</span>
      </div>

      <div className="base-node-body">
        <div className="base-node-name">{name || <em>unnamed</em>}</div>
        {children && <div className="base-node-extra">{children}</div>}
      </div>
    </div>
  )
}
