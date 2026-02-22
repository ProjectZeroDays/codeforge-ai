'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentsAPI } from '@/lib/api'
import { useStore } from '@/store/useStore'
import { Users, Plus, Activity, Trash2, Play, Pause } from 'lucide-react'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'

export default function AgentPanel() {
  const [showCreateAgent, setShowCreateAgent] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<any>(null)

  // Fetch agents
  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsAPI.list,
  })

  // Fetch agent activity
  const { data: activityData } = useQuery({
    queryKey: ['agent-activity', selectedAgent?.id],
    queryFn: () => agentsAPI.getActivity(selectedAgent!.id),
    enabled: !!selectedAgent,
  })

  const handleAgentSelect = (agent: any) => {
    setSelectedAgent(agent)
  }

  return (
    <div className="h-full flex bg-dark-950">
      {/* Agents List */}
      <div className="w-80 border-r border-dark-800 flex flex-col">
        <div className="p-4 border-b border-dark-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">AI Agents</h3>
            <button
              onClick={() => setShowCreateAgent(true)}
              className="p-1.5 bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-gray-400">
            {agentsData?.agents?.length || 0} active agents
          </p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {agentsData?.agents?.map((agent: any, index: number) => (
            <motion.button
              key={agent.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => handleAgentSelect(agent)}
              className={`w-full p-4 text-left border-b border-dark-800 hover:bg-dark-800 transition-colors ${
                selectedAgent?.id === agent.id ? 'bg-dark-800' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center text-white font-medium flex-shrink-0">
                  {agent.name.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium mb-1">{agent.name}</div>
                  <div className="text-sm text-gray-400 mb-2">{agent.role}</div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 text-xs rounded ${
                        agent.status === 'active'
                          ? 'bg-green-600 text-white'
                          : agent.status === 'idle'
                          ? 'bg-yellow-600 text-white'
                          : 'bg-gray-600 text-gray-300'
                      }`}
                    >
                      {agent.status}
                    </span>
                    {agent.tasks_completed > 0 && (
                      <span className="text-xs text-gray-500">
                        {agent.tasks_completed} tasks
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </motion.button>
          ))}

          {!agentsData?.agents?.length && (
            <div className="p-8 text-center text-gray-500">
              <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No agents yet</p>
              <button
                onClick={() => setShowCreateAgent(true)}
                className="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg text-sm"
              >
                Create First Agent
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Agent Details */}
      <div className="flex-1 flex flex-col">
        {selectedAgent ? (
          <>
            {/* Agent Header */}
            <div className="h-20 border-b border-dark-800 flex items-center justify-between px-6">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-full bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center text-white font-medium text-xl">
                  {selectedAgent.name.charAt(0)}
                </div>
                <div>
                  <h2 className="text-xl font-semibold">{selectedAgent.name}</h2>
                  <p className="text-sm text-gray-400">{selectedAgent.role}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button className="px-4 py-2 bg-dark-800 hover:bg-dark-700 rounded-lg flex items-center gap-2 transition-colors">
                  <Play className="w-4 h-4" />
                  Assign Task
                </button>
                <button className="p-2 text-red-400 hover:bg-dark-800 rounded-lg transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Agent Info */}
            <div className="p-6 space-y-6">
              {/* Capabilities */}
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">Capabilities</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedAgent.capabilities?.map((cap: string) => (
                    <span
                      key={cap}
                      className="px-3 py-1 bg-dark-800 border border-dark-700 rounded-lg text-sm"
                    >
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              {/* Activity */}
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">Recent Activity</h3>
                <div className="space-y-2">
                  {activityData?.activity?.length > 0 ? (
                    activityData.activity.slice(0, 10).map((task: any) => (
                      <div
                        key={task.id}
                        className="p-3 bg-dark-800 border border-dark-700 rounded-lg"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Activity className="w-4 h-4 text-primary-400" />
                            <span className="font-medium">{task.type}</span>
                          </div>
                          <span
                            className={`px-2 py-0.5 text-xs rounded ${
                              task.status === 'completed'
                                ? 'bg-green-600 text-white'
                                : task.status === 'in_progress'
                                ? 'bg-blue-600 text-white'
                                : task.status === 'failed'
                                ? 'bg-red-600 text-white'
                                : 'bg-gray-600 text-white'
                            }`}
                          >
                            {task.status}
                          </span>
                        </div>
                        <p className="text-sm text-gray-400">{task.description}</p>
                        {task.completed_at && (
                          <p className="text-xs text-gray-500 mt-2">
                            {new Date(task.completed_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No activity yet</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Users className="w-16 h-16 mx-auto mb-4 text-gray-600" />
              <h3 className="text-xl font-semibold mb-2">No Agent Selected</h3>
              <p className="text-gray-400">Select an agent to view details and activity</p>
            </div>
          </div>
        )}
      </div>

      {/* Create Agent Modal */}
      {showCreateAgent && (
        <CreateAgentModal onClose={() => setShowCreateAgent(false)} />
      )}
    </div>
  )
}

function CreateAgentModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [capabilities, setCapabilities] = useState<string[]>([])
  const [capInput, setCapInput] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const queryClient = useQueryClient()

  const createMutation = useMutation({
    mutationFn: agentsAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      toast.success('Agent created successfully')
      onClose()
    },
    onError: () => {
      toast.error('Failed to create agent')
    },
  })

  const handleAddCapability = () => {
    if (capInput.trim() && !capabilities.includes(capInput.trim())) {
      setCapabilities([...capabilities, capInput.trim()])
      setCapInput('')
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      name,
      role,
      capabilities,
      system_prompt: systemPrompt || `You are ${name}, a specialized AI agent with the role of ${role}.`,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-dark-900 border border-dark-800 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-xl font-semibold mb-4">Create New Agent</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Agent Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 focus:outline-none focus:border-primary-600"
              placeholder="Backend Developer Agent"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Role/Specialty</label>
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 focus:outline-none focus:border-primary-600"
              placeholder="Backend Development"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Capabilities</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={capInput}
                onChange={(e) => setCapInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCapability())}
                className="flex-1 bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 focus:outline-none focus:border-primary-600"
                placeholder="Add capability (e.g., Python, FastAPI, Database Design)"
              />
              <button
                type="button"
                onClick={handleAddCapability}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {capabilities.map((cap) => (
                <span
                  key={cap}
                  className="px-3 py-1 bg-dark-800 border border-dark-700 rounded-lg text-sm flex items-center gap-2"
                >
                  {cap}
                  <button
                    type="button"
                    onClick={() => setCapabilities(capabilities.filter((c) => c !== cap))}
                    className="text-red-400 hover:text-red-300"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              System Prompt (Optional)
            </label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 focus:outline-none focus:border-primary-600 resize-none font-mono text-sm"
              rows={6}
              placeholder="Custom instructions for the agent..."
            />
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-dark-800 hover:bg-dark-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-dark-700 rounded-lg transition-colors"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}