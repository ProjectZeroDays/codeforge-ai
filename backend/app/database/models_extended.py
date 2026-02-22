"""
Extended Database Models for CodeForge AI High-Value Features
- Project Templates Library
- API Key Management
- Code Quality Metrics
- Agent Collaboration
- Export/Import
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid
import enum


# ============================================================
# Project Templates Library
# ============================================================

class TemplateCategory(enum.Enum):
    REST_API = "rest_api"
    WEB_APP = "web_app"
    CLI_TOOL = "cli_tool"
    MICROSERVICE = "microservice"
    DATA_SCIENCE = "data_science"
    MACHINE_LEARNING = "machine_learning"
    FULLSTACK = "fullstack"
    LIBRARY = "library"
    OTHER = "other"


class ProjectTemplate(Base):
    """Pre-built project templates"""
    __tablename__ = "project_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)  # rest_api, web_app, cli_tool, etc.
    language = Column(String(100), nullable=False)  # python, javascript, typescript, go, etc.
    framework = Column(String(100))  # fastapi, express, nextjs, flask, etc.
    tags = Column(JSON)  # ["api", "auth", "database"]
    
    # Template structure
    files = Column(JSON, nullable=False)  # List of {path, content, is_binary}
    dependencies = Column(JSON)  # Package dependencies
    scripts = Column(JSON)  # Build/run scripts
    env_template = Column(Text)  # .env template
    readme_template = Column(Text)  # README.md template
    
    # Metadata
    version = Column(String(50), default="1.0.0")
    author = Column(String(255), default="CodeForge AI")
    repository_url = Column(String(500))
    documentation_url = Column(String(500))
    thumbnail_url = Column(String(500))
    
    # Usage stats
    usage_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    is_built_in = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# API Key Management
# ============================================================

class APIKeyProvider(enum.Enum):
    VENICE_AI = "venice_ai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GITHUB = "github"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class APIKey(Base):
    """Securely stored API keys with encryption"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)  # User-friendly name
    provider = Column(String(100), nullable=False)  # venice_ai, openai, github, etc.
    
    # Encrypted key storage (encrypted with Fernet)
    encrypted_key = Column(Text, nullable=False)
    key_hash = Column(String(64))  # SHA256 hash for verification
    key_prefix = Column(String(10))  # First few chars for identification
    
    # Metadata
    description = Column(Text)
    environment = Column(String(50), default="production")  # production, development, testing
    
    # Rotation and expiry
    expires_at = Column(DateTime(timezone=True))
    last_rotated_at = Column(DateTime(timezone=True))
    rotation_reminder_days = Column(Integer, default=90)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    monthly_usage = Column(JSON)  # {"2024-01": 150, "2024-02": 200}
    
    # Status
    is_active = Column(Boolean, default=True)
    is_validated = Column(Boolean, default=False)
    validation_error = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class APIKeyUsageLog(Base):
    """Detailed API key usage tracking"""
    __tablename__ = "api_key_usage_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    
    endpoint = Column(String(500))
    method = Column(String(10))  # GET, POST, etc.
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    tokens_used = Column(Integer)
    cost_estimate = Column(Float)
    error_message = Column(Text)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Code Quality Metrics
# ============================================================

class CodeQualityMetrics(Base):
    """Code quality analysis results"""
    __tablename__ = "code_quality_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Basic metrics
    total_files = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    code_lines = Column(Integer, default=0)
    comment_lines = Column(Integer, default=0)
    blank_lines = Column(Integer, default=0)
    
    # Language distribution
    language_breakdown = Column(JSON)  # {"python": 1500, "javascript": 800}
    
    # Complexity metrics
    avg_cyclomatic_complexity = Column(Float)
    max_cyclomatic_complexity = Column(Integer)
    complexity_by_file = Column(JSON)  # {"path": complexity}
    
    # Maintainability
    maintainability_index = Column(Float)  # 0-100 scale
    technical_debt_minutes = Column(Integer)
    
    # Code duplication
    duplication_percentage = Column(Float)
    duplicated_blocks = Column(JSON)  # List of duplicated code blocks
    
    # Security vulnerabilities
    security_issues = Column(JSON)  # List of detected issues
    security_score = Column(Integer)  # 0-100
    
    # Dependencies
    total_dependencies = Column(Integer)
    outdated_dependencies = Column(JSON)
    vulnerable_dependencies = Column(JSON)
    
    # Test coverage (if available)
    test_coverage_percentage = Column(Float)
    
    # Overall score
    overall_score = Column(Integer)  # 0-100
    grade = Column(String(2))  # A+, A, B+, B, C+, C, D, F
    
    # Recommendations
    recommendations = Column(JSON)  # List of improvement suggestions
    
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CodeQualityHistory(Base):
    """Track metrics over time"""
    __tablename__ = "code_quality_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    overall_score = Column(Integer)
    maintainability_index = Column(Float)
    security_score = Column(Integer)
    test_coverage = Column(Float)
    total_lines = Column(Integer)
    
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Agent Collaboration
# ============================================================

