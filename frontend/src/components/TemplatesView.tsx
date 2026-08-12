'use client'

import { useEffect, useState } from 'react'
import { templatesAPI, ProjectTemplate } from '@/lib/api-extended'

export default function TemplatesView() {
  const [templates, setTemplates] = useState<ProjectTemplate[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    templatesAPI.list()
      .then((res) => setTemplates(res.templates || []))
      .catch((err) => console.error('Failed to load templates:', err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full bg-dark-950 text-white p-8 overflow-y-auto">
      <h1 className="text-2xl font-bold mb-6">Project Templates</h1>
      {loading ? (
        <div className="text-gray-400">Loading templates...</div>
      ) : templates.length === 0 ? (
        <div className="text-gray-400">No project templates found.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((t) => (
            <div key={t.id} className="bg-dark-900 border border-dark-800 rounded-xl p-6 flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider text-primary-400 font-semibold">{t.category}</span>
                <h3 className="text-lg font-bold mt-1">{t.name}</h3>
                <p className="text-gray-400 text-sm mt-2">{t.description}</p>
              </div>
              <div className="mt-6 flex items-center justify-between">
                <span className="text-xs text-gray-500">Language: {t.language}</span>
                <button
                  onClick={() => alert(`Selected template: ${t.name}`)}
                  className="px-6 py-3 bg-primary-600 hover:bg-primary-500 rounded-lg text-sm font-medium transition-colors"
                >
                  Use Template
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}