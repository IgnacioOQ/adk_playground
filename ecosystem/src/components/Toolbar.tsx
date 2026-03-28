import { useRef } from 'react'
import type { Node, Edge } from '@xyflow/react'
import type { NodeData } from '../types/agent'
import { generatePythonCode } from '../utils/codeGenerator'
import './Toolbar.css'

interface ToolbarProps {
  nodes: Node<NodeData>[]
  edges: Edge[]
  onNew: () => void
  onSave: () => void
  onLoad: () => void
  onLoadFile: (nodes: Node<NodeData>[], edges: Edge[]) => void
}

export default function Toolbar({ nodes, edges, onNew, onSave, onLoad, onLoadFile }: ToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target?.result as string)
        if (!json.nodes || !json.edges) throw new Error('Missing nodes or edges')
        onLoadFile(json.nodes, json.edges)
      } catch {
        alert('Failed to load preset: invalid JSON format.')
      }
    }
    reader.readAsText(file)
    // Reset so the same file can be re-loaded
    event.target.value = ''
  }

  function handleExport() {
    const code = generatePythonCode(nodes, edges)
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'agent.py'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <header className="toolbar">
      <div className="toolbar-brand">
        <span className="toolbar-logo">⬡</span>
        <span className="toolbar-title">ADK Agent Designer</span>
      </div>
      <div className="toolbar-actions">
        <button className="toolbar-btn" onClick={onNew} title="Clear canvas">
          New
        </button>
        <button className="toolbar-btn" onClick={onSave} title="Save to browser storage">
          Save
        </button>
        <button className="toolbar-btn" onClick={onLoad} title="Load from browser storage">
          Load
        </button>
        <button className="toolbar-btn" onClick={() => fileInputRef.current?.click()} title="Load a preset JSON file">
          Load File
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <button className="toolbar-btn toolbar-btn-primary" onClick={handleExport} title="Export agent.py">
          Export Python
        </button>
      </div>
    </header>
  )
}
