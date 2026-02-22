'use client'

import { useState } from 'react'
import Dashboard from '@/components/Dashboard'
import ChatInterface from '@/components/ChatInterface'
import ProjectWorkspace from '@/components/ProjectWorkspace'
import AgentPanel from '@/components/AgentPanel'
import Sidebar from '@/components/Sidebar'
import { useStore } from '@/store/useStore'

export default function Home() {
  const { activeView } = useStore()

  return (
    <div className="flex h-screen bg-dark-950">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {activeView === 'dashboard' && <Dashboard />}
        {activeView === 'chat' && <ChatInterface />}
        {activeView === 'projects' && <ProjectWorkspace />}
        {activeView === 'agents' && <AgentPanel />}
      </main>
    </div>
  )
}