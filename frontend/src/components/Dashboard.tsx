'use client'

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { projectsAPI, agentsAPI } from '@/lib/api'
import { useStore } from '@/store/useStore'
import {
  FolderKanban,
  Users,
  Activity,
  Zap,
  ArrowRight,
  Plus,
} from 'lucide-react'
import { motion } from 'framer-motion'

export default function Dashboard() {
  const { setActiveView, setProjects, setAgents } = useStore()

  // Fetch projects
  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsAPI.list,
  })

  // Fetch agents
  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsAPI.list,
  })

  useEffect(() => {
    if (projectsData?.projects) {
      setProjects(projectsData.projects)
    }
  }, [projectsData, setProjects])

  useEffect(() => {
    if (agentsData?.agents) {
      setAgents(agentsData.agents)
    }
  }, [agentsData, setAgents])

  const stats = [
    {
      label: 'Active Projects',
      value: projectsData?.projects?.length || 0,
      icon: FolderKanban,
      color: 'from-blue-500 to-blue-600',
      action: () => setActiveView('projects'),
    },
    {
      label: 'AI Agents',
      value: agentsData?.agents?.length || 0,
      icon: Users,
      color: 'from-purple-500 to-purple-600',
      action: () => setActiveView('agents'),
    },
    {
      label: 'Tasks Completed',
      value: agentsData?.agents?.reduce((acc: number, agent: any) => acc + (agent.tasks_completed || 0), 0) || 0,
      icon: Activity,
      color: 'from-green-500 to-green-600',
    },
    {
      label: 'Code Generated',
      value: projectsData?.projects?.reduce((acc: number, p: any) => acc + (p.file_count || 0), 0) || 0,
      icon: Zap,
      color: 'from-yellow-500 to-yellow-600',
    },
  ]

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-primary-400 to-purple-400 bg-clip-text text-transparent">
            Welcome to CodeForge AI
          </h1>
          <p className="text-gray-400 text-lg">
            Your AI-powered development platform with multi-agent orchestration
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => {
            const Icon = stat.icon
            return (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`
                  bg-dark-900 border border-dark-800 rounded-xl p-6
                  ${stat.action ? 'cursor-pointer hover:border-primary-600' : ''}
                  transition-all duration-200
                `}
                onClick={stat.action}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  {stat.action && (
                    <ArrowRight className="w-5 h-5 text-gray-600" />
                  )}
                </div>
                <div className="text-3xl font-bold mb-1">{stat.value}</div>
                <div className="text-gray-400 text-sm">{stat.label}</div>
              </motion.div>
            )
          })}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-dark-900 border border-dark-800 rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">Recent Projects</h3>
              <button
                onClick={() => setActiveView('projects')}
                className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1"
              >
                View All
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {projectsData?.projects?.length > 0 ? (
              <div className="space-y-3">
                {projectsData.projects.slice(0, 3).map((project: any) => (
                  <div
                    key={project.id}
                    className="p-3 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{project.name}</div>
                        <div className="text-sm text-gray-400">
                          {project.description || 'No description'}
                        </div>
                      </div>
                      {project.framework && (
                        <span className="px-2 py-1 bg-primary-600 text-white text-xs rounded">
                          {project.framework}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <FolderKanban className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No projects yet</p>
                <button
                  onClick={() => setActiveView('projects')}
                  className="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                  Create Project
                </button>
              </div>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-dark-900 border border-dark-800 rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">Active Agents</h3>
              <button
                onClick={() => setActiveView('agents')}
                className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1"
              >
                View All
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {agentsData?.agents?.length > 0 ? (
              <div className="space-y-3">
                {agentsData.agents.slice(0, 3).map((agent: any) => (
                  <div
                    key={agent.id}
                    className="p-3 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center text-white font-medium">
                          {agent.name.charAt(0)}
                        </div>
                        <div>
                          <div className="font-medium">{agent.name}</div>
                          <div className="text-sm text-gray-400">{agent.role}</div>
                        </div>
                      </div>
                      <span
                        className={`px-2 py-1 text-xs rounded ${
                          agent.status === 'active'
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-600 text-gray-300'
                        }`}
                      >
                        {agent.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No agents running</p>
                <button
                  onClick={() => setActiveView('agents')}
                  className="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center gap-2 mx-auto"
                >
                  <Plus className="w-4 h-4" />
                  Create Agent
                </button>
              </div>
            )}
          </motion.div>
        </div>

        {/* Quick Start */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-primary-900/50 to-purple-900/50 border border-primary-800 rounded-xl p-6"
        >
          <h3 className="text-xl font-semibold mb-4">🚀 Quick Start</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => setActiveView('chat')}
              className="p-4 bg-dark-900/80 rounded-lg hover:bg-dark-900 transition-colors text-left"
            >
              <div className="text-primary-400 mb-2">1. Start Chatting</div>
              <div className="text-sm text-gray-400">
                Begin a conversation with the AI to generate code
              </div>
            </button>
            <button
              onClick={() => setActiveView('projects')}
              className="p-4 bg-dark-900/80 rounded-lg hover:bg-dark-900 transition-colors text-left"
            >
              <div className="text-primary-400 mb-2">2. Create Project</div>
              <div className="text-sm text-gray-400">
                Set up a new project workspace
              </div>
            </button>
            <button
              onClick={() => setActiveView('agents')}
              className="p-4 bg-dark-900/80 rounded-lg hover:bg-dark-900 transition-colors text-left"
            >
              <div className="text-primary-400 mb-2">3. Deploy Agents</div>
              <div className="text-sm text-gray-400">
                Create AI agents to automate development tasks
              </div>
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}