/**
 * Extended API Client for CodeForge AI High-Value Features
 * - Project Templates
 * - Export/Import
 * - API Key Management
 * - Code Quality Metrics
 * - Agent Collaboration
 */

import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================
// Types
// ============================================================

// Templates
export interface ProjectTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  language: string;
  framework?: string;
  tags: string[];
  version: string;
  usage_count: number;
  rating: number;
  is_built_in: boolean;
  thumbnail_url?: string;
}

export interface TemplateDetail extends ProjectTemplate {
  files: { path: string; content: string }[];
  dependencies?: Record<string, any>;
  scripts?: Record<string, string>;
  env_template?: string;
  readme_template?: string;
}

export interface CreateFromTemplateRequest {
  template_id: string;
  project_name: string;
  project_description?: string;
  customizations?: Record<string, any>;
}

// API Keys
export interface APIKey {
  id: string;
  name: string;
  provider: string;
  key_prefix: string;
  description?: string;
  environment: string;
  is_active: boolean;
  is_validated: boolean;
  usage_count: number;
  last_used_at?: string;
  expires_at?: string;
  needs_rotation: boolean;
  created_at: string;
}

export interface AddAPIKeyRequest {
  name: string;
  provider: string;
  api_key: string;
  description?: string;
  environment?: string;
  rotation_reminder_days?: number;
}

export interface APIKeyUsageStats {
  key_id: string;
  key_name: string;
  period_days: number;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_response_time_ms: number;
  error_count: number;
  error_rate: number;
  monthly_usage: Record<string, number>;
}

// Code Quality
export interface CodeQualityMetrics {
  project_id: string;
  analyzed_at: string;
  total_files: number;
  total_lines: number;
  code_lines: number;
  language_breakdown: Record<string, number>;
  avg_complexity: number;
  max_complexity: number;
  maintainability_index: number;
  duplication_percentage: number;
  security_score: number;
  overall_score: number;
  grade: string;
  recommendations: {
    category: string;
    priority: string;
    message: string;
    action: string;
  }[];
}

export interface QualityAnalysisResult {
  project_id: string;
  analyzed_at: string;
  summary: {
    total_files: number;
    total_lines: number;
    code_lines: number;
    languages: Record<string, number>;
    overall_score: number;
    grade: string;
  };
  complexity: {
    average: number;
    max: number;
    high_complexity_files: string[];
  };
  duplication: {
    percentage: number;
    blocks_found: number;
  };
  security: {
    score: number;
    issues_found: number;
    critical_issues: any[];
  };
  maintainability: {
    index: number;
    technical_debt_minutes: number;
  };
  recommendations: {
    category: string;
    priority: string;
    message: string;
    action: string;
  }[];
}

// Agent Collaboration
export interface AgentMessage {
  id: string;
  from_agent_id: string;
  to_agent_id: string;
  message_type: string;
  subject?: string;
  content: string;
  metadata?: Record<string, any>;
  thread_id: string;
  status: string;
  priority: string;
  requires_response: boolean;
  created_at: string;
}

export interface SharedContext {
  id: string;
  name: string;
  description?: string;
  context_type: string;
  data: Record<string, any>;
  project_id?: string;
  scope: string;
  participating_agents: string[];
  creator_agent_id: string;
  version: number;
  created_at: string;
}

export interface TaskDelegation {
  id: string;
  parent_agent_id: string;
  child_agent_id: string;
  task_description: string;
  delegation_type: string;
  status: string;
  progress_percentage: number;
}

export interface CollaborationGraph {
  nodes: {
    id: string;
    name: string;
    role: string;
    status: string;
  }[];
  edges: {
    source: string;
    target: string;
    type: string;
    weight?: number;
    status?: string;
  }[];
  stats: {
    total_agents: number;
    total_connections: number;
    active_delegations: number;
  };
}

// ============================================================
// Project Templates API
// ============================================================

export const templatesAPI = {
  list: async (params?: {
    category?: string;
    language?: string;
    framework?: string;
  }): Promise<{ templates: ProjectTemplate[]; total: number }> => {
    const response = await api.get('/api/templates', { params });
    return response.data;
  },

  getCategories: async (): Promise<{
    categories: { id: string; name: string; icon: string }[];
  }> => {
    const response = await api.get('/api/templates/categories');
    return response.data;
  },

  get: async (templateId: string): Promise<TemplateDetail> => {
    const response = await api.get(`/api/templates/${templateId}`);
    return response.data;
  },

  createProject: async (
    request: CreateFromTemplateRequest
  ): Promise<{
    project_id: string;
    name: string;
    files_created: string[];
    template_used: string;
  }> => {
    const response = await api.post('/api/templates/create-project', request);
    return response.data;
  },

  create: async (template: Partial<TemplateDetail>): Promise<{ id: string; name: string; message: string }> => {
    const response = await api.post('/api/templates', template);
    return response.data;
  },
};

