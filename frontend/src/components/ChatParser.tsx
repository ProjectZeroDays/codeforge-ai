'use client'

import { useState, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Upload, FileText, Code, Download, FolderPlus, Loader2, CheckCircle, XCircle, FileCode } from 'lucide-react'
import toast from 'react-hot-toast'
import { chatParserAPI, projectsAPI } from '@/lib/api'

interface ExtractedFile {
  path: string
  content: string
  language?: string
}

interface ExtractionResult {
  success: boolean
  extraction_id?: string
  files: Record<string, string>
  code_blocks_count: number
  languages_detected: string[]
  source_format?: string
  readme_content?: string
  error?: string
}

export default function ChatParser() {
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null)
  const [selectedExtractedFile, setSelectedExtractedFile] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')

  // Fetch previous extractions
  const { data: extractionsData, refetch: refetchExtractions } = useQuery({
    queryKey: ['extractions'],
    queryFn: chatParserAPI.listExtractions,
  })

  // Upload and parse mutation
  const parseMutation = useMutation({
    mutationFn: (file: File) => chatParserAPI.uploadAndParse(file),
    onSuccess: (data: ExtractionResult) => {
      setExtractionResult(data)
      if (data.success) {
        toast.success(`Extracted ${data.code_blocks_count} code blocks!`)
        refetchExtractions()
      } else {
        toast.error(data.error || 'Extraction failed')
      }
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to parse document')
    },
  })

  // Create project mutation
  const createProjectMutation = useMutation({
    mutationFn: ({ extractionId, name }: { extractionId: string; name: string }) =>
      chatParserAPI.createProject(extractionId, name),
    onSuccess: () => {
      toast.success('Project created successfully!')
      setProjectName('')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create project')
    },
  })

  // Download ZIP mutation
  const downloadMutation = useMutation({
    mutationFn: (file: File) => chatParserAPI.downloadZip(file),
    onSuccess: (data: Blob) => {
      const url = window.URL.createObjectURL(data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'extracted_project.zip'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success('Downloaded ZIP file!')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to download')
    },
  })

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      setSelectedFile(file)
      parseMutation.mutate(file)
    }
  }, [parseMutation])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setSelectedFile(file)
      parseMutation.mutate(file)
    }
  }

  const supportedFormats = ['DOCX', 'PDF', 'TXT', 'HTML', 'MD']

  return (
    <div className="h-full flex flex-col bg-dark-900 text-white p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Chat Parser & Code Extractor</h2>
        <p className="text-gray-400">
          Upload AI chat transcripts to extract code and reconstruct projects
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 overflow-hidden">
        {/* Upload Section */}
        <div className="flex flex-col space-y-4">
          {/* Drop Zone */}
          <div
            className={`
              relative border-2 border-dashed rounded-xl p-8
              flex flex-col items-center justify-center
              transition-all duration-200 cursor-pointer
              ${dragActive
                ? 'border-primary-500 bg-primary-500/10'
                : 'border-gray-700 hover:border-gray-600 hover:bg-dark-800'
              }
            `}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => document.getElementById('fileInput')?.click()}
          >
            <input
              id="fileInput"
              type="file"
              accept=".docx,.pdf,.txt,.html,.htm,.md,.markdown"
              onChange={handleFileInput}
              className="hidden"
            />
            
            {parseMutation.isPending ? (
              <div className="flex flex-col items-center">
                <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
                <p className="text-gray-300">Parsing document...</p>
              </div>
            ) : (
              <>
                <Upload className="w-12 h-12 text-gray-500 mb-4" />
                <p className="text-gray-300 text-center mb-2">
                  Drag & drop a chat transcript or click to browse
                </p>
                <p className="text-gray-500 text-sm">
                  Supported: {supportedFormats.join(', ')}
                </p>
              </>
            )}
          </div>

          {/* Selected File Info */}
          {selectedFile && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-dark-800 rounded-lg p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-primary-500" />
                <div>
                  <p className="font-medium">{selectedFile.name}</p>
                  <p className="text-sm text-gray-400">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              {extractionResult?.success && (
                <CheckCircle className="w-6 h-6 text-green-500" />
              )}
            </motion.div>
          )}

          {/* Extraction Result Summary */}
          {extractionResult?.success && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-dark-800 rounded-lg p-4 space-y-3"
            >
              <h3 className="font-semibold text-lg">Extraction Summary</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-dark-700 rounded-lg p-3">
                  <p className="text-gray-400 text-sm">Code Blocks</p>
                  <p className="text-2xl font-bold text-primary-500">
                    {extractionResult.code_blocks_count}
                  </p>
                </div>
                <div className="bg-dark-700 rounded-lg p-3">
                  <p className="text-gray-400 text-sm">Files</p>
                  <p className="text-2xl font-bold text-green-500">
                    {Object.keys(extractionResult.files).length}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-gray-400 text-sm mb-2">Languages Detected</p>
                <div className="flex flex-wrap gap-2">
                  {extractionResult.languages_detected.map((lang) => (
                    <span
                      key={lang}
                      className="px-2 py-1 bg-primary-500/20 text-primary-400 rounded text-sm"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
              </div>

              {extractionResult.source_format && (
                <div>
                  <p className="text-gray-400 text-sm">Source Format</p>
                  <p className="text-white">{extractionResult.source_format}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => selectedFile && downloadMutation.mutate(selectedFile)}
                  disabled={downloadMutation.isPending}
                  className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg transition-colors"
                >
                  {downloadMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  Download ZIP
                </button>
                
                {extractionResult.extraction_id && (
                  <div className="flex-1 flex gap-2">
                    <input
                      type="text"
                      placeholder="Project name"
                      value={projectName}
                      onChange={(e) => setProjectName(e.target.value)}
                      className="flex-1 bg-dark-700 border border-gray-600 rounded-lg px-3 py-2 text-sm"
                    />
                    <button
                      onClick={() => {
                        if (projectName && extractionResult.extraction_id) {
                          createProjectMutation.mutate({
                            extractionId: extractionResult.extraction_id,
                            name: projectName,
                          })
                        }
                      }}
                      disabled={!projectName || createProjectMutation.isPending}
                      className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                    >
                      <FolderPlus className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Previous Extractions */}
          <div className="flex-1 overflow-auto">
            <h3 className="font-semibold mb-3">Recent Extractions</h3>
            <div className="space-y-2">
              {extractionsData?.extractions?.map((extraction: any) => (
                <div
                  key={extraction.id}
                  className="bg-dark-800 rounded-lg p-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <FileCode className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium">{extraction.filename}</p>
                      <p className="text-xs text-gray-400">
                        {extraction.code_blocks_count} blocks • {extraction.languages_detected?.join(', ')}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      extraction.status === 'completed'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-yellow-500/20 text-yellow-400'
                    }`}
                  >
                    {extraction.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Extracted Files Preview */}
        <div className="flex flex-col bg-dark-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h3 className="font-semibold">Extracted Files</h3>
          </div>
          
          <div className="flex flex-1 overflow-hidden">
            {/* File List */}
            <div className="w-1/3 border-r border-gray-700 overflow-auto p-2">
              {extractionResult?.success ? (
                Object.keys(extractionResult.files).map((path) => (
                  <button
                    key={path}
                    onClick={() => setSelectedExtractedFile(path)}
                    className={`
                      w-full text-left px-3 py-2 rounded-lg text-sm
                      flex items-center gap-2 mb-1
                      ${selectedExtractedFile === path
                        ? 'bg-primary-500/20 text-primary-400'
                        : 'hover:bg-dark-700'
                      }
                    `}
                  >
                    <Code className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{path}</span>
                  </button>
                ))
              ) : (
                <p className="text-gray-500 text-sm p-4 text-center">
                  No files extracted yet
                </p>
              )}
            </div>

            {/* File Content */}
            <div className="flex-1 overflow-auto p-4">
              {selectedExtractedFile && extractionResult?.files[selectedExtractedFile] ? (
                <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap">
                  {extractionResult.files[selectedExtractedFile]}
                </pre>
              ) : (
                <p className="text-gray-500 text-center">
                  Select a file to preview
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
