'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsAPI } from '@/lib/api'
import { useStore } from '@/store/useStore'
import MonacoEditor from '@monaco-editor/react'
import {
  FolderKanban,
  Plus,
  FileText,
  Save,
  Trash2,
  Github,
  Play,
} from 'lucide-react'
import toast from 'react-hot-toast'

export default function ProjectWorkspace() {
  const { activeProject, setActiveProject } = useStore()
  const [selectedFile, setSelectedFile] = useState<any>(null)
  const [editorValue, setEditorValue] = useState('')
  const [showCreateProject, setShowCreateProject] = useState(false)
  const queryClient = useQueryClient()

  // Fetch projects
  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsAPI.list,
  })

  // Fetch files for active project
  const { data: filesData } = useQuery({
    queryKey: ['project-files', activeProject?.id],
    queryFn: () => projectsAPI.getFiles(activeProject!.id),
    enabled: !!activeProject,
  })

  // Save file mutation
  const saveFileMutation = useMutation({
    mutationFn: (data: any) => projectsAPI.saveFile(activeProject!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-files'] })
      toast.success('File saved successfully')
    },
    onError: () => {
      toast.error('Failed to save file')
    },
  })

  const handleSaveFile = () => {
    if (!selectedFile || !activeProject) return

    saveFileMutation.mutate({
      path: selectedFile.path,
      content: editorValue,
    })
  }

  const handleFileSelect = (file: any) => {
    setSelectedFile(file)
    setEditorValue(file.content || '')
  }

  return (
    <div className="h-full flex bg-dark-950">
      {/* Projects Sidebar */}
      <div className="w-64 border-r border-dark-800 flex flex-col">
        <div className="p-4 border-b border-dark-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Projects</h3>
            <button
              onClick={() => setShowCreateProject(true)}
              className="p-1.5 bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {projectsData?.projects?.map((project: any) => (
            <button
              key={project.id}
              onClick={() => setActiveProject(project)}
              className={`w-full p-3 text-left border-b border-dark-800 hover:bg-dark-800 transition-colors ${
                activeProject?.id === project.id ? 'bg-dark-800' : ''
              }`}
            >
              <div className="flex items-center gap-2">
                <FolderKanban className="w-4 h-4 text-primary-400" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{project.name}</div>
                  {project.framework && (
                    <div className="text-xs text-gray-500">{project.framework}</div>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* File Explorer */}
      {activeProject && (
        <div className="w-64 border-r border-dark-800 flex flex-col">
          <div className="p-4 border-b border-dark-800">
            <h3 className="font-semibold mb-2">{activeProject.name}</h3>
            <p className="text-xs text-gray-400">Files</p>
          </div>

          <div className="flex-1 overflow-y-auto">
            {filesData?.files?.map((file: any) => (
              <button
                key={file.id}
                onClick={() => handleFileSelect(file)}
                className={`w-full p-3 text-left border-b border-dark-800 hover:bg-dark-800 transition-colors ${
                  selectedFile?.id === file.id ? 'bg-dark-800' : ''
                }`}
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">{file.path}</div>
                    <div className="text-xs text-gray-500">{file.language}</div>
                  </div>
                </div>
              </button>
            ))}

            {!filesData?.files?.length && (
              <div className="p-4 text-center text-gray-500">
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No files yet</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 flex flex-col">
        {selectedFile ? (
          <>
            {/* Editor Header */}
            <div className="h-14 border-b border-dark-800 flex items-center justify-between px-4">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-gray-400" />
                <div>
                  <div className="text-sm font-medium">{selectedFile.path}</div>
                  <div className="text-xs text-gray-500">{selectedFile.language}</div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                   onClick={handleSaveFile}
                   disabled={saveFileMutation.isPending}
                   className="px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-dark-700 rounded-lg flex items-center gap-2 transition-colors"
                 >
                   <Save className="w-4 h-4" />
                   {saveFileMutation.isPending ? 'Saving...' : 'Save'}
                 </button>
                <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
                <button className="p-1.5 text-gray-400 hover:text-white transition-colors">
                  <Github className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Monaco Editor */}
            <div className="flex-1">
              <MonacoEditor
                height="100%"
                language={selectedFile.language}
                value={editorValue}
                onChange={(value) => setEditorValue(value || '')}
                theme="vs-dark"
                options={{
                  minimap: { enabled: true },
                  fontSize: 14,
                  lineNumbers: 'on',
                  roundedSelection: false,
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 2,
                  wordWrap: 'on',
                  formatOnPaste: true,
                  formatOnType: true,
                }}
              />
            </div>
          </>
        ) : activeProject ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <FileText className="w-16 h-16 mx-auto mb-4 text-gray-600" />
              <h3 className="text-xl font-semibold mb-2">No File Selected</h3>
              <p className="text-gray-400">Select a file from the sidebar to start editing</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <FolderKanban className="w-16 h-16 mx-auto mb-4 text-gray-600" />
              <h3 className="text-xl font-semibold mb-2">No Project Selected</h3>
              <p className="text-gray-400 mb-6">Create or select a project to get started</p>
              <button
                onClick={() => setShowCreateProject(true)}
                className="px-6 py-3 bg-primary-600 hover:bg-primary-700 rounded-lg font-medium flex items-center gap-2 mx-auto"
              >
                <Plus className="w-5 h-5" />
                Create New Project
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreateProject && (
        <CreateProjectModal onClose={() => setShowCreateProject(false)} />
      )}
    </div>
  )
}

function CreateProjectModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [framework, setFramework] = useState('')
  const queryClient = useQueryClient()

  const createMutation = useMutation({
    mutationFn: projectsAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      toast.success('Project created successfully')
      onClose()
    },
    onError: () => {
      toast.error('Failed to create project')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({ name, description, framework })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-dark-900 border border-dark-800 rounded-xl p-6 w-full max-w-md">
        <h3 className="text-xl font-semibold mb-4">Create New Project</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Project Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 focus:outline-none focus:border-primary-600"
              placeholder="my-awesome-project"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 focus:outline-none focus:border-primary-600 resize-none"
              rows={3}
              placeholder="Brief description of your project"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Framework (Optional)</label>
            <select
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 rounded-lg px-3 py-2 focus:outline-none focus:border-primary-600"
            >
              <option value="">Select framework</option>
              <option value="react">React</option>
              <option value="nextjs">Next.js</option>
              <option value="vue">Vue.js</option>
              <option value="python">Python</option>
              <option value="fastapi">FastAPI</option>
              <option value="django">Django</option>
              <option value="nodejs">Node.js</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-3 bg-dark-800 hover:bg-dark-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-dark-700 rounded-lg transition-colors"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}