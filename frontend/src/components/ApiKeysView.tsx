'use client'

import { useEffect, useState } from 'react'
import { apiKeysAPI, APIKey } from '@/lib/api-extended'

export default function ApiKeysView() {
  const [keys, setKeys] = useState<APIKey[]>([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [newProvider, setNewProvider] = useState('openai')
  const [newKey, setNewKey] = useState('')

  const loadKeys = () => {
    apiKeysAPI.list()
      .then((res) => setKeys(res.api_keys || []))
      .catch((err: any) => console.error('Failed to load API keys:', err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadKeys()
  }, [])

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName || !newKey) return
    apiKeysAPI.add({ name: newName, provider: newProvider, api_key: newKey, environment: 'production' })
      .then(() => {
        setNewName('')
        setNewKey('')
        loadKeys()
      })
      .catch((err: any) => alert('Failed to add API key: ' + err.message))
  }

  const handleDelete = (id: string) => {
    if (!confirm('Are you sure you want to delete this API key?')) return
    apiKeysAPI.delete(id)
      .then(loadKeys)
      .catch((err: any) => alert('Failed to delete: ' + err.message))
  }

  return (
    <div className="flex flex-col h-full bg-dark-950 text-white p-8 overflow-y-auto">
      <h1 className="text-2xl font-bold mb-6">API Key Management</h1>

      {/* Add Key Form */}
      <form onSubmit={handleAdd} className="bg-dark-900 border border-dark-800 rounded-xl p-6 mb-8 flex gap-4 items-end">
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-400 mb-1">Key Name</label>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="My OpenAI Key"
            className="w-full bg-dark-950 border border-dark-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary-500"
          />
        </div>
        <div className="w-48">
          <label className="block text-xs font-medium text-gray-400 mb-1">Provider</label>
          <select
            value={newProvider}
            onChange={(e) => setNewProvider(e.target.value)}
            className="w-full bg-dark-950 border border-dark-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary-500"
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="venice">Venice AI</option>
            <option value="github">GitHub</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-400 mb-1">API Key</label>
          <input
            type="password"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="sk-..."
            className="w-full bg-dark-950 border border-dark-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary-500"
          />
        </div>
        <button
          type="submit"
          className="px-6 py-3 bg-primary-600 hover:bg-primary-500 rounded-lg text-sm font-medium transition-colors"
        >
          Add Key
        </button>
      </form>

      {/* Keys List */}
      <h2 className="text-lg font-semibold mb-4">Configured Keys</h2>
      {loading ? (
        <div className="text-gray-400">Loading API keys...</div>
      ) : keys.length === 0 ? (
        <div className="text-gray-400">No API keys stored.</div>
      ) : (
        <div className="bg-dark-900 border border-dark-800 rounded-xl overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-dark-800 text-gray-400 uppercase text-xs">
              <tr>
                <th className="px-6 py-3">Name</th>
                <th className="px-6 py-3">Provider</th>
                <th className="px-6 py-3">Prefix</th>
                <th className="px-6 py-3">Environment</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-800">
              {keys.map((k) => (
                <tr key={k.id} className="hover:bg-dark-850">
                  <td className="px-6 py-4 font-medium">{k.name}</td>
                  <td className="px-6 py-4 capitalize text-gray-300">{k.provider}</td>
                  <td className="px-6 py-4 font-mono text-xs text-gray-400">{k.key_prefix}...</td>
                  <td className="px-6 py-4 text-gray-300">{k.environment}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${k.needs_rotation ? 'bg-yellow-500/10 text-yellow-500' : 'bg-green-500/10 text-green-500'}`}>
                      {k.needs_rotation ? 'Rotation Needed' : 'Active'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleDelete(k.id)}
                      className="text-red-400 hover:text-red-300 font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}