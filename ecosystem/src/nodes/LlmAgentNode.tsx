import type { NodeProps } from '@xyflow/react'
import type { Node } from '@xyflow/react'
import type { LlmAgentData } from '../types/agent'
import BaseNode from './BaseNode'

export default function LlmAgentNode({ data, selected }: NodeProps<Node<LlmAgentData>>) {
  return (
    <BaseNode kind="LlmAgent" name={data.name} selected={selected}>
      {data.model && <span>{data.model}</span>}
      {data.output_key && <span>→ {data.output_key}</span>}
    </BaseNode>
  )
}
