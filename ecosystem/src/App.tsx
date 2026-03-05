import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ReactFlow,
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  type OnConnect,
  type Node,
  type Edge,
  type NodeTypes,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './App.css'

import { defaultData, kindColor, edgeStyle } from './types/agent'
import type { AgentKind, NodeData } from './types/agent'

import LlmAgentNode from './nodes/LlmAgentNode'
import SequentialAgentNode from './nodes/SequentialAgentNode'
import ParallelAgentNode from './nodes/ParallelAgentNode'
import LoopAgentNode from './nodes/LoopAgentNode'
import ToolNode from './nodes/ToolNode'
import McpToolsetNode from './nodes/McpToolsetNode'
import ObservationSetNode from './nodes/ObservationSetNode'

import NodePalette from './components/NodePalette'
import PropertyPanel from './components/PropertyPanel'
import Toolbar from './components/Toolbar'

const STORAGE_KEY = 'adk-designer-state'

const nodeTypes: NodeTypes = {
  LlmAgent: LlmAgentNode,
  SequentialAgent: SequentialAgentNode,
  ParallelAgent: ParallelAgentNode,
  LoopAgent: LoopAgentNode,
  Tool: ToolNode,
  McpToolset: McpToolsetNode,
  ObservationSet: ObservationSetNode,
}

const INITIAL_NODES: Node<NodeData>[] = []
const INITIAL_EDGES: Edge[] = []

// ObservationSet nodes need an initial size
const OBS_SET_DEFAULTS = { style: { width: 320, height: 220 }, zIndex: -1 }

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeData>>(INITIAL_NODES)
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const reactFlowWrapper = useRef<HTMLDivElement>(null)
  const [reactFlowInstance, setReactFlowInstance] = useState<ReturnType<typeof import('@xyflow/react').useReactFlow> | null>(null)
  const idCounter = useRef(1)
  // Always-current snapshot of nodes for use in onConnect callback
  const nodesRef = useRef<Node<NodeData>[]>([])
  useEffect(() => { nodesRef.current = nodes }, [nodes])

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null

  // ── Connections ────────────────────────────────────────────────────────────
  const onConnect: OnConnect = useCallback(
    (connection) => {
      const sourceKind = nodesRef.current.find((n) => n.id === connection.source)?.data.kind
      const targetKind = nodesRef.current.find((n) => n.id === connection.target)?.data.kind
      const style = edgeStyle(sourceKind, targetKind)

      const edge: Edge = {
        ...connection,
        id: `e-${connection.source}-${connection.target}-${Date.now()}`,
        data: { kind: style.kind },
        style: {
          stroke: style.color,
          strokeDasharray: style.dashed ? '6,4' : undefined,
        },
        animated: style.animated,
        markerEnd: { type: 'arrowclosed' as const, color: style.color },
      }
      setEdges((eds) => addEdge(edge, eds))
    },
    [setEdges],
  )

  // ── Drag-and-drop from palette ─────────────────────────────────────────────
  function onDragStart(kind: AgentKind, event: React.DragEvent) {
    event.dataTransfer.setData('nodeKind', kind)
    event.dataTransfer.effectAllowed = 'move'
  }

  function onDrop(event: React.DragEvent) {
    event.preventDefault()
    const kind = event.dataTransfer.getData('nodeKind') as AgentKind
    if (!kind || !reactFlowWrapper.current || !reactFlowInstance) return

    const bounds = reactFlowWrapper.current.getBoundingClientRect()
    const position = (reactFlowInstance as { screenToFlowPosition: (p: { x: number; y: number }) => { x: number; y: number } }).screenToFlowPosition({
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
    })

    const id = `${kind}-${idCounter.current++}`
    const extras = kind === 'ObservationSet' ? OBS_SET_DEFAULTS : {}
    const newNode: Node<NodeData> = {
      id,
      type: kind,
      position,
      data: defaultData(kind),
      ...extras,
    }
    setNodes((nds) => nds.concat(newNode))
    setSelectedNodeId(id)
  }

  function onDragOver(event: React.DragEvent) {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }

  // ── Selection ──────────────────────────────────────────────────────────────
  function onNodeClick(_: React.MouseEvent, node: Node<NodeData>) {
    setSelectedNodeId(node.id)
  }

  function onPaneClick() {
    setSelectedNodeId(null)
  }

  // ── Property panel updates ─────────────────────────────────────────────────
  function handleNodeChange(id: string, patch: Partial<NodeData>) {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, ...patch } as NodeData } : n,
      ),
    )
  }

  function handleNodeDelete(id: string) {
    setNodes((nds) => nds.filter((n) => n.id !== id))
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id))
    setSelectedNodeId(null)
  }

  // ── Toolbar actions ────────────────────────────────────────────────────────
  function handleNew() {
    if (nodes.length > 0 && !confirm('Clear the canvas? Unsaved changes will be lost.')) return
    setNodes([])
    setEdges([])
    setSelectedNodeId(null)
  }

  function handleSave() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ nodes, edges }))
    alert('Saved to browser storage.')
  }

  function handleLoad() {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) { alert('No saved design found.'); return }
    try {
      const { nodes: n, edges: e } = JSON.parse(raw)
      setNodes(n)
      setEdges(e)
      setSelectedNodeId(null)
    } catch {
      alert('Failed to load: saved data is corrupted.')
    }
  }

  return (
    <div className="app">
      <Toolbar nodes={nodes} edges={edges} onNew={handleNew} onSave={handleSave} onLoad={handleLoad} />

      <div className="app-body">
        <NodePalette onDragStart={onDragStart} />

        <div className="canvas-wrapper" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            onInit={(inst) => setReactFlowInstance(inst as never)}
            connectionMode={ConnectionMode.Loose}
            fitView
            deleteKeyCode="Delete"
            colorMode="dark"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1.5}
              color="#2d3148"
            />
            <Controls />
            <MiniMap
              nodeColor={(n) => {
                const d = n.data as NodeData
                return d.kind === 'ObservationSet' ? (d.color as string) : kindColor(d.kind)
              }}
              style={{ background: '#12141f', border: '1px solid #2d3148' }}
            />
          </ReactFlow>
        </div>

        <PropertyPanel
          node={selectedNode}
          onChange={handleNodeChange}
          onDelete={handleNodeDelete}
        />
      </div>
    </div>
  )
}
