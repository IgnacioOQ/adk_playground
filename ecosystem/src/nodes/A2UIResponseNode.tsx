import type { NodeProps } from '@xyflow/react'
import type { Node } from '@xyflow/react'
import type { A2UIResponseData } from '../types/agent'
import BaseNode from './BaseNode'

export default function A2UIResponseNode({ data, selected }: NodeProps<Node<A2UIResponseData>>) {
  const chips = data.components
    .split(',')
    .map((c) => c.trim())
    .filter(Boolean)

  return (
    <BaseNode kind="A2UIResponse" name={data.name} selected={selected}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, marginTop: 2 }}>
        {chips.map((c) => (
          <span
            key={c}
            style={{
              fontSize: 9,
              padding: '1px 5px',
              borderRadius: 9999,
              background: '#ec489920',
              border: '1px solid #ec489960',
              color: '#ec4899',
              fontFamily: 'monospace',
            }}
          >
            {c}
          </span>
        ))}
      </div>
      {data.renderer && (
        <span style={{ fontSize: 10, opacity: 0.6, marginTop: 2 }}>{data.renderer}</span>
      )}
    </BaseNode>
  )
}