// ============================================================
// Export/Import API
// ============================================================

export const exportAPI = {
  exportProject: async (
    projectId: string,
    options?: {
      include_history?: boolean;
      include_metrics?: boolean;
      include_agents?: boolean;
    }
  ): Promise<Blob> => {
    const response = await api.post(
      `/api/export/project/${projectId}`,
      null,
      {
        params: options,
        responseType: 'blob',
      }
    );
    return response.data;
  },

  exportAgent: async (
    agentId: string,
    options?: {
      include_tasks?: boolean;
      include_activities?: boolean;
    }
  ): Promise<any> => {
    const response = await api.post(`/api/export/agent/${agentId}`, null, {
      params: options,
    });
    return response.data;
  },

  bulkExport: async (
    projectIds?: string[],
    agentIds?: string[]
  ): Promise<Blob> => {
    const response = await api.post(
      '/api/export/bulk',
      { project_ids: projectIds, agent_ids: agentIds },
      { responseType: 'blob' }
    );
    return response.data;
  },
};

export const importAPI = {
  importProject: async (
    file: File,
    newName?: string
  ): Promise<{
    project_id: string;
    name: string;
    files_imported: number;
    message: string;
  }> => {
    const formData = new FormData();
    formData.append('file', file);
    if (newName) formData.append('new_name', newName);

    const response = await api.post('/api/import/project', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  importAgent: async (
    file: File
  ): Promise<{
    agent_id: string;
    name: string;
    role: string;
    message: string;
  }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/api/import/agent', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  bulkImport: async (
    file: File
  ): Promise<{
    projects: any[];
    agents: any[];
    errors: any[];
  }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/api/import/bulk', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  validate: async (
    file: File,
    importType: string = 'project'
  ): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/api/import/validate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { import_type: importType },
    });
    return response.data;
  },
};

// ============================================================
// API Keys Management API
// ============================================================

