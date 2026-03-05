import { NodeResizer } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { Node } from '@xyflow/react'
import type { ObservationSetData } from '../types/agent'
import './ObservationSetNode.css'

export default function ObservationSetNode({ data, selected }: NodeProps<Node<ObservationSetData>>) {
  const color = data.color as string || '#e879f9'

  return (
    <div
      className="obs-node"
      style={{
        borderColor: selected ? '#fff' : color,
        background: `${color}0d`,   // 5% opacity fill
      }}
    >
      <NodeResizer
        minWidth={160}
        minHeight={120}
        isVisible={selected}
        lineStyle={{ borderColor: color }}
        handleStyle={{ background: color, border: 'none', width: 8, height: 8 }}
      />

      <div className="obs-node-label" style={{ color }}>
        <span className="obs-node-icon">👁️</span>
        <span className="obs-node-title">{data.name || 'Observation Set'}</span>
        {data.for_agent && (
          <span className="obs-node-agent">for: {data.for_agent}</span>
        )}
      </div>
    </div>
  )
}
