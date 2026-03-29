import { useRef } from 'react'
import type { Node, Edge } from '@xyflow/react'
import type { NodeData } from '../types/agent'
import { generatePythonCode, type PresetMeta } from '../utils/codeGenerator'
import './Toolbar.css'

interface ToolbarProps {
  nodes: Node<NodeData>[]
  edges: Edge[]
  presetMeta: PresetMeta | null
  selectMode: boolean
  onSelectModeToggle: () => void
  onNew: () => void
  onSave: () => void
  onLoad: () => void
  onLoadFile: (nodes: Node<NodeData>[], edges: Edge[], meta: PresetMeta) => void
}

export default function Toolbar({ nodes, edges, presetMeta, selectMode, onSelectModeToggle, onNew, onSave, onLoad, onLoadFile }: ToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target?.result as string)
        if (!json.nodes || !json.edges) throw new Error('Missing nodes or edges')
        onLoadFile(json.nodes, json.edges, json._meta ?? { name: file.name.replace('.json', '') })
      } catch {
        alert('Failed to load preset: invalid JSON format.')
      }
    }
    reader.readAsText(file)
    event.target.value = ''
  }

  function handleExportPreset() {
    const meta: PresetMeta = presetMeta ?? {
      name: 'untitled',
      description: '',
      created: new Date().toISOString().slice(0, 10),
    }
    const preset = { _meta: meta, nodes, edges }
    const blob = new Blob([JSON.stringify(preset, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${meta.name.toLowerCase().replace(/\s+/g, '_')}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleExport() {
    const code = generatePythonCode(nodes, edges, presetMeta)
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
        <button
          className={`toolbar-btn${selectMode ? ' toolbar-btn-active' : ''}`}
          onClick={onSelectModeToggle}
          title={selectMode ? 'Switch to Pan mode (drag canvas to pan)' : 'Switch to Select mode (drag canvas to select area)'}
        >
          {selectMode ? '⬚ Select' : '✥ Pan'}
        </button>
        <div style={{ width: 1, background: '#2d3148', margin: '6px 0' }} />
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
        <button className="toolbar-btn" onClick={handleExportPreset} title="Export canvas as preset JSON">
          Export Preset
        </button>
        <button className="toolbar-btn toolbar-btn-primary" onClick={handleExport} title="Export agent.py">
          Export Python
        </button>
      </div>
    </header>
  )
}
