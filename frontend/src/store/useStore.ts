import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type View = 'dashboard' | 'chat' | 'projects' | 'agents' | 'templates' | 'apikeys' | 'collaboration'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  model?: string
}

interface Agent {
  id: string
  name: string
  role: string
  status: string
  capabilities: string[]
}

interface Project {
  id: string
  name: string
  description: string
  framework?: string
  created_at: string
}

interface StoreState {
  // View
  activeView: View
  setActiveView: (view: View) => void

  // Chat
  messages: Message[]
  addMessage: (message: Message) => void
  clearMessages: () => void

  // Agents
  agents: Agent[]
  setAgents: (agents: Agent[]) => void
  addAgent: (agent: Agent) => void

  // Projects
  projects: Project[]
  setProjects: (projects: Project[]) => void
  activeProject: Project | null
  setActiveProject: (project: Project | null) => void

  // WebSocket
  isConnected: boolean
  setIsConnected: (connected: boolean) => void
}

export const useStore = create<StoreState>()(persist(
    (set) => ({
      // View
      activeView: 'dashboard',
      setActiveView: (view) => set({ activeView: view }),

      // Chat
      messages: [],
      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
      clearMessages: () => set({ messages: [] }),

      // Agents
      agents: [],
      setAgents: (agents) => set({ agents }),
      addAgent: (agent) => set((state) => ({ agents: [...state.agents, agent] })),

      // Projects
      projects: [],
      setProjects: (projects) => set({ projects }),
      activeProject: null,
      setActiveProject: (project) => set({ activeProject: project }),

      // WebSocket
      isConnected: false,
      setIsConnected: (connected) => set({ isConnected: connected }),
    }),
    {
      name: 'codeforge-storage',
      partialize: (state) => ({
        activeView: state.activeView,
        messages: state.messages,
        activeProject: state.activeProject,
        agents: state.agents,
        projects: state.projects,
        isConnected: state.isConnected,
      }),
    }
  )
)