class AgentMessage(Base):
    """Agent-to-agent communication"""
    __tablename__ = "agent_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    from_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    to_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    message_type = Column(String(50), nullable=False)  # task_delegation, code_review, context_share, query, response
    subject = Column(String(255))
    content = Column(Text, nullable=False)
    message_data = Column(JSON)  # Renamed from 'metadata' - reserved in SQLAlchemy
    
    # Thread tracking
    thread_id = Column(String)  # For conversation threading
    parent_message_id = Column(String, ForeignKey("agent_messages.id", ondelete="SET NULL"))
    
    # Status
    status = Column(String(50), default="sent")  # sent, delivered, read, processed, error
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Response tracking
    requires_response = Column(Boolean, default=False)
    response_id = Column(String)
    responded_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    replies = relationship("AgentMessage", 
                          remote_side=[id],
                          backref="parent_message")


class SharedContext(Base):
    """Shared memory/context between agents"""
    __tablename__ = "shared_contexts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Context data
    context_type = Column(String(100), nullable=False)  # project, codebase, architecture, requirements, decisions
    data = Column(JSON, nullable=False)  # The actual shared context
    
    # Scope
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"))
    scope = Column(String(50), default="project")  # project, global, team
    
    # Participating agents
    participating_agents = Column(JSON)  # List of agent IDs with access
    creator_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"))
    
    # Versioning
    version = Column(Integer, default=1)
    previous_version_id = Column(String)
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskDelegation(Base):
    """Task delegation tracking between agents"""
    __tablename__ = "task_delegations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    parent_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    child_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    original_task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"))
    delegated_task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"))
    
    delegation_type = Column(String(50), nullable=False)  # full, partial, assistance
    reason = Column(Text)  # Why the task was delegated
    instructions = Column(Text)  # Specific instructions for the child
    
    # Acceptance
    accepted = Column(Boolean)
    acceptance_reason = Column(Text)
    
    # Progress
    status = Column(String(50), default="pending")  # pending, accepted, in_progress, completed, rejected
    progress_percentage = Column(Integer, default=0)
    
    # Results
    result_summary = Column(Text)
    artifacts = Column(JSON)  # Files or outputs created
    
    delegated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class CodeReviewRequest(Base):
    """Collaborative code review requests between agents"""
    __tablename__ = "code_review_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    author_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    reviewer_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"))
    
    # Code to review
    files = Column(JSON, nullable=False)  # List of {path, content, diff}
    context = Column(Text)  # What the code does, why changes were made
    
    # Review parameters
    focus_areas = Column(JSON)  # ["security", "performance", "readability"]
    urgency = Column(String(20), default="normal")
    
    # Status
    status = Column(String(50), default="pending")  # pending, in_review, completed, approved, changes_requested
    
    # Review results
    review_comments = Column(JSON)  # List of {file, line, comment, severity}
    overall_feedback = Column(Text)
    approval_status = Column(String(50))  # approved, changes_requested, needs_discussion
    suggested_changes = Column(JSON)  # Suggested code modifications
    
    # Merge conflict resolution
    has_conflicts = Column(Boolean, default=False)
    conflict_resolution = Column(JSON)  # AI-suggested resolution
    
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True))


# ============================================================
# Export/Import
# ============================================================

class ExportRecord(Base):
    """Track project and agent exports"""
    __tablename__ = "export_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    export_type = Column(String(50), nullable=False)  # project, agent, bulk, backup
    
    # What was exported
    project_id = Column(String, ForeignKey("projects.id", ondelete="SET NULL"))
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"))
    items = Column(JSON)  # For bulk exports, list of item IDs
    
    # Export details
    format = Column(String(20), nullable=False)  # zip, json, tar
    filename = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer)
    file_path = Column(String(1000))  # Temporary path for download
    
    # Export configuration
    include_history = Column(Boolean, default=False)
    include_metrics = Column(Boolean, default=False)
    include_agents = Column(Boolean, default=False)
    
    # Manifest
    manifest = Column(JSON)  # Summary of exported content
    
    # Status
    status = Column(String(50), default="pending")  # pending, processing, ready, downloaded, expired
    error_message = Column(Text)
    
    expires_at = Column(DateTime(timezone=True))  # When the download link expires
    downloaded_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImportRecord(Base):
    """Track imports"""
    __tablename__ = "import_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    import_type = Column(String(50), nullable=False)  # project, agent, bulk, backup
    
    # Source
    source_filename = Column(String(500), nullable=False)
    source_format = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer)
    
    # Import results
    created_project_id = Column(String, ForeignKey("projects.id", ondelete="SET NULL"))
    created_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"))
    created_items = Column(JSON)  # List of created items for bulk imports
    
    # Validation
    validation_passed = Column(Boolean)
    validation_errors = Column(JSON)
    
    # Status
    status = Column(String(50), default="pending")  # pending, validating, importing, completed, failed
    error_message = Column(Text)
    
    # Summary
    import_summary = Column(JSON)  # What was imported
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
