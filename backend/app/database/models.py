from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid


class Project(Base):
    """Project model"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    framework = Column(String(100))
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")
    prompts = relationship("Prompt", back_populates="project", cascade="all, delete-orphan")


class File(Base):
    """File model"""
    __tablename__ = "files"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    path = Column(String(500), nullable=False)
    content = Column(Text)
    language = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="files")


class AgentModel(Base):
    """Agent model"""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    capabilities = Column(JSON)
    system_prompt = Column(Text)
    parent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"))
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    terminated_at = Column(DateTime(timezone=True))
    
    # Relationships
    children = relationship("AgentModel", remote_side=[id], cascade="all, delete-orphan")
    tasks = relationship("TaskModel", back_populates="agent", cascade="all, delete-orphan")


class TaskModel(Base):
    """Task model"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(100), nullable=False)
    description = Column(Text)
    data = Column(JSON)
    status = Column(String(50), default="pending")
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    agent = relationship("AgentModel", back_populates="tasks")


class Prompt(Base):
    """Prompt/Interaction model"""
    __tablename__ = "prompts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"))
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text)
    model_used = Column(String(100))
    tokens_used = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="prompts")


class SystemPrompt(Base):
    """System Prompt configuration"""
    __tablename__ = "system_prompts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GeneratedCode(Base):
    """Generated code log"""
    __tablename__ = "generated_code"
    
    id = Column(String, primary_key=True)
    raw_response = Column(Text)
    code_blocks = Column(JSON)
    language = Column(String(50))
    timestamp = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentActivity(Base):
    """Agent activity log"""
    __tablename__ = "agent_activities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(String(100), nullable=False)
    description = Column(Text)
    activity_data = Column(JSON)  # Renamed from 'metadata' - reserved in SQLAlchemy
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class LocalLLMConfig(Base):
    """Local LLM configuration"""
    __tablename__ = "local_llm_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    model_id = Column(String(500), nullable=False)  # HuggingFace model ID
    model_path = Column(String(1000))  # Local path if downloaded
    is_downloaded = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    device = Column(String(50), default="auto")  # cuda, cpu, auto
    quantization = Column(String(50))  # 4bit, 8bit, none
    max_context_length = Column(Integer, default=8192)
    default_temperature = Column(String(10), default="0.7")
    default_top_p = Column(String(10), default="0.9")
    default_max_tokens = Column(Integer, default=2048)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChatExtraction(Base):
    """Chat extraction records"""
    __tablename__ = "chat_extractions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # docx, pdf, txt, html, md
    source_format = Column(String(100))  # ChatGPT, Claude, Gemini, etc.
    extracted_files = Column(JSON)  # List of extracted file paths and content
    project_structure = Column(JSON)  # Reconstructed project structure
    code_blocks_count = Column(Integer, default=0)
    languages_detected = Column(JSON)  # List of detected languages
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    project_id = Column(String, ForeignKey("projects.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class WorkflowTemplate(Base):
    """GitHub Actions workflow templates"""
    __tablename__ = "workflow_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)  # linting, testing, security, deployment, custom
    template_content = Column(Text, nullable=False)  # YAML template
    variables = Column(JSON)  # Template variables for customization
    languages = Column(JSON)  # Supported languages
    is_built_in = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CodeCompletionSession(Base):
    """Code completion and interactive development sessions"""
    __tablename__ = "code_completion_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"))
    session_type = Column(String(100), nullable=False)  # completion, wizard, refactor
    status = Column(String(50), default="active")  # active, paused, completed
    conversation_history = Column(JSON)  # Developer-AI conversation
    decisions_made = Column(JSON)  # Architecture, patterns, standards decisions
    generated_artifacts = Column(JSON)  # List of generated files/tests/docs
    missing_functions = Column(JSON)  # Identified missing functions
    completion_progress = Column(Integer, default=0)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())