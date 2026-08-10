import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Chat & AI
export const chatAPI = {
  sendMessage: async (messages: any[], options?: any) => {
    const response = await api.post('/api/chat', {
      messages,
      ...options,
    })
    return response.data
  },

  generateCode: async (prompt: string, options?: any) => {
    const response = await api.post('/api/generate-code', {
      messages: [{ role: 'user', content: prompt }],
      ...options,
    })
    return response.data
  },

  updateSystemPrompt: async (data: any) => {
    const response = await api.put('/api/system-prompt', data)
    return response.data
  },

  // Unified chat supporting both Venice and Local LLM
  unifiedChat: async (data: {
    messages: any[]
    provider: 'venice' | 'local'
    model?: string
    system_prompt?: string
    system_prompt_id?: string
    temperature?: number
    max_tokens?: number
    stream?: boolean
  }) => {
    const response = await api.post('/api/unified-chat', data)
    return response.data
  },
}

// System Prompts
export const systemPromptsAPI = {
  list: async () => {
    const response = await api.get('/api/system-prompts')
    return response.data
  },

  get: async (promptId: string) => {
    const response = await api.get(`/api/system-prompts/${promptId}`)
    return response.data
  },
}

// Local LLM
export const localLLMAPI = {
  getStatus: async () => {
    const response = await api.get('/api/local-llm/status')
    return response.data
  },

  downloadModel: async (modelId?: string) => {
    const response = await api.post('/api/local-llm/download', null, {
      params: { model_id: modelId },
    })
    return response.data
  },

  loadModel: async (config: {
    name: string
    model_id: string
    device?: string
    quantization?: string
    max_context_length?: number
  }) => {
    const response = await api.post('/api/local-llm/load', config)
    return response.data
  },

  unloadModel: async () => {
    const response = await api.post('/api/local-llm/unload')
    return response.data
  },

  generate: async (data: {
    prompt: string
    system_prompt?: string
    temperature?: number
    top_p?: number
    max_tokens?: number
  }) => {
    const response = await api.post('/api/local-llm/generate', data)
    return response.data
  },

  listModels: async () => {
    const response = await api.get('/api/local-llm/models')
    return response.data
  },

  getConfigs: async () => {
    const response = await api.get('/api/local-llm/configs')
    return response.data
  },
}

// Chat Parser
export const chatParserAPI = {
  uploadAndParse: async (file: File, fileType?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (fileType) {
      formData.append('file_type', fileType)
    }
    const response = await api.post('/api/chat-parser/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  createProject: async (extractionId: string, projectName: string) => {
    const response = await api.post('/api/chat-parser/create-project', {
      extraction_id: extractionId,
      project_name: projectName,
    })
    return response.data
  },

  downloadZip: async (file: File, fileType?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (fileType) {
      formData.append('file_type', fileType)
    }
    const response = await api.post('/api/chat-parser/download-zip', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
    })
    return response.data
  },

  listExtractions: async () => {
    const response = await api.get('/api/chat-parser/extractions')
    return response.data
  },
}

// Workflow Generator
export const workflowsAPI = {
  generate: async (config: {
    name: string
    languages: string[]
    include_linting?: boolean
    include_testing?: boolean
    include_security?: boolean
    include_build?: boolean
    include_deploy?: boolean
    deploy_target?: string
  }) => {
    const response = await api.post('/api/workflows/generate', config)
    return response.data
  },

  generateForProject: async (projectId: string, config: any) => {
    const response = await api.post(`/api/workflows/generate-for-project/${projectId}`, config)
    return response.data
  },

  createTemplate: async (data: {
    name: string
    description?: string
    category: string
    template_content: string
    variables?: any
    languages?: string[]
  }) => {
    const response = await api.post('/api/workflows/templates', data)
    return response.data
  },

  listTemplates: async (category?: string) => {
    const response = await api.get('/api/workflows/templates', {
      params: { category },
    })
    return response.data
  },
}

// Code Completion
export const codeCompletionAPI = {
  analyzeCode: async (data: {
    code: string
    language: string
    file_path?: string
  }) => {
    const response = await api.post('/api/code-completion/analyze', data)
    return response.data
  },

  completeFunction: async (data: {
    code: string
    function_name: string
    language: string
    requirements?: string
  }) => {
    const response = await api.post('/api/code-completion/complete-function', data)
    return response.data
  },
}

// Development Wizard
export const wizardAPI = {
  startSession: async (projectId?: string) => {
    const response = await api.post('/api/wizard/start', null, {
      params: { project_id: projectId },
    })
    return response.data
  },

  answerQuestion: async (data: {
    session_id: string
    question_id: string
    answer: string
  }) => {
    const response = await api.post('/api/wizard/answer', data)
    return response.data
  },

  generateScaffolding: async (sessionId: string) => {
    const response = await api.post(`/api/wizard/${sessionId}/generate`)
    return response.data
  },

  getGeneratedFiles: async (sessionId: string) => {
    const response = await api.get(`/api/wizard/${sessionId}/files`)
    return response.data
  },
}

// Agents
export const agentsAPI = {
  create: async (data: any) => {
    const response = await api.post('/api/agents/create', data)
    return response.data
  },

  list: async () => {
    const response = await api.get('/api/agents')
    return response.data
  },

  get: async (agentId: string) => {
    const response = await api.get(`/api/agents/${agentId}`)
    return response.data
  },

  assignTask: async (agentId: string, task: any) => {
    const response = await api.post(`/api/agents/${agentId}/task`, task)
    return response.data
  },

  terminate: async (agentId: string) => {
    const response = await api.delete(`/api/agents/${agentId}`)
    return response.data
  },

  getActivity: async (agentId: string) => {
    const response = await api.get(`/api/agents/${agentId}/activity`)
    return response.data
  },
}

// Projects
export const projectsAPI = {
  create: async (data: any) => {
    const response = await api.post('/api/projects', data)
    return response.data
  },

  list: async () => {
    const response = await api.get('/api/projects')
    return response.data
  },

  get: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}`)
    return response.data
  },

  getFiles: async (projectId: string) => {
    const response = await api.get(`/api/projects/${projectId}/files`)
    return response.data
  },

  saveFile: async (projectId: string, fileData: any) => {
    const response = await api.post(`/api/projects/${projectId}/files`, fileData)
    return response.data
  },

  deleteFile: async (projectId: string, fileId: string) => {
    const response = await api.delete(`/api/projects/${projectId}/files/${fileId}`)
    return response.data
  },
}

// GitHub
export const githubAPI = {
  createRepo: async (data: any) => {
    const response = await api.post('/api/github/repos', data)
    return response.data
  },

  push: async (data: any) => {
    const response = await api.post('/api/github/push', data)
    return response.data
  },

  listRepos: async () => {
    const response = await api.get('/api/github/repos')
    return response.data
  },

  getRepoStatus: async (repoName: string) => {
    const response = await api.get(`/api/github/repos/${repoName}/status`)
    return response.data
  },
}

export default api