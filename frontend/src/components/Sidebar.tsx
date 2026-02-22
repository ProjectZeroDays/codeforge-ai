'use client'

import { useStore } from '@/store/useStore'
import {
  LayoutDashboard,
  MessageSquare,
  FolderKanban,
  Users,
  Github,
  Settings,
  Activity,
} from 'lucide-react'
import { motion } from 'framer-motion'

const navItems = [
  { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'chat', icon: MessageSquare, label: 'AI Chat' },
  { id: 'projects', icon: FolderKanban, label: 'Projects' },
  { id: 'agents', icon: Users, label: 'Agents' },
]

export default function Sidebar() {
  const { activeView, setActiveView, isConnected } = useStore()

  return (
    <aside className="w-20 bg-dark-900 border-r border-dark-800 flex flex-col items-center py-6 space-y-6">
      {/* Logo */}
      <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-lg">
        CF
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col space-y-2 w-full px-3">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeView === item.id

          return (
            <motion.button
              key={item.id}
              onClick={() => setActiveView(item.id as any)}
              className={`
                relative w-full h-14 rounded-xl flex items-center justify-center
                transition-all duration-200
                ${isActive
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'text-gray-400 hover:bg-dark-800 hover:text-white'
                }
              `}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              title={item.label}
            >
              <Icon className="w-6 h-6" />

              {isActive && (
                <motion.div
                  className="absolute -right-1 w-1 h-8 bg-primary-400 rounded-l-full"
                  layoutId="activeIndicator"
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
            </motion.button>
          )
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="flex flex-col space-y-2 w-full px-3">
        {/* Connection Status */}
        <div
          className="w-full h-14 rounded-xl flex items-center justify-center"
          title={isConnected ? 'Connected' : 'Disconnected'}
        >
          <Activity
            className={`w-5 h-5 ${isConnected ? 'text-green-500' : 'text-gray-600'}`}
          />
        </div>

        {/* GitHub */}
        <button
          className="w-full h-14 rounded-xl flex items-center justify-center text-gray-400 hover:bg-dark-800 hover:text-white transition-colors"
          title="GitHub Integration"
        >
          <Github className="w-6 h-6" />
        </button>

        {/* Settings */}
        <button
          className="w-full h-14 rounded-xl flex items-center justify-center text-gray-400 hover:bg-dark-800 hover:text-white transition-colors"
          title="Settings"
        >
          <Settings className="w-6 h-6" />
        </button>
      </div>
    </aside>
  )
}