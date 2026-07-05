import React, { useState, useEffect, useRef } from 'react'
import { getGraph, clearGraph } from '../api/client'
import { Trash2, RefreshCw, ZoomIn, ZoomOut, Maximize } from 'lucide-react'

interface GraphNode {
  id: string
  label: string
  type: string
  description: string
  sources: string[]
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  type: string
  description: string
  source_file: string
}

interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

const TYPE_COLORS: Record<string, string> = {
  person: '#A78BFA', // purple-400
  organization: '#22D3EE', // cyan-400
  technology: '#FB923C', // orange-400
  concept: '#34D399', // emerald-400
  location: '#FB7185', // rose-400
  event: '#FBBF24', // amber-400
  other: '#9CA3AF', // gray-400
}

export default function GraphVisualizer() {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [selectedLink, setSelectedLink] = useState<GraphLink | null>(null)
  
  // Transform for Pan & Zoom
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  
  const svgRef = useRef<SVGSVGElement>(null)
  const simulationRef = useRef<number | null>(null)
  const isPanningRef = useRef(false)
  const panStartRef = useRef({ x: 0, y: 0 })
  const draggedNodeRef = useRef<string | null>(null)

  useEffect(() => {
    fetchGraphData()
    return () => {
      if (simulationRef.current) cancelAnimationFrame(simulationRef.current)
    }
  }, [])

  async function fetchGraphData() {
    setLoading(true)
    try {
      const res = await getGraph()
      
      // Initialize nodes with random positions
      const width = 700
      const height = 500
      const nodes = res.nodes.map((n: GraphNode) => ({
        ...n,
        x: width / 2 + (Math.random() - 0.5) * 200,
        y: height / 2 + (Math.random() - 0.5) * 200,
        vx: 0,
        vy: 0,
      }))
      
      setData({ nodes, links: res.links })
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  // Force Directed Simulation loop
  useEffect(() => {
    if (data.nodes.length === 0) return

    const width = 700
    const height = 500
    const repulsion = 400
    const attraction = 0.04
    const gravity = 0.015
    const damping = 0.85
    const linkLength = 120

    const runSimulation = () => {
      setData(prev => {
        const nodes = prev.nodes.map(n => ({ ...n }))
        const nodeMap = new Map(nodes.map(n => [n.id, n]))
        
        // 1. Repulsion (between all nodes)
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const n1 = nodes[i]
            const n2 = nodes[j]
            const dx = n2.x! - n1.x!
            const dy = n2.y! - n1.y!
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            
            if (dist < 300) {
              const force = repulsion / (dist * dist)
              const forceX = force * (dx / dist)
              const forceY = force * (dy / dist)
              
              n1.vx = (n1.vx || 0) - forceX
              n1.vy = (n1.vy || 0) - forceY
              n2.vx = (n2.vx || 0) + forceX
              n2.vy = (n2.vy || 0) + forceY
            }
          }
        }

        // 2. Attraction (along links)
        prev.links.forEach(l => {
          const sourceId = typeof l.source === 'object' ? (l.source as GraphNode).id : (l.source as string)
          const targetId = typeof l.target === 'object' ? (l.target as GraphNode).id : (l.target as string)
          
          const s = nodeMap.get(sourceId)
          const t = nodeMap.get(targetId)
          
          if (s && t) {
            const dx = t.x! - s.x!
            const dy = t.y! - s.y!
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            const force = attraction * (dist - linkLength)
            const forceX = force * (dx / dist)
            const forceY = force * (dy / dist)
            
            s.vx = (s.vx || 0) + forceX
            s.vy = (s.vy || 0) + forceY
            t.vx = (t.vx || 0) - forceX
            t.vy = (t.vy || 0) - forceY
          }
        })

        // 3. Gravity & Update Positions
        const cx = width / 2
        const cy = height / 2
        nodes.forEach(n => {
          if (n.id === draggedNodeRef.current) return // Skip updates for dragged node

          const dx = cx - n.x!
          const dy = cy - n.y!
          
          n.vx = ((n.vx || 0) + dx * gravity) * damping
          n.vy = ((n.vy || 0) + dy * gravity) * damping
          
          n.x! += n.vx
          n.y! += n.vy
        })

        return { nodes, links: prev.links }
      })

      simulationRef.current = requestAnimationFrame(runSimulation)
    }

    simulationRef.current = requestAnimationFrame(runSimulation)
    return () => {
      if (simulationRef.current) cancelAnimationFrame(simulationRef.current)
    }
  }, [data.nodes.length, data.links.length])

  // Mouse Handlers for Dragging & Panning
  const handleMouseDown = (e: React.MouseEvent) => {
    const target = e.target as SVGElement
    const nodeId = target.getAttribute('data-node-id')
    
    if (nodeId) {
      draggedNodeRef.current = nodeId
    } else {
      isPanningRef.current = true
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggedNodeRef.current && svgRef.current) {
      const rect = svgRef.current.getBoundingClientRect()
      
      // Calculate coordinates in zoom/pan space
      const mouseX = (e.clientX - rect.left - pan.x) / zoom
      const mouseY = (e.clientY - rect.top - pan.y) / zoom
      
      setData(prev => {
        const nodes = prev.nodes.map(n => {
          if (n.id === draggedNodeRef.current) {
            return { ...n, x: mouseX, y: mouseY, vx: 0, vy: 0 }
          }
          return n
        })
        return { nodes, links: prev.links }
      })
    } else if (isPanningRef.current) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y
      })
    }
  }

  const handleMouseUp = () => {
    draggedNodeRef.current = null
    isPanningRef.current = false
  }

  // Zoom Handler
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const zoomFactor = 1.1
    if (e.deltaY < 0) {
      setZoom(z => Math.min(z * zoomFactor, 3))
    } else {
      setZoom(z => Math.max(z / zoomFactor, 0.4))
    }
  }

  const handleClearGraph = async () => {
    if (!confirm('Clear the entire knowledge graph? All entity-relation records will be deleted.')) return
    try {
      await clearGraph()
      setData({ nodes: [], links: [] })
      setSelectedNode(null)
      setSelectedLink(null)
    } catch {}
  }

  const handleResetZoom = () => {
    setPan({ x: 0, y: 0 })
    setZoom(1)
  }

  return (
    <div className="flex flex-1 h-full overflow-hidden bg-gray-900 text-gray-150">
      {/* Graph Area */}
      <div className="flex-1 relative flex flex-col min-w-0 border-r border-gray-800">
        
        {/* Controls */}
        <div className="absolute top-4 left-4 flex gap-2 z-10 bg-gray-850/80 backdrop-blur border border-gray-700 p-1.5 rounded-xl shadow-lg">
          <button onClick={fetchGraphData} className="p-1.5 rounded-lg hover:bg-gray-750 transition-colors" title="Reload Graph">
            <RefreshCw size={15} />
          </button>
          <button onClick={() => setZoom(z => Math.min(z * 1.2, 3))} className="p-1.5 rounded-lg hover:bg-gray-750 transition-colors" title="Zoom In">
            <ZoomIn size={15} />
          </button>
          <button onClick={() => setZoom(z => Math.max(z / 1.2, 0.4))} className="p-1.5 rounded-lg hover:bg-gray-750 transition-colors" title="Zoom Out">
            <ZoomOut size={15} />
          </button>
          <button onClick={handleResetZoom} className="p-1.5 rounded-lg hover:bg-gray-750 transition-colors" title="Recenter">
            <Maximize size={15} />
          </button>
          <div className="h-5 w-px bg-gray-700 self-center mx-1"></div>
          <button onClick={handleClearGraph} className="p-1.5 rounded-lg hover:bg-red-950/40 text-red-400 hover:text-red-300 transition-colors" title="Clear All Graph Data">
            <Trash2 size={15} />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <svg className="animate-spin h-8 w-8 text-cyan-500" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-sm text-gray-400 font-medium">Extracting Relationships...</span>
            </div>
          </div>
        ) : data.nodes.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-6">
            <div className="text-5xl">📊</div>
            <div>
              <div className="text-lg font-semibold text-gray-200">Knowledge Graph is Empty</div>
              <p className="text-sm text-gray-400 mt-1 max-w-sm">
                Ingest TXT, PDF, DOCX files or websites in the Sidebar, and the application will extract entities and relationships automatically!
              </p>
            </div>
          </div>
        ) : (
          <svg
            ref={svgRef}
            className="flex-1 w-full h-full cursor-grab active:cursor-grabbing select-none"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
          >
            {/* Arrow Marker Definitions */}
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="22" // offset to position arrow at node boundary
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#4B5563" />
              </marker>
            </defs>

            {/* Transform Group */}
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              
              {/* Edges / Lines */}
              {data.links.map((link, idx) => {
                const s = typeof link.source === 'object' ? (link.source as GraphNode) : data.nodes.find(n => n.id === link.source)
                const t = typeof link.target === 'object' ? (link.target as GraphNode) : data.nodes.find(n => n.id === link.target)
                if (!s || !t) return null

                const isSelected = selectedLink === link
                
                return (
                  <g key={`link-${idx}`} className="cursor-pointer" onClick={(e) => { e.stopPropagation(); setSelectedLink(link); setSelectedNode(null); }}>
                    <line
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke={isSelected ? '#22D3EE' : '#374151'}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      strokeDasharray={isSelected ? '4,4' : undefined}
                      markerEnd="url(#arrow)"
                      className="transition-colors hover:stroke-cyan-500/80"
                    />
                    {/* Invisible thicker line for easier clicking */}
                    <line
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke="transparent"
                      strokeWidth={10}
                    />
                    {/* Relation Type Label */}
                    <text
                      x={(s.x! + t.x!) / 2}
                      y={(s.y! + t.y!) / 2 - 4}
                      fill={isSelected ? '#22D3EE' : '#6B7280'}
                      fontSize="9"
                      textAnchor="middle"
                      className="font-mono bg-gray-900 pointer-events-none"
                    >
                      {link.type}
                    </text>
                  </g>
                )
              })}

              {/* Nodes */}
              {data.nodes.map(node => {
                const color = TYPE_COLORS[node.type] || TYPE_COLORS.other
                const isSelected = selectedNode === node
                
                return (
                  <g
                    key={node.id}
                    className="cursor-pointer group"
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={(e) => { e.stopPropagation(); setSelectedNode(node); setSelectedLink(null); }}
                  >
                    {/* Pulsing ring for selected node */}
                    {isSelected && (
                      <circle
                        r={18}
                        fill="none"
                        stroke={color}
                        strokeWidth="1.5"
                        className="animate-ping opacity-75"
                      />
                    )}
                    
                    {/* Node circle */}
                    <circle
                      data-node-id={node.id}
                      r={13}
                      fill="#1F2937"
                      stroke={isSelected ? '#FFFFFF' : color}
                      strokeWidth={isSelected ? 2.5 : 2}
                      className="transition-all duration-150 group-hover:scale-110"
                      style={{ filter: `drop-shadow(0 0 4px ${color}40)` }}
                    />
                    
                    {/* Text Label */}
                    <text
                      y={26}
                      fill="#E5E7EB"
                      fontSize="10"
                      fontWeight="600"
                      textAnchor="middle"
                      className="pointer-events-none"
                      style={{ textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}
                    >
                      {node.label}
                    </text>
                    
                    {/* Subtype Badge */}
                    <text
                      y={-18}
                      fill={color}
                      fontSize="8"
                      fontFamily="monospace"
                      textAnchor="middle"
                      className="pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      {node.type.toUpperCase()}
                    </text>
                  </g>
                )
              })}
            </g>
          </svg>
        )}
      </div>

      {/* Detail Sidebar */}
      <div className="w-80 bg-gray-850 p-5 flex flex-col gap-5 overflow-y-auto flex-shrink-0">
        <div>
          <h2 className="text-md font-bold text-gray-100">Knowledge Base Graph</h2>
          <p className="text-xs text-gray-400 mt-1">Explore entities, relationships, and RAG facts extracted from documents.</p>
        </div>

        <div className="h-px bg-gray-800"></div>

        {selectedNode ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border"
                style={{ color: TYPE_COLORS[selectedNode.type], borderColor: TYPE_COLORS[selectedNode.type] + '40', backgroundColor: TYPE_COLORS[selectedNode.type] + '10' }}>
                {selectedNode.type}
              </span>
              <button onClick={() => setSelectedNode(null)} className="text-xs text-gray-500 hover:text-gray-300">Close</button>
            </div>
            
            <div>
              <h3 className="text-lg font-bold text-gray-150 leading-snug">{selectedNode.label}</h3>
              {selectedNode.description ? (
                <p className="text-xs text-gray-300 leading-relaxed mt-2 p-3 bg-gray-900/40 border border-gray-800 rounded-xl">
                  {selectedNode.description}
                </p>
              ) : (
                <p className="text-xs text-gray-500 italic mt-2">No description available.</p>
              )}
            </div>

            <div>
              <h4 className="text-[11px] uppercase tracking-wider font-mono text-gray-400 font-bold mb-1.5">Sources</h4>
              <div className="flex flex-col gap-1">
                {selectedNode.sources.map((src, i) => (
                  <div key={i} className="text-xs px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-cyan-300 font-mono overflow-hidden text-ellipsis whitespace-nowrap" title={src}>
                    {src}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : selectedLink ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border border-cyan-800/40 bg-cyan-950/20 text-cyan-400">
                RELATIONSHIP
              </span>
              <button onClick={() => setSelectedLink(null)} className="text-xs text-gray-500 hover:text-gray-300">Close</button>
            </div>

            <div>
              <div className="flex flex-col gap-1 items-center bg-gray-900/30 border border-gray-800 rounded-xl p-3">
                <span className="text-xs font-semibold text-gray-300">
                  {typeof selectedLink.source === 'object' ? (selectedLink.source as GraphNode).label : selectedLink.source}
                </span>
                <span className="text-[10px] font-mono text-cyan-400 uppercase py-0.5 px-2 bg-cyan-950/40 border border-cyan-800/30 rounded-md my-1.5">
                  {selectedLink.type}
                </span>
                <span className="text-xs font-semibold text-gray-300">
                  {typeof selectedLink.target === 'object' ? (selectedLink.target as GraphNode).label : selectedLink.target}
                </span>
              </div>

              {selectedLink.description ? (
                <p className="text-xs text-gray-300 leading-relaxed mt-3 p-3 bg-gray-900/40 border border-gray-800 rounded-xl">
                  {selectedLink.description}
                </p>
              ) : (
                <p className="text-xs text-gray-500 italic mt-3">No description available.</p>
              )}
            </div>

            <div>
              <h4 className="text-[11px] uppercase tracking-wider font-mono text-gray-400 font-bold mb-1.5">Source Document</h4>
              <div className="text-xs px-2.5 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-cyan-300 font-mono overflow-hidden text-ellipsis whitespace-nowrap" title={selectedLink.source_file}>
                {selectedLink.source_file}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4 text-xs text-gray-400 leading-relaxed">
            <p>Click on any node or edge in the graph to view detailed properties, relationships, and sources.</p>
            
            <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-4 flex flex-col gap-3 mt-2">
              <h4 className="text-[10px] font-mono uppercase text-gray-300 font-bold">Graph Stats</h4>
              <div className="flex justify-between">
                <span>Total Entities:</span>
                <span className="font-bold text-gray-200">{data.nodes.length}</span>
              </div>
              <div className="flex justify-between">
                <span>Total Relations:</span>
                <span className="font-bold text-gray-200">{data.links.length}</span>
              </div>
            </div>

            <div className="mt-4 flex flex-col gap-2">
              <h4 className="text-[10px] font-mono uppercase text-gray-300 font-bold mb-1">Legend</h4>
              {Object.entries(TYPE_COLORS).map(([type, color]) => {
                // Skip 'other' if no nodes use it or show it at end
                return (
                  <div key={type} className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }}></span>
                    <span className="capitalize">{type}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