export const apiKeysAPI = {
  list: async (params?: {
    provider?: string;
    environment?: string;
  }): Promise<{ api_keys: APIKey[] }> => {
    const response = await api.get('/api/api-keys', { params });
    return response.data;
  },

  add: async (
    request: AddAPIKeyRequest
  ): Promise<{
    id: string;
    name: string;
    provider: string;
    key_prefix: string;
    is_validated: boolean;
    message: string;
  }> => {
    const response = await api.post('/api/api-keys', request);
    return response.data;
  },

  get: async (
    keyId: string,
    decrypt: boolean = false
  ): Promise<APIKey & { api_key?: string }> => {
    const response = await api.get(`/api/api-keys/${keyId}`, {
      params: { decrypt },
    });
    return response.data;
  },

  update: async (
    keyId: string,
    data: {
      name?: string;
      description?: string;
      new_key?: string;
      is_active?: boolean;
    }
  ): Promise<{ id: string; name: string; message: string }> => {
    const response = await api.put(`/api/api-keys/${keyId}`, data);
    return response.data;
  },

  delete: async (keyId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/api/api-keys/${keyId}`);
    return response.data;
  },

  rotate: async (
    keyId: string,
    newKey: string
  ): Promise<{ id: string; name: string; message: string }> => {
    const response = await api.post(`/api/api-keys/${keyId}/rotate`, null, {
      params: { new_key: newKey },
    });
    return response.data;
  },

  getUsage: async (keyId: string, days: number = 30): Promise<APIKeyUsageStats> => {
    const response = await api.get(`/api/api-keys/${keyId}/usage`, {
      params: { days },
    });
    return response.data;
  },

  getKeysNeedingRotation: async (): Promise<
    {
      id: string;
      name: string;
      provider: string;
      days_since_rotation: number;
      rotation_reminder_days: number;
    }[]
  > => {
    const response = await api.get('/api/api-keys/rotation/needed');
    return response.data;
  },
};

// ============================================================
// Code Quality API
// ============================================================

export const codeQualityAPI = {
  analyze: async (projectId: string): Promise<QualityAnalysisResult> => {
    const response = await api.post(`/api/quality/analyze/${projectId}`);
    return response.data;
  },

  getMetrics: async (projectId: string): Promise<CodeQualityMetrics> => {
    const response = await api.get(`/api/quality/metrics/${projectId}`);
    return response.data;
  },

  getHistory: async (
    projectId: string,
    limit: number = 30
  ): Promise<{
    history: {
      recorded_at: string;
      overall_score: number;
      maintainability_index: number;
      security_score: number;
      total_lines: number;
    }[];
  }> => {
    const response = await api.get(`/api/quality/history/${projectId}`, {
      params: { limit },
    });
    return response.data;
  },

  getReport: async (
    projectId: string,
    format: 'markdown' | 'json' = 'markdown'
  ): Promise<{ report: string; format: string }> => {
    const response = await api.get(`/api/quality/report/${projectId}`, {
      params: { format },
    });
    return response.data;
  },
};

// ============================================================
// Agent Collaboration API
// ============================================================

export const collaborationAPI = {
  // Messages
  sendMessage: async (data: {
    from_agent_id: string;
    to_agent_id: string;
    message_type: string;
    content: string;
    subject?: string;
    metadata?: Record<string, any>;
    priority?: string;
    requires_response?: boolean;
  }): Promise<{ message_id: string; thread_id: string; status: string }> => {
    const response = await api.post('/api/collaboration/messages', data);
    return response.data;
  },

  getMessages: async (
    agentId: string,
    params?: {
      direction?: 'received' | 'sent' | 'all';
      message_type?: string;
      status?: string;
      limit?: number;
    }
  ): Promise<{ messages: AgentMessage[] }> => {
    const response = await api.get(`/api/collaboration/messages/${agentId}`, {
      params,
    });
    return response.data;
  },

  replyToMessage: async (
    messageId: string,
    fromAgentId: string,
    content: string
  ): Promise<{ message_id: string; thread_id: string; status: string }> => {
    const response = await api.post(
      `/api/collaboration/messages/${messageId}/reply`,
      null,
      { params: { from_agent_id: fromAgentId, content } }
    );
    return response.data;
  },

  // Shared Context
  createContext: async (data: {
    name: string;
    context_type: string;
    data: Record<string, any>;
    creator_agent_id: string;
    project_id?: string;
    participating_agents?: string[];
    description?: string;
    expires_in_hours?: number;
  }): Promise<{ context_id: string; name: string; context_type: string; message: string }> => {
    const response = await api.post('/api/collaboration/context', data);
    return response.data;
  },

  getContext: async (contextId: string): Promise<SharedContext> => {
    const response = await api.get(`/api/collaboration/context/${contextId}`);
    return response.data;
  },

  listContexts: async (params?: {
    agent_id?: string;
    project_id?: string;
    context_type?: string;
  }): Promise<{ contexts: Partial<SharedContext>[] }> => {
    const response = await api.get('/api/collaboration/context', { params });
    return response.data;
  },

  // Task Delegation
  delegateTask: async (data: {
    parent_agent_id: string;
    child_agent_id: string;
    task_description: string;
    delegation_type?: string;
    instructions?: string;
    reason?: string;
  }): Promise<{ delegation_id: string; task_id: string; status: string }> => {
    const response = await api.post('/api/collaboration/delegate', data);
    return response.data;
  },

  acceptDelegation: async (
    delegationId: string,
    accepted: boolean,
    reason?: string
  ): Promise<{ delegation_id: string; accepted: boolean; status: string }> => {
    const response = await api.post(
      `/api/collaboration/delegate/${delegationId}/accept`,
      null,
      { params: { accepted, reason } }
    );
    return response.data;
  },

  updateDelegationProgress: async (
    delegationId: string,
    progress: number
  ): Promise<{ status: string; progress: number }> => {
    const response = await api.post(
      `/api/collaboration/delegate/${delegationId}/progress`,
      null,
      { params: { progress } }
    );
    return response.data;
  },

  // Code Review
  requestReview: async (data: {
    author_agent_id: string;
    reviewer_agent_id: string;
    project_id: string;
    files: { path: string; content: string; diff?: string }[];
    context?: string;
    focus_areas?: string[];
    urgency?: string;
  }): Promise<{ review_id: string; status: string }> => {
    const response = await api.post('/api/collaboration/code-review', data);
    return response.data;
  },

  submitReview: async (data: {
    review_id: string;
    approval_status: string;
    overall_feedback: string;
    comments?: { file: string; line: number; comment: string; severity: string }[];
    suggested_changes?: any[];
  }): Promise<{ review_id: string; approval_status: string; status: string }> => {
    const response = await api.post(
      `/api/collaboration/code-review/${data.review_id}/submit`,
      data
    );
    return response.data;
  },

  // Collaboration Graph
  getGraph: async (projectId?: string): Promise<CollaborationGraph> => {
    const response = await api.get('/api/collaboration/graph', {
      params: { project_id: projectId },
    });
    return response.data;
  },
};

// Download helper for exports
export const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};
