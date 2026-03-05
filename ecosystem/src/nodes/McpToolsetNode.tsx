import type { NodeProps } from '@xyflow/react'
import type { Node } from '@xyflow/react'
import type { McpToolsetData } from '../types/agent'
import BaseNode from './BaseNode'

export default function McpToolsetNode({ data, selected }: NodeProps<Node<McpToolsetData>>) {
  return (
    <BaseNode kind="McpToolset" name={data.name} selected={selected}>
      <span>{data.command}</span>
      {data.tool_filter && <span>filter: {data.tool_filter}</span>}
    </BaseNode>
  )
}
