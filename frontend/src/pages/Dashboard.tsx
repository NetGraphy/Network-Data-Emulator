import { useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { fetchTopology } from '../api/client'

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: topology, isLoading } = useQuery({
    queryKey: ['topology'],
    queryFn: fetchTopology,
    refetchInterval: 15000,
  })

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!topology) return { initialNodes: [], initialEdges: [] }

    const nodes: Node[] = topology.nodes.map((n, i) => ({
      id: n.id,
      position: {
        x: 200 + (i % 4) * 280,
        y: 100 + Math.floor(i / 4) * 200,
      },
      data: {
        label: (
          <div className="text-center">
            <div className="text-sm font-bold">{n.hostname}</div>
            <div className="text-xs text-gray-400">{n.platform}</div>
            <div className="text-xs text-gray-500">{n.interface_count} intf</div>
          </div>
        ),
      },
      style: {
        background: n.admin_state === 'active' ? '#0f2b1d' : '#2b1d0f',
        border: `2px solid ${n.admin_state === 'active' ? '#22c55e' : '#f59e0b'}`,
        borderRadius: 12,
        padding: 16,
        color: '#e5e7eb',
        minWidth: 140,
      },
    }))

    const edges: Edge[] = topology.edges.map(e => ({
      id: e.id,
      source: e.source_device_id,
      target: e.target_device_id,
      label: `${e.source_interface.replace(/GigabitEthernet/, 'Gi')} ↔ ${e.target_interface.replace(/GigabitEthernet/, 'Gi')}`,
      style: {
        stroke: e.oper_state === 'up' ? '#22c55e' : '#ef4444',
        strokeWidth: 2,
      },
      labelStyle: { fill: '#9ca3af', fontSize: 10 },
      labelBgStyle: { fill: '#111827' },
    }))

    return { initialNodes: nodes, initialEdges: edges }
  }, [topology])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  const onNodeClick = useCallback((_: any, node: Node) => {
    navigate(`/devices/${node.id}`)
  }, [navigate])

  if (isLoading) {
    return <div className="flex items-center justify-center h-full text-gray-500">Loading topology...</div>
  }

  return (
    <div className="h-full">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Network Topology</h2>
          <p className="text-xs text-gray-500">
            {topology?.nodes.length || 0} devices, {topology?.edges.length || 0} links
          </p>
        </div>
      </div>
      <div className="h-[calc(100%-72px)]">
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1f2937" gap={20} />
          <Controls />
          <MiniMap
            nodeColor={n => n.style?.border?.toString().includes('#22c55e') ? '#22c55e' : '#f59e0b'}
            style={{ background: '#111827' }}
          />
        </ReactFlow>
      </div>
    </div>
  )
}
