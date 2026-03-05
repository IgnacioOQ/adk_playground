import type { NodeProps } from '@xyflow/react'
import type { Node } from '@xyflow/react'
import type { ToolData } from '../types/agent'
import BaseNode from './BaseNode'

export default function ToolNode({ data, selected }: NodeProps<Node<ToolData>>) {
  return (
    <BaseNode kind="Tool" name={data.name} selected={selected}>
      {data.description && <span>{data.description}</span>}
    </BaseNode>
  )
}
