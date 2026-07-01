import React, { useState, useEffect, useRef } from 'react'
import useSWR from 'swr'
import {
  Cpu,
  Layers,
  Link as LinkIcon,
  FileText,
  Calendar,
  GitBranch,
  Wrench,
  Play,
  Pause,
  SkipForward,
  SkipBack,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Move,
  Map,
  Save,
  FolderOpen,
  AlertTriangle,
  Trash2,
  Plus,
  X,
  CheckCircle,
  HelpCircle,
  Clock,
  Compass,
  Check
} from 'lucide-react'

// Constants
const API_BASE = process.env.NEXT_PUBLIC_API_HOST
  ? `https://${process.env.NEXT_PUBLIC_API_HOST}/api/v1`
  : '/api/v1'

const fetcher = (url: string) => fetch(url).then((r) => (r.ok ? r.json() : null))

// Types
interface NodeData {
  name: string
  [key: string]: any
}

interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: NodeData
}

interface WorkflowEdge {
  id: string
  source: string
  target: string
  source_handle?: string | null
  target_handle?: string | null
}

interface Workflow {
  id: string
  name: string
  description?: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  created_at?: string
  updated_at?: string
}

interface SimulationStep {
  step_index: number
  node_id: string
  node_name: string
  node_type: string
  status: 'success' | 'failure' | 'running' | 'pending'
  logs: string[]
  outputs: any
  errors: string[]
  duration_ms: number
}

// Available node type configurations
const NODE_TYPES = [
  { type: 'agent', label: 'Agent Node', icon: Cpu, color: '#3b82f6', defaultData: { name: 'New Agent', framework: 'crewai', agentName: 'Researcher', systemPrompt: 'You are a helpful assistant.' } },
  { type: 'llm', label: 'LLM Node', icon: Compass, color: '#a855f7', defaultData: { name: 'LLM Synthesizer', model: 'claude-3-5-sonnet', temperature: 0.3, systemPrompt: 'Summarize the input data.' } },
  { type: 'memory', label: 'Memory Node', icon: Layers, color: '#10b981', defaultData: { name: 'Memory Store', memoryKey: 'chat_history', mode: 'read', storageType: 'semantic' } },
  { type: 'http', label: 'HTTP Request', icon: LinkIcon, color: '#f59e0b', defaultData: { name: 'API Call', url: 'https://api.example.com/v1/data', method: 'GET', headers: '{}', body: '' } },
  { type: 'file', label: 'File Processing', icon: FileText, color: '#6366f1', defaultData: { name: 'File Operation', filePath: '/workspace/input.txt', action: 'read' } },
  { type: 'scheduler', label: 'Scheduler', icon: Calendar, color: '#ec4899', defaultData: { name: 'Cron Trigger', cron: '0 9 * * 1-5', triggerEvent: 'scheduled_report' } },
  { type: 'conditional', label: 'Conditional Logic', icon: GitBranch, color: '#f97316', defaultData: { name: 'If/Else Route', property: 'status', operator: 'eq', value: 'success' } },
  { type: 'custom-tool', label: 'Custom Tool', icon: Wrench, color: '#06b6d4', defaultData: { name: 'Custom Sandbox Script', toolName: 'custom_executor', arguments: '{}' } }
]

