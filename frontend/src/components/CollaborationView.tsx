'use client'

import { useEffect, useState } from 'react'
import { collaborationAPI, CollaborationGraph } from '@/lib/api-extended'

export default function CollaborationView() {
  const [graph, setGraph] = useState<CollaborationGraph | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    collaborationAPI.getGraph()
      .then((res) => setGraph(res))
      .catch((err) => console.error('Failed to load collaboration graph:', err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full bg-dark-950 text-white p-8 overflow-y-auto">
      <h1 className="text-2xl font-bold mb-6">Agent Collaboration & Graph</h1>

      {loading ? (
        <div className="text-gray-400">Loading collaboration graph...</div>
      ) : !graph ? (
        <div className="text-gray-400">No collaboration data available.</div>
      ) : (
        <div className="space-y-6">
          {/* Stats Bar */}
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-6">
              <div className="text-gray-400 text-sm">Total Agents</div>
              <div className="text-3xl font-bold mt-2 text-primary-400">{graph.stats.total_agents}</div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-6">
              <div className="text-gray-400 text-sm">Active Connections</div>
              <div className="text-3xl font-bold mt-2 text-primary-400">{graph.stats.total_connections}</div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-6">
              <div className="text-gray-400 text-sm">Active Delegations</div>
              <div className="text-3xl font-bold mt-2 text-primary-400">{graph.stats.active_delegations}</div>
            </div>
          </div>

          {/* Nodes List */}
          <div className="bg-dark-900 border border-dark-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Registered Agents</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {graph.nodes.map((n) => (
                <div key={n.id} className="bg-dark-950 border border-dark-800 rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{n.name}</div>
                    <div className="text-xs text-gray-400 capitalize">{n.role}</div>
                  </div>
                  <span className="px-2 py-1 bg-green-500/10 text-green-500 rounded-full text-xs font-semibold">
                    {n.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}