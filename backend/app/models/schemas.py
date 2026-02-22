from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    model: Optional[str] = Field(None, description="Model to use")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(4096, gt=0)
    context: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    use_local_llm: Optional[bool] = Field(False, description="Use local LLM instead of Venice API")


class SystemPromptUpdate(BaseModel):
    name: str
    content: str
    category: Optional[str] = "general"
    is_active: Optional[bool] = True


class ProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    framework: Optional[str] = None


class AgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., description="Agent role/specialty")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    system_prompt: str = Field(..., description="Custom system prompt")
    system_prompt_id: Optional[str] = Field(None, description="ID of predefined system prompt")
    parent_id: Optional[str] = None


class GitHubRepoRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = ""
    private: bool = False


class FileData(BaseModel):
    path: str
    content: str


class PushToGitHubRequest(BaseModel):
    repo_name: str
    files: List[FileData]
    commit_message: str
    branch: Optional[str] = "main"


# ==================== Local LLM Schemas ====================

class LocalLLMConfigRequest(BaseModel):
    """Request to configure a local LLM"""
    name: str = Field(..., min_length=1, max_length=255)
    model_id: str = Field(..., description="HuggingFace model ID")
    device: Optional[str] = Field("auto", description="Device to use: cuda, cpu, auto")
    quantization: Optional[str] = Field(None, description="Quantization: 4bit, 8bit, none")
    max_context_length: Optional[int] = Field(8192, gt=0)
    default_temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    default_top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0)
    default_max_tokens: Optional[int] = Field(2048, gt=0)


class LocalLLMGenerateRequest(BaseModel):
    """Request to generate text with local LLM"""
    prompt: str = Field(..., description="The prompt to generate from")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(2048, gt=0)
    stop_sequences: Optional[List[str]] = None


class LocalLLMStatusResponse(BaseModel):
    """Response for local LLM status"""
    is_loaded: bool
    cuda_available: bool
    cuda_device_count: int
    model_id: Optional[str] = None
    device: Optional[str] = None
    quantization: Optional[str] = None
    gpu_memory_allocated: Optional[str] = None
    gpu_memory_reserved: Optional[str] = None


# ==================== Chat Parser Schemas ====================

class ChatParserRequest(BaseModel):
    """Request to parse a chat document"""
    file_type: Optional[str] = Field(None, description="File type: docx, pdf, txt, html, md")


class ExtractedCodeBlock(BaseModel):
    """An extracted code block"""
    content: str
    language: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    confidence: float = 1.0


class ChatExtractionResponse(BaseModel):
    """Response from chat parsing"""
    success: bool
    extraction_id: Optional[str] = None
    files: Dict[str, str] = {}
    code_blocks_count: int = 0
    languages_detected: List[str] = []
    source_format: Optional[str] = None
    readme_content: Optional[str] = None
    error: Optional[str] = None


class CreateProjectFromExtractionRequest(BaseModel):
    """Request to create project from extraction"""
    extraction_id: str
    project_name: str


# ==================== Workflow Generator Schemas ====================

class WorkflowCategory(str, Enum):
    LINTING = "linting"
    TESTING = "testing"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    CUSTOM = "custom"


class WorkflowConfigRequest(BaseModel):
    """Request to generate workflows"""
    name: str = Field(..., min_length=1, max_length=255)
    languages: List[str] = Field(..., description="Target programming languages")
    include_linting: bool = True
    include_testing: bool = True
    include_security: bool = True
    include_build: bool = True
    include_deploy: bool = False
    node_version: str = "18"
    python_version: str = "3.11"
    go_version: str = "1.21"
    java_version: str = "17"
    deploy_target: Optional[str] = Field(None, description="Deploy target: vercel, docker, aws")
    custom_steps: Optional[List[Dict[str, Any]]] = None


class WorkflowGenerateResponse(BaseModel):
    """Response from workflow generation"""
    success: bool
    workflows: List[str] = []
    languages_detected: List[str] = []
    error: Optional[str] = None


class WorkflowTemplateRequest(BaseModel):
    """Request to create a workflow template"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: WorkflowCategory
    template_content: str = Field(..., description="YAML template content")
    variables: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None


# ==================== Code Completion Schemas ====================

class CodeAnalysisRequest(BaseModel):
    """Request to analyze code for completion"""
    code: str = Field(..., description="Code to analyze")
    language: str = Field(..., description="Programming language")
    file_path: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class MissingFunctionResponse(BaseModel):
    """A missing function identified in code"""
    name: str
    file_path: str
    line_number: int
    signature: Optional[str] = None
    context: Optional[str] = None


class CodeAnalysisResponse(BaseModel):
    """Response from code analysis"""
    missing_functions: List[MissingFunctionResponse]
    incomplete_sections: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    analysis_summary: Dict[str, Any]


class CompleteFunctionRequest(BaseModel):
    """Request to complete a specific function"""
    code: str = Field(..., description="Existing code context")
    function_name: str = Field(..., description="Name of function to complete")
    language: str = Field(..., description="Programming language")
    requirements: Optional[str] = Field(None, description="Additional requirements")


class CompletionResponse(BaseModel):
    """Response from function completion"""
    success: bool
    implementation: Optional[str] = None
    function_name: Optional[str] = None
    language: Optional[str] = None
    error: Optional[str] = None


# ==================== Development Wizard Schemas ====================

class WizardQuestionResponse(BaseModel):
    """A question from the development wizard"""
    id: str
    question: str
    options: Optional[List[str]] = None
    depends_on: Optional[str] = None
    phase: Optional[str] = None
    message: Optional[str] = None


class WizardAnswerRequest(BaseModel):
    """Request to answer a wizard question"""
    session_id: str
    question_id: str
    answer: str


class WizardSessionResponse(BaseModel):
    """Response with wizard session info"""
    session_id: str
    phase: str
    decisions_count: int
    next_question: Optional[WizardQuestionResponse] = None


class WizardScaffoldingResponse(BaseModel):
    """Response from scaffolding generation"""
    success: bool
    files: List[str] = []
    total_files: int = 0
    decisions_applied: int = 0
    error: Optional[str] = None


# ==================== Combined AI Request ====================

class AIProvider(str, Enum):
    VENICE = "venice"
    LOCAL = "local"


class UnifiedChatRequest(BaseModel):
    """Unified chat request supporting both Venice API and local LLM"""
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    provider: AIProvider = Field(AIProvider.VENICE, description="AI provider to use")
    model: Optional[str] = Field(None, description="Model to use (for Venice)")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    system_prompt_id: Optional[str] = Field(None, description="Predefined system prompt ID")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(4096, gt=0)
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0)
    context: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = Field(True, description="Stream response")


# ==================== Response Models ====================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None