export default function WorkflowBuilder() {
  // SWR for loading workflows from backend
  const { data: workflowsList, mutate: mutateWorkflows } = useSWR<Workflow[]>(`${API_BASE}/workflows`, fetcher)

  // Canvas State
  const [nodes, setNodes] = useState<WorkflowNode[]>([])
  const [edges, setEdges] = useState<WorkflowEdge[]>([])
  const [workflowName, setWorkflowName] = useState('My Automation Pipeline')
  const [workflowDesc, setWorkflowDesc] = useState('Describe your pipeline goals and structure...')
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null)
  
  // Selection & UI State
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [isTemplatesOpen, setIsTemplatesOpen] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  
  // Zoom & Pan
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })
  
  // Drag node state (from palette to canvas)
  const [draggedNodeType, setDraggedNodeType] = useState<string | null>(null)
  const [isDraggingNodeOnCanvas, setIsDraggingNodeOnCanvas] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  
  // Connection line dragging state
  const [connectingFrom, setConnectingFrom] = useState<{ nodeId: string; handle: string } | null>(null)
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 })

  // Simulation State
  const [simulationSteps, setSimulationSteps] = useState<SimulationStep[]>([])
  const [simulationStatus, setSimulationStatus] = useState<'idle' | 'running' | 'paused' | 'success' | 'failure'>('idle')
  const [currentStepIndex, setCurrentStepIndex] = useState(-1)
  const [simLogs, setSimLogs] = useState<string[]>([])
  
  // Refs
  const canvasRef = useRef<HTMLDivElement>(null)

  // Load first workflow or template on mount
  useEffect(() => {
    if (workflowsList && workflowsList.length > 0 && !selectedWorkflowId) {
      loadWorkflow(workflowsList[0])
    }
  }, [workflowsList])

  // Real-time Validation Warning checks
  const getValidationWarnings = () => {
    const warnings: string[] = []
    
    // Check for disconnected nodes (no edges attached)
    nodes.forEach(node => {
      const isConnected = edges.some(e => e.source === node.id || e.target === node.id)
      if (!isConnected && nodes.length > 1) {
        warnings.push(`Node "${node.data.name}" is isolated and not connected to any other node.`)
      }
      
      // Node specific field validation warnings
      if (node.type === 'http' && !node.data.url) {
        warnings.push(`Node "${node.data.name}" has an empty HTTP URL.`)
      }
      if (node.type === 'file' && !node.data.filePath) {
        warnings.push(`Node "${node.data.name}" has an empty File Path.`)
      }
    })
    return warnings
  }

  // Load a workflow template or saved workflow
  const loadWorkflow = (wf: Workflow) => {
    setNodes(wf.nodes || [])
    setEdges(wf.edges || [])
    setWorkflowName(wf.name)
    setWorkflowDesc(wf.description || '')
    setSelectedWorkflowId(wf.id)
    setSelectedNodeId(null)
    setSimulationStatus('idle')
    setSimulationSteps([])
    setSimLogs(['System: Workflow loaded successfully. Ready to simulate.'])
    setCurrentStepIndex(-1)
  }

  // Create a new blank workflow
  const handleNewWorkflow = () => {
    const newId = `wf-${Math.random().toString(36).substr(2, 9)}`
    setNodes([
      { id: 'node-1', type: 'scheduler', position: { x: 150, y: 220 }, data: { name: 'Schedule Trigger', cron: '0 9 * * 1-5' } }
    ])
    setEdges([])
    setWorkflowName('Untitled Workflow')
    setWorkflowDesc('A brand new automation pipeline')
    setSelectedWorkflowId(newId)
    setSelectedNodeId('node-1')
    setSimulationStatus('idle')
    setSimulationSteps([])
    setSimLogs(['System: New workflow created.'])
    setCurrentStepIndex(-1)
  }

  // Save workflow to backend
  const handleSaveWorkflow = async () => {
    const id = selectedWorkflowId || `wf-${Math.random().toString(36).substr(2, 9)}`
    if (!selectedWorkflowId) {
      setSelectedWorkflowId(id)
    }

    const payload: Workflow = {
      id,
      name: workflowName,
      description: workflowDesc,
      nodes,
      edges
    }

    try {
      const res = await fetch(`${API_BASE}/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (res.ok) {
        setSaveSuccess(true)
        setTimeout(() => setSaveSuccess(false), 3000)
        if (mutateWorkflows) mutateWorkflows()
      }
    } catch (err) {
      console.error('Failed to save workflow', err)
    }
  }

  // Delete a workflow
  const handleDeleteWorkflow = async (id: string) => {
    if (confirm('Are you sure you want to delete this workflow?')) {
      try {
        const res = await fetch(`${API_BASE}/workflows/${id}`, {
          method: 'DELETE'
        })
        if (res.ok) {
          if (mutateWorkflows) mutateWorkflows()
          if (selectedWorkflowId === id) {
            setSelectedWorkflowId(null)
          }
        }
      } catch (err) {
        console.error('Failed to delete workflow', err)
      }
    }
  }

  // Zoom controls
  const zoomIn = () => setZoom(prev => Math.min(prev + 0.1, 1.8))
  const zoomOut = () => setZoom(prev => Math.max(prev - 0.1, 0.5))
  const zoomReset = () => {
    setZoom(1.0)
    setPan({ x: 0, y: 0 })
  }

  // Pan controls via mouse drag on grid background
  const handleMouseDownBg = (e: React.MouseEvent) => {
    if (e.button !== 0) return // Left click only
    setIsPanning(true)
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMoveCanvas = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      })
    } else if (isDraggingNodeOnCanvas && dragOffset) {
      // Calculate scaled coords
      const rect = canvasRef.current?.getBoundingClientRect()
      if (rect) {
        const clientX = e.clientX - rect.left - pan.x
        const clientY = e.clientY - rect.top - pan.y
        setNodes(prev =>
          prev.map(n =>
            n.id === isDraggingNodeOnCanvas
              ? { ...n, position: { x: Math.round(clientX / zoom - dragOffset.x), y: Math.round(clientY / zoom - dragOffset.y) } }
              : n
          )
        )
      }
    } else if (connectingFrom) {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (rect) {
        setCursorPos({
          x: (e.clientX - rect.left - pan.x) / zoom,
          y: (e.clientY - rect.top - pan.y) / zoom
        })
      }
    }
  }

  const handleMouseUpCanvas = () => {
    setIsPanning(false)
    setIsDraggingNodeOnCanvas(null)
    if (connectingFrom) {
      setConnectingFrom(null)
    }
  }

  // Node Dragging Start
  const handleMouseDownNode = (e: React.MouseEvent, node: WorkflowNode) => {
    e.stopPropagation()
    setSelectedNodeId(node.id)
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    // Capture click offset inside the node itself to prevent jumping
    setDragOffset({
      x: (e.clientX - rect.left) / zoom,
      y: (e.clientY - rect.top) / zoom
    })
    setIsDraggingNodeOnCanvas(node.id)
  }

  // Drag and Drop from library palette
  const handleDragStartFromPalette = (type: string) => {
    setDraggedNodeType(type)
  }

  const handleDropOnCanvas = (e: React.DragEvent) => {
    e.preventDefault()
    if (!draggedNodeType) return
    const rect = canvasRef.current?.getBoundingClientRect()
    if (rect) {
      const canvasX = (e.clientX - rect.left - pan.x) / zoom
      const canvasY = (e.clientY - rect.top - pan.y) / zoom
      
      const config = NODE_TYPES.find(t => t.type === draggedNodeType)
      const newNode: WorkflowNode = {
        id: `node-${Math.random().toString(36).substr(2, 9)}`,
        type: draggedNodeType,
        position: { x: Math.round(canvasX - 100), y: Math.round(canvasY - 40) },
        data: JSON.parse(JSON.stringify(config?.defaultData || { name: 'New Node' }))
      }
      setNodes(prev => [...prev, newNode])
      setSelectedNodeId(newNode.id)
    }
    setDraggedNodeType(null)
  }

  // Connection handling
  const handleStartConnection = (e: React.MouseEvent, nodeId: string, handle: string) => {
    e.stopPropagation()
    const rect = canvasRef.current?.getBoundingClientRect()
    if (rect) {
      setConnectingFrom({ nodeId, handle })
      setCursorPos({
        x: (e.clientX - rect.left - pan.x) / zoom,
        y: (e.clientY - rect.top - pan.y) / zoom
      })
    }
  }

  const handleEndConnection = (e: React.MouseEvent, targetNodeId: string) => {
    e.stopPropagation()
    if (connectingFrom && connectingFrom.nodeId !== targetNodeId) {
      // Create new edge
      const edgeId = `edge-${Math.random().toString(36).substr(2, 9)}`
      const newEdge: WorkflowEdge = {
        id: edgeId,
        source: connectingFrom.nodeId,
        target: targetNodeId,
        source_handle: connectingFrom.handle,
        target_handle: 'input'
      }
      // Check if connection already exists to prevent duplicates
      const exists = edges.some(edge => edge.source === newEdge.source && edge.target === newEdge.target)
      if (!exists) {
        setEdges(prev => [...prev, newEdge])
      }
    }
    setConnectingFrom(null)
  }

  // Node Deletion
  const deleteNode = (nodeId: string) => {
    setNodes(prev => prev.filter(n => n.id !== nodeId))
    setEdges(prev => prev.filter(e => e.source !== nodeId && e.target !== nodeId))
    if (selectedNodeId === nodeId) setSelectedNodeId(null)
  }

  // Config Update
  const updateNodeData = (nodeId: string, key: string, value: any) => {
    setNodes(prev =>
      prev.map(n =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, [key]: value } }
          : n
      )
    )
  }

  // Compute coordinate centers for drawing SVGs
  const getNodeCoordinates = (nodeId: string, handleType: string) => {
    const node = nodes.find(n => n.id === nodeId)
    if (!node) return { x: 0, y: 0 }
    
    // Width and height approximation for node positions
    const nodeWidth = 220
    const nodeHeight = 80
    
    if (handleType === 'input') {
      return { x: node.position.x, y: node.position.y + nodeHeight / 2 }
    } else if (handleType === 'true') {
      return { x: node.position.x + nodeWidth, y: node.position.y + nodeHeight / 3 }
    } else if (handleType === 'false') {
      return { x: node.position.x + nodeWidth, y: node.position.y + (nodeHeight / 3) * 2 }
    } else {
      return { x: node.position.x + nodeWidth, y: node.position.y + nodeHeight / 2 }
    }
  }

  // Simulation Runner Controllers
  const triggerSimulation = async () => {
    if (!selectedWorkflowId) return
    setSimulationStatus('running')
    setSimLogs(prev => [...prev, 'System: Launching pipeline execution simulation...'])
    
    try {
      const res = await fetch(`${API_BASE}/workflows/${selectedWorkflowId}/run`, {
        method: 'POST'
      })
      if (res.ok) {
        const simResult = await res.json()
        setSimulationSteps(simResult.steps || [])
        if (simResult.steps && simResult.steps.length > 0) {
          setCurrentStepIndex(0)
          setSimLogs(prev => [
            ...prev,
            ...simResult.steps[0].logs.map((l: string) => `[Node: ${simResult.steps[0].node_name}] ${l}`)
          ])
        } else {
          setSimulationStatus('success')
        }
      } else {
        setSimulationStatus('failure')
        setSimLogs(prev => [...prev, 'CRITICAL: Simulation failed to bootstrap on the server backend.'])
      }
    } catch (e) {
      setSimulationStatus('failure')
      setSimLogs(prev => [...prev, 'CRITICAL: Offline mode — simulation error.'])
    }
  }

  // Step controls
  const stepForward = () => {
    if (currentStepIndex < simulationSteps.length - 1) {
      const nextIndex = currentStepIndex + 1
      setCurrentStepIndex(nextIndex)
      const nextStep = simulationSteps[nextIndex]
      setSimLogs(prev => [
        ...prev,
        ...nextStep.logs.map((l: string) => `[Node: ${nextStep.node_name}] ${l}`)
      ])
      if (nextStep.status === 'failure') {
        setSimulationStatus('failure')
      } else if (nextIndex === simulationSteps.length - 1) {
        setSimulationStatus('success')
      }
    }
  }

  const stepBackward = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1)
      setSimLogs(prev => [...prev, 'System: Reverting execution step back.'])
      setSimulationStatus('running')
    }
  }

  const resetSimulation = () => {
    setSimulationStatus('idle')
    setCurrentStepIndex(-1)
    setSimulationSteps([])
    setSimLogs(['System: Simulation reset. Ready to launch.'])
  }

  // Current active node in simulation
  const activeNodeId = currentStepIndex >= 0 && currentStepIndex < simulationSteps.length
    ? simulationSteps[currentStepIndex].node_id
    : null

  // Check state of nodes in simulation
  const getNodeSimulationStatus = (nodeId: string) => {
    if (simulationStatus === 'idle') return null
    
    // Find if node has completed or is active
    const step = simulationSteps.find(s => s.node_id === nodeId)
    if (!step) return 'pending'
    
    const stepIdx = simulationSteps.indexOf(step)
    if (stepIdx === currentStepIndex) return 'running'
    if (stepIdx < currentStepIndex) return step.status // success or failure
    return 'pending'
  }

  return (
    <div className="flex flex-col h-screen bg-[#070913] text-[#e2e8f0] font-sans overflow-hidden">
      {/* Top Header Navigation */}
      <header className="flex items-center justify-between px-6 py-3.5 border-b border-white/10 bg-zinc-950/80 backdrop-blur z-30">
        <div className="flex items-center gap-3">
          <Cpu className="text-blue-500 animate-pulse" size={24} />
          <div>
            <div className="flex items-center gap-2">
              <input
                value={workflowName}
                onChange={e => setWorkflowName(e.target.value)}
                className="bg-transparent text-lg font-semibold text-white border-b border-transparent hover:border-white/20 focus:border-blue-500 focus:outline-none px-1"
                placeholder="Workflow Name"
              />
              <span className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded font-mono">
                PIPELINE
              </span>
            </div>
            <input
              value={workflowDesc}
              onChange={e => setWorkflowDesc(e.target.value)}
              className="bg-transparent text-xs text-zinc-400 focus:outline-none w-80 truncate"
              placeholder="Add description..."
            />
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsTemplatesOpen(!isTemplatesOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 bg-white/5 text-sm text-zinc-300 hover:bg-white/10 transition"
          >
            <FolderOpen size={14} />
            Workflows
          </button>
          
          <button
            onClick={handleSaveWorkflow}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition shadow-lg shadow-blue-900/20"
          >
            <Save size={14} />
            Save Pipeline
          </button>

          <a
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-sm text-zinc-400 hover:text-white transition"
          >
            Dashboard
          </a>
        </div>
      </header>

      {/* Main Builder Pane */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Templates Slide Panel Overlay */}
        {isTemplatesOpen && (
          <div className="absolute left-0 top-0 bottom-0 w-80 bg-zinc-950/95 border-r border-white/10 z-40 p-4 shadow-2xl animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">Pipeline Templates</h3>
              <button onClick={() => setIsTemplatesOpen(false)} className="text-zinc-500 hover:text-white">
                <X size={16} />
              </button>
            </div>
            
            <div className="space-y-3 max-h-[75vh] overflow-y-auto pr-1">
              <div className="p-3 rounded-xl bg-blue-500/5 border border-blue-500/20 mb-4">
                <button
                  onClick={handleNewWorkflow}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition"
                >
                  <Plus size={14} /> New Blank Pipeline
                </button>
              </div>

              {workflowsList?.map(wf => (
                <div key={wf.id} className="p-3.5 rounded-xl border border-white/5 bg-white/5 hover:border-blue-500/40 transition">
                  <div className="flex justify-between items-start">
                    <h4 className="font-semibold text-sm text-zinc-200">{wf.name}</h4>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteWorkflow(wf.id) }}
                      className="text-zinc-600 hover:text-red-400 p-0.5 rounded"
                      title="Delete Pipeline"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-1 line-clamp-2">{wf.description}</p>
                  <button
                    onClick={() => { loadWorkflow(wf); setIsTemplatesOpen(false) }}
                    className="mt-3 text-[11px] text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
                  >
                    Load Workflow &rarr;
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Left Toolbar: Node Palette & Templates list */}
        <aside className="w-64 border-r border-white/10 bg-zinc-950/60 p-4 flex flex-col justify-between select-none shrink-0 z-20">
          <div>
            <div className="mb-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-2">Drag Nodes to Canvas</h3>
              <p className="text-[10px] text-zinc-500 leading-normal">Drag components from this sidebar to construct your agent automation flow.</p>
            </div>

            <div className="space-y-2 overflow-y-auto max-h-[60vh] pr-1">
              {NODE_TYPES.map(n => {
                const Icon = n.icon
                return (
                  <div
                    key={n.type}
                    draggable
                    onDragStart={() => handleDragStartFromPalette(n.type)}
                    className="flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-zinc-900/60 hover:bg-zinc-900 hover:border-white/20 transition cursor-grab active:cursor-grabbing group"
                  >
                    <div className="p-2 rounded-lg" style={{ backgroundColor: `${n.color}15`, color: n.color }}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-zinc-200 group-hover:text-white transition">{n.label}</div>
                      <div className="text-[9px] text-zinc-500 mt-0.5 uppercase tracking-wider">{n.type}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Canvas Navigation Tools */}
          <div className="border-t border-white/10 pt-4 mt-4">
            <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3">Viewport Controls</h4>
            <div className="flex gap-2">
              <button onClick={zoomIn} className="flex-1 py-2 bg-zinc-900 hover:bg-zinc-800 rounded-lg border border-white/10 flex justify-center text-zinc-400 hover:text-white transition" title="Zoom In">
                <ZoomIn size={16} />
              </button>
              <button onClick={zoomOut} className="flex-1 py-2 bg-zinc-900 hover:bg-zinc-800 rounded-lg border border-white/10 flex justify-center text-zinc-400 hover:text-white transition" title="Zoom Out">
                <ZoomOut size={16} />
              </button>
              <button onClick={zoomReset} className="flex-1 py-2 bg-zinc-900 hover:bg-zinc-800 rounded-lg border border-white/10 flex justify-center text-zinc-400 hover:text-white transition text-xs font-semibold" title="Reset view">
                100%
              </button>
            </div>
            <div className="text-[9px] text-zinc-500 mt-2 text-center">
              Drag background to pan. Mouse wheel to zoom.
            </div>
          </div>
        </aside>

        {/* Center: Dynamic Workflow Canvas Grid */}
        <main
          ref={canvasRef}
          onDragOver={e => e.preventDefault()}
          onDrop={handleDropOnCanvas}
          onMouseMove={handleMouseMoveCanvas}
          onMouseUp={handleMouseUpCanvas}
          onMouseDown={handleMouseDownBg}
          className="flex-1 h-full relative overflow-hidden bg-[#070913]"
          style={{ cursor: isPanning ? 'grabbing' : connectingFrom ? 'crosshair' : 'default' }}
        >
          {/* Subtle Canvas SVG Grid lines */}
          <div
            className="absolute inset-0 transition-transform duration-75 origin-top-left pointer-events-none"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px)',
              backgroundSize: '24px 24px'
            }}
          />

          {/* SVG Connection Layer */}
          <svg
            className="absolute inset-0 pointer-events-none origin-top-left z-10"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
          >
            {/* Draw permanent edges */}
            {edges.map(edge => {
              const start = getNodeCoordinates(edge.source, edge.source_handle || 'output')
              const end = getNodeCoordinates(edge.target, 'input')
              
              // Compute smooth bezier curve
              const dx = Math.abs(end.x - start.x) * 0.5
              const path = `M ${start.x} ${start.y} C ${start.x + dx} ${start.y}, ${end.x - dx} ${end.y}, ${end.x} ${end.y}`
              
              const isSimulatingActive = activeNodeId === edge.source
              
              return (
                <g key={edge.id} className="pointer-events-auto">
                  <path
                    d={path}
                    fill="none"
                    stroke={isSimulatingActive ? '#3b82f6' : '#ffffff20'}
                    strokeWidth="3"
                    className={isSimulatingActive ? 'animate-pulse' : ''}
                    style={{ transition: 'stroke 0.2s' }}
                  />
                  {isSimulatingActive && (
                    <circle r="4" fill="#60a5fa">
                      <animateMotion dur="2s" repeatCount="indefinite" path={path} />
                    </circle>
                  )}
                  {/* Small delete click target for edge */}
                  <path
                    d={path}
                    fill="none"
                    stroke="transparent"
                    strokeWidth="10"
                    className="cursor-pointer hover:stroke-red-500/30 transition"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm('Delete this connection?')) {
                        setEdges(prev => prev.filter(edgeItem => edgeItem.id !== edge.id))
                      }
                    }}
                  />
                </g>
              )
            })}

            {/* Draw temporary dragging edge */}
            {connectingFrom && (
              <path
                d={`M ${getNodeCoordinates(connectingFrom.nodeId, connectingFrom.handle).x} ${getNodeCoordinates(connectingFrom.nodeId, connectingFrom.handle).y} C ${getNodeCoordinates(connectingFrom.nodeId, connectingFrom.handle).x + Math.abs(cursorPos.x - getNodeCoordinates(connectingFrom.nodeId, connectingFrom.handle).x) * 0.5} ${getNodeCoordinates(connectingFrom.nodeId, connectingFrom.handle).y}, ${cursorPos.x - Math.abs(cursorPos.x - getNodeCoordinates(connectingFrom.nodeId, connectingFrom.handle).x) * 0.5} ${cursorPos.y}, ${cursorPos.x} ${cursorPos.y}`}
                fill="none"
                stroke="#60a5fa"
                strokeWidth="2"
                strokeDasharray="4 4"
              />
            )}
          </svg>

          {/* HTML Nodes Layer */}
          <div
            className="absolute inset-0 origin-top-left transition-transform duration-75 z-20"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
          >
            {nodes.map(node => {
              const config = NODE_TYPES.find(t => t.type === node.type)
              const Icon = config?.icon || HelpCircle
              const isSelected = selectedNodeId === node.id
              const simStatus = getNodeSimulationStatus(node.id)
              
              // Get style variables based on simulation status
              let borderColor = 'border-white/10'
              let shadowStyle = ''
              if (isSelected) {
                borderColor = 'border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.3)]'
              } else if (simStatus === 'running') {
                borderColor = 'border-amber-400'
                shadowStyle = 'shadow-[0_0_20px_rgba(245,158,11,0.5)] animate-pulse'
              } else if (simStatus === 'success') {
                borderColor = 'border-emerald-500'
                shadowStyle = 'shadow-[0_0_12px_rgba(16,185,129,0.2)]'
              } else if (simStatus === 'failure') {
                borderColor = 'border-red-500'
                shadowStyle = 'shadow-[0_0_20px_rgba(239,68,68,0.5)]'
              }

              return (
                <div
                  key={node.id}
                  onMouseDown={(e) => handleMouseDownNode(e, node)}
                  onMouseUp={(e) => handleEndConnection(e, node.id)}
                  style={{ left: node.position.x, top: node.position.y }}
                  className={`absolute w-56 bg-zinc-900/90 backdrop-blur rounded-xl border ${borderColor} ${shadowStyle} select-none transition-shadow p-3.5 flex flex-col justify-between cursor-move hover:bg-zinc-900 group`}
                >
                  {/* Top line details */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg" style={{ backgroundColor: `${config?.color}15`, color: config?.color }}>
                        <Icon size={14} />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-zinc-100 truncate">{node.data.name}</div>
                        <div className="text-[8px] text-zinc-500 uppercase tracking-wider">{node.type}</div>
                      </div>
                    </div>
                    {/* Node status indicators */}
                    <div className="flex items-center gap-1 shrink-0">
                      {simStatus === 'success' && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />}
                      {simStatus === 'running' && <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />}
                      {simStatus === 'failure' && <span className="h-1.5 w-1.5 rounded-full bg-red-500" />}
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteNode(node.id) }}
                        className="text-zinc-600 hover:text-red-400 p-0.5 rounded opacity-0 group-hover:opacity-100 transition"
                      >
                        <Trash2 size={10} />
                      </button>
                    </div>
                  </div>

                  {/* Handles */}
                  {/* Input handle (left side) */}
                  <div
                    className="absolute -left-1.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-zinc-950 border-2 border-white/20 hover:border-blue-500 transition cursor-crosshair z-30"
                    title="Input Port"
                  />
                  
                  {/* Output handles (right side) */}
                  {node.type === 'conditional' ? (
                    <>
                      {/* True handle */}
                      <div
                        onMouseDown={(e) => handleStartConnection(e, node.id, 'true')}
                        className="absolute -right-1.5 top-1/3 -translate-y-1/2 w-3 h-3 rounded-full bg-emerald-500 border-2 border-zinc-950 hover:bg-emerald-400 transition cursor-crosshair z-30"
                        title="True Branch"
                      />
                      {/* False handle */}
                      <div
                        onMouseDown={(e) => handleStartConnection(e, node.id, 'false')}
                        className="absolute -right-1.5 top-2/3 -translate-y-1/2 w-3 h-3 rounded-full bg-red-500 border-2 border-zinc-950 hover:bg-red-400 transition cursor-crosshair z-30"
                        title="False Branch"
                      />
                    </>
                  ) : (
                    <div
                      onMouseDown={(e) => handleStartConnection(e, node.id, 'output')}
                      className="absolute -right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-zinc-950 border-2 border-white/20 hover:border-blue-500 transition cursor-crosshair z-30"
                      title="Output Port"
                    />
                  )}
                </div>
              )
            })}
          </div>

          {/* Minimap Overlay (bottom-right of canvas) */}
          <div className="absolute right-4 bottom-4 w-40 h-28 bg-zinc-950/80 border border-white/10 rounded-xl p-2 pointer-events-none select-none z-30">
            <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase text-zinc-500 mb-1.5">
              <Map size={10} /> Minimap
            </div>
            <div className="relative w-full h-[72px] bg-black/40 rounded border border-white/5 overflow-hidden">
              {/* Scale mini-nodes into preview box */}
              {nodes.map(n => (
                <div
                  key={n.id}
                  className="absolute rounded bg-blue-500/40 border border-blue-500/60"
                  style={{
                    left: `${Math.min(100, Math.max(0, (n.position.x / 1400) * 100))}%`,
                    top: `${Math.min(100, Math.max(0, (n.position.y / 800) * 100))}%`,
                    width: '16px',
                    height: '8px'
                  }}
                />
              ))}
            </div>
          </div>
        </main>

        {/* Right Sidebar: Selected Node Editor Form */}
        <aside className="w-80 border-l border-white/10 bg-zinc-950/60 p-5 overflow-y-auto shrink-0 z-20">
          {selectedNodeId ? (
            (() => {
              const node = nodes.find(n => n.id === selectedNodeId)
              if (!node) return <div className="text-zinc-500 text-xs italic">Select a node to configure it.</div>
              const config = NODE_TYPES.find(t => t.type === node.type)
              return (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-zinc-200">Configure Node</h3>
                      <p className="text-[10px] text-zinc-500 uppercase tracking-wider">{node.type}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-white/5 text-zinc-400">
                      {config && <config.icon size={16} />}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Component Label</label>
                      <input
                        value={node.data.name}
                        onChange={e => updateNodeData(node.id, 'name', e.target.value)}
                        className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:border-blue-500 focus:outline-none"
                      />
                    </div>

                    {/* Agent Node Configs */}
                    {node.type === 'agent' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Framework Adapter</label>
                          <select
                            value={node.data.framework}
                            onChange={e => updateNodeData(node.id, 'framework', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          >
                            <option value="crewai">CrewAI</option>
                            <option value="langchain">LangChain</option>
                            <option value="claude_code">Claude Code</option>
                            <option value="custom">Custom Agent</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">System Instruction</label>
                          <textarea
                            value={node.data.systemPrompt}
                            onChange={e => updateNodeData(node.id, 'systemPrompt', e.target.value)}
                            className="w-full h-24 bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                      </>
                    )}

                    {/* LLM Node Configs */}
                    {node.type === 'llm' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Model Family</label>
                          <select
                            value={node.data.model}
                            onChange={e => updateNodeData(node.id, 'model', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          >
                            <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                            <option value="gpt-4o">GPT-4o</option>
                            <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Temperature</label>
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            max="1"
                            value={node.data.temperature}
                            onChange={e => updateNodeData(node.id, 'temperature', parseFloat(e.target.value))}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">System prompt</label>
                          <textarea
                            value={node.data.systemPrompt}
                            onChange={e => updateNodeData(node.id, 'systemPrompt', e.target.value)}
                            className="w-full h-24 bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                      </>
                    )}

                    {/* Memory Node Configs */}
                    {node.type === 'memory' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Memory Key</label>
                          <input
                            value={node.data.memoryKey}
                            onChange={e => updateNodeData(node.id, 'memoryKey', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Access Mode</label>
                          <select
                            value={node.data.mode}
                            onChange={e => updateNodeData(node.id, 'mode', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          >
                            <option value="read">Read Context</option>
                            <option value="write">Write Context</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Storage Medium</label>
                          <select
                            value={node.data.storageType}
                            onChange={e => updateNodeData(node.id, 'storageType', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          >
                            <option value="semantic">Semantic (Vector Store)</option>
                            <option value="episodic">Episodic (Trace Cache)</option>
                            <option value="procedural">Procedural (Rules)</option>
                          </select>
                        </div>
                      </>
                    )}

                    {/* HTTP Request Node Configs */}
                    {node.type === 'http' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Method</label>
                          <select
                            value={node.data.method}
                            onChange={e => updateNodeData(node.id, 'method', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          >
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                            <option value="PUT">PUT</option>
                            <option value="DELETE">DELETE</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">URL</label>
                          <input
                            value={node.data.url}
                            onChange={e => updateNodeData(node.id, 'url', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                      </>
                    )}

                    {/* File Node Configs */}
                    {node.type === 'file' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">File Path</label>
                          <input
                            value={node.data.filePath}
                            onChange={e => updateNodeData(node.id, 'filePath', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">FileSystem Action</label>
                          <select
                            value={node.data.action}
                            onChange={e => updateNodeData(node.id, 'action', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          >
                            <option value="read">Read File</option>
                            <option value="write">Write File</option>
                            <option value="delete">Delete File</option>
                          </select>
                        </div>
                      </>
                    )}

                    {/* Scheduler Node Configs */}
                    {node.type === 'scheduler' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Cron Pattern</label>
                          <input
                            value={node.data.cron}
                            onChange={e => updateNodeData(node.id, 'cron', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none font-mono"
                          />
                        </div>
                      </>
                    )}

                    {/* Conditional Logic Node Configs */}
                    {node.type === 'conditional' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Property name</label>
                          <input
                            value={node.data.property}
                            onChange={e => updateNodeData(node.id, 'property', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Operator</label>
                          <select
                            value={node.data.operator}
                            onChange={e => updateNodeData(node.id, 'operator', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          >
                            <option value="eq">Equals</option>
                            <option value="ne">Not Equal</option>
                            <option value="gt">Greater Than</option>
                          </select>
                        </div>
                      </>
                    )}

                    {/* Custom Tool Node Configs */}
                    {node.type === 'custom-tool' && (
                      <>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Tool Binding name</label>
                          <input
                            value={node.data.toolName}
                            onChange={e => updateNodeData(node.id, 'toolName', e.target.value)}
                            className="w-full bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-zinc-500 uppercase mb-1.5">Mock Inputs (JSON)</label>
                          <textarea
                            value={node.data.arguments}
                            onChange={e => updateNodeData(node.id, 'arguments', e.target.value)}
                            className="w-full h-24 bg-[#0a0c16] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none font-mono"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )
            })()
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Compass size={40} className="text-zinc-700 mb-2" />
              <h4 className="text-xs font-semibold text-zinc-400">Node Configuration</h4>
              <p className="text-[10px] text-zinc-500 mt-1 max-w-xs leading-normal">
                Click any component node on the grid workspace to edit its properties, prompts, and parameters.
              </p>
            </div>
          )}
        </aside>
      </div>

      {/* Bottom Panel: Interactive Simulation logs & controls */}
      <footer className="h-64 border-t border-white/10 bg-zinc-950/90 z-20 flex flex-col">
        {/* Simulation Control Board */}
        <div className="flex items-center justify-between px-6 py-2 border-b border-white/5 bg-zinc-950">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Simulation Control Board</span>
            {simulationStatus !== 'idle' && (
              <span className={`inline-flex items-center gap-1.5 text-[9px] font-semibold px-2 py-0.5 rounded-full ${
                simulationStatus === 'running' ? 'bg-amber-400/10 text-amber-400' :
                simulationStatus === 'success' ? 'bg-emerald-500/10 text-emerald-400' :
                'bg-red-500/10 text-red-400'
              }`}>
                {simulationStatus.toUpperCase()}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={stepBackward}
              disabled={currentStepIndex <= 0}
              className="p-1.5 hover:text-white text-zinc-500 disabled:opacity-30 disabled:hover:text-zinc-500 transition"
              title="Step Backward"
            >
              <SkipBack size={16} />
            </button>

            {simulationStatus === 'running' ? (
              <button
                onClick={() => setSimulationStatus('paused')}
                className="p-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition"
                title="Pause Simulation"
              >
                <Pause size={16} />
              </button>
            ) : (
              <button
                onClick={triggerSimulation}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition"
                title="Play Simulation"
              >
                <Play size={14} /> Run Simulation
              </button>
            )}

            <button
              onClick={stepForward}
              disabled={currentStepIndex >= simulationSteps.length - 1}
              className="p-1.5 hover:text-white text-zinc-500 disabled:opacity-30 disabled:hover:text-zinc-500 transition"
              title="Step Forward"
            >
              <SkipForward size={16} />
            </button>

            <div className="w-[1px] h-4 bg-white/10 mx-2" />

            <button
              onClick={resetSimulation}
              className="p-1.5 hover:text-red-400 text-zinc-500 transition"
              title="Reset Simulation"
            >
              <RotateCcw size={16} />
            </button>
          </div>

          <div className="flex items-center gap-2">
            {getValidationWarnings().length > 0 ? (
              <span className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full">
                <AlertTriangle size={12} />
                {getValidationWarnings().length} Warnings
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-2 py-0.5 rounded-full">
                <CheckCircle size={12} />
                Valid Graph
              </span>
            )}
          </div>
        </div>

        {/* Logs Stream & Details grid */}
        <div className="flex-1 grid grid-cols-3 overflow-hidden">
          {/* Logs stream (Cols 1 & 2) */}
          <div className="col-span-2 border-r border-white/5 flex flex-col overflow-hidden">
            <div className="flex justify-between items-center px-4 py-1.5 bg-black/20 text-[9px] font-bold text-zinc-500 uppercase tracking-wider">
              <span>Execution Logs Output</span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px] space-y-1.5 text-zinc-400 bg-[#04050a] select-text">
              {simLogs.map((log, i) => {
                let colorClass = 'text-zinc-400'
                if (log.startsWith('System:')) colorClass = 'text-blue-400 font-semibold'
                else if (log.startsWith('CRITICAL:')) colorClass = 'text-red-500 font-bold'
                else if (log.includes('success') || log.includes('OK')) colorClass = 'text-emerald-400'
                else if (log.includes('vulnerabilit') || log.includes('warning')) colorClass = 'text-amber-400'

                return (
                  <div key={i} className={colorClass}>
                    {log}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Step Inspector & Warnings (Col 3) */}
          <div className="flex flex-col overflow-hidden bg-zinc-950/40">
            <div className="px-4 py-1.5 bg-black/20 text-[9px] font-bold text-zinc-500 uppercase tracking-wider border-b border-white/5">
              Step Inspector & Warnings
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Warnings display */}
              {getValidationWarnings().length > 0 ? (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-bold text-amber-400 uppercase tracking-wide flex items-center gap-1">
                    <AlertTriangle size={12} /> Graph Validation Reports
                  </div>
                  <ul className="list-disc list-inside text-[10px] text-zinc-400 space-y-1 pl-1">
                    {getValidationWarnings().map((w, idx) => (
                      <li key={idx} className="leading-tight">{w}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="text-[10px] text-zinc-500 italic">No layout or connection warnings found in your canvas.</div>
              )}

              {/* Step info display if simulating */}
              {currentStepIndex >= 0 && simulationSteps[currentStepIndex] && (
                <div className="p-3 bg-[#0a0c16] rounded-xl border border-white/5 space-y-2">
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                    Active Node Details
                  </div>
                  <div className="text-xs font-semibold text-zinc-200">
                    {simulationSteps[currentStepIndex].node_name}
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/5">
                    <div>
                      <div className="text-[8px] text-zinc-500 uppercase">Duration</div>
                      <div className="text-[10px] font-mono font-semibold text-zinc-300">
                        {simulationSteps[currentStepIndex].duration_ms}ms
                      </div>
                    </div>
                    <div>
                      <div className="text-[8px] text-zinc-500 uppercase">Outputs</div>
                      <pre className="text-[8px] font-mono text-blue-400 overflow-x-auto truncate max-w-[120px]">
                        {JSON.stringify(simulationSteps[currentStepIndex].outputs)}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
