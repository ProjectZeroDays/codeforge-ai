"""
Extended API Routes for High-Value Features
- Project Templates
- Export/Import
- API Key Management
- Code Quality Metrics
- Agent Collaboration
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import json
from io import BytesIO

from app.database.connection import get_db

# ============================================================
# Pydantic Models for API
# ============================================================

# Templates
class TemplateListResponse(BaseModel):
    templates: List[Dict[str, Any]]
    total: int

class CreateFromTemplateRequest(BaseModel):
    template_id: str
    project_name: str
    project_description: Optional[str] = None
    customizations: Optional[Dict[str, Any]] = None

class CreateTemplateRequest(BaseModel):
    name: str
    description: str
    category: str
    language: str
    framework: Optional[str] = None
    files: List[Dict[str, Any]]
    tags: Optional[List[str]] = None
    dependencies: Optional[Dict[str, Any]] = None

# API Keys
class AddAPIKeyRequest(BaseModel):
    name: str
    provider: str
    api_key: str
    description: Optional[str] = None
    environment: str = "production"
    rotation_reminder_days: int = 90

class UpdateAPIKeyRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    new_key: Optional[str] = None
    is_active: Optional[bool] = None

# Export/Import
class ExportProjectRequest(BaseModel):
    project_id: str
    include_history: bool = False
    include_metrics: bool = False
    include_agents: bool = False

class BulkExportRequest(BaseModel):
    project_ids: Optional[List[str]] = None
    agent_ids: Optional[List[str]] = None

# Code Quality
class AnalyzeProjectRequest(BaseModel):
    project_id: str

# Agent Collaboration
class SendMessageRequest(BaseModel):
    from_agent_id: str
    to_agent_id: str
    message_type: str
    content: str
    subject: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: str = "normal"
    requires_response: bool = False

class CreateSharedContextRequest(BaseModel):
    name: str
    context_type: str
    data: Dict[str, Any]
    creator_agent_id: str
    project_id: Optional[str] = None
    participating_agents: Optional[List[str]] = None
    description: Optional[str] = None
    expires_in_hours: Optional[int] = None

class DelegateTaskRequest(BaseModel):
    parent_agent_id: str
    child_agent_id: str
    task_description: str
    delegation_type: str = "full"
    instructions: Optional[str] = None
    reason: Optional[str] = None

class CodeReviewRequest(BaseModel):
    author_agent_id: str
    reviewer_agent_id: str
    project_id: str
    files: List[Dict[str, Any]]
    context: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    urgency: str = "normal"

class SubmitReviewRequest(BaseModel):
    review_id: str
    approval_status: str
    overall_feedback: str
    comments: Optional[List[Dict[str, Any]]] = None
    suggested_changes: Optional[List[Dict[str, Any]]] = None

# ============================================================
# Routers
# ============================================================

templates_router = APIRouter(prefix="/api/templates", tags=["Project Templates"])
export_router = APIRouter(prefix="/api/export", tags=["Export"])
import_router = APIRouter(prefix="/api/import", tags=["Import"])
api_keys_router = APIRouter(prefix="/api/api-keys", tags=["API Keys"])
quality_router = APIRouter(prefix="/api/quality", tags=["Code Quality"])
collaboration_router = APIRouter(prefix="/api/collaboration", tags=["Agent Collaboration"])

# ============================================================
# Project Templates Endpoints
# ============================================================

@templates_router.get("/")
async def list_templates(
    category: Optional[str] = None,
    language: Optional[str] = None,
    framework: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List available project templates"""
    from app.services.templates_service import ProjectTemplatesService
    
    service = ProjectTemplatesService()
    templates = await service.list_templates(db, category, language, framework)
    
    return {
        "templates": templates,
        "total": len(templates)
    }

@templates_router.get("/categories")
async def get_categories():
    """Get available template categories"""
    return {
        "categories": [
            {"id": "rest_api", "name": "REST API", "icon": "api"},
            {"id": "web_app", "name": "Web Application", "icon": "globe"},
            {"id": "cli_tool", "name": "CLI Tool", "icon": "terminal"},
            {"id": "microservice", "name": "Microservice", "icon": "box"},
            {"id": "data_science", "name": "Data Science", "icon": "chart"},
            {"id": "machine_learning", "name": "Machine Learning", "icon": "brain"},
            {"id": "fullstack", "name": "Full-Stack", "icon": "layers"},
            {"id": "library", "name": "Library/Package", "icon": "package"}
        ]
    }

@templates_router.get("/{template_id}")
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific template by ID"""
    from app.services.templates_service import ProjectTemplatesService
    
    service = ProjectTemplatesService()
    template = await service.get_template(db, template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

@templates_router.post("/create-project")
async def create_project_from_template(
    request: CreateFromTemplateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project from a template"""
    from app.services.templates_service import ProjectTemplatesService
    
    service = ProjectTemplatesService()
    
    try:
        result = await service.create_project_from_template(
            db,
            request.template_id,
            request.project_name,
            request.project_description,
            request.customizations
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@templates_router.post("/")
async def create_template(
    request: CreateTemplateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a custom template"""
    from app.services.templates_service import ProjectTemplatesService
    
    service = ProjectTemplatesService()
    result = await service.create_custom_template(
        db,
        request.name,
        request.description,
        request.category,
        request.language,
        request.files,
        request.framework,
        request.tags,
        request.dependencies
    )
    return result

# ============================================================
# Export Endpoints
# ============================================================

@export_router.post("/project/{project_id}")
async def export_project(
    project_id: str,
    include_history: bool = False,
    include_metrics: bool = False,
    include_agents: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Export a project as a ZIP file"""
    from app.services.export_import_service import ExportService
    
    service = ExportService()
    
    try:
        zip_buffer = await service.export_project(
            db, project_id, include_history, include_metrics, include_agents
        )
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="project_{project_id}.zip"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@export_router.post("/agent/{agent_id}")
async def export_agent(
    agent_id: str,
    include_tasks: bool = True,
    include_activities: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Export an agent as JSON"""
    from app.services.export_import_service import ExportService
    
    service = ExportService()
    
    try:
        result = await service.export_agent(db, agent_id, include_tasks, include_activities)
        return JSONResponse(
            content=result,
            headers={
                "Content-Disposition": f'attachment; filename="agent_{agent_id}.json"'
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@export_router.post("/bulk")
async def bulk_export(
    request: BulkExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk export multiple projects and agents"""
    from app.services.export_import_service import ExportService
    
    service = ExportService()
    zip_buffer = await service.bulk_export(db, request.project_ids, request.agent_ids)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="codeforge_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        }
    )

# ============================================================
# Import Endpoints
# ============================================================

@import_router.post("/project")
async def import_project(
    file: UploadFile = File(...),
    new_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Import a project from a ZIP file"""
    from app.services.export_import_service import ImportService
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    contents = await file.read()
    zip_buffer = BytesIO(contents)
    
    service = ImportService()
    
    try:
        result = await service.import_project(db, zip_buffer, new_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@import_router.post("/agent")
async def import_agent(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Import an agent from a JSON file"""
    from app.services.export_import_service import ImportService
    
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    contents = await file.read()
    agent_data = json.loads(contents.decode())
    
    service = ImportService()
    
    try:
        result = await service.import_agent(db, agent_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@import_router.post("/bulk")
async def bulk_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Import from a bulk export ZIP"""
    from app.services.export_import_service import ImportService
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    contents = await file.read()
    zip_buffer = BytesIO(contents)
    
    service = ImportService()
    result = await service.bulk_import(db, zip_buffer)
    
    return result

@import_router.post("/validate")
async def validate_import(
    file: UploadFile = File(...),
    import_type: str = "project"
):
    """Validate an import file before importing"""
    from app.services.export_import_service import ImportService
    
    contents = await file.read()
    file_buffer = BytesIO(contents)
    
    service = ImportService()
    result = await service.validate_import(file_buffer, import_type)
    
    return result

# ============================================================
# API Keys Endpoints
# ============================================================

@api_keys_router.get("/")
async def list_api_keys(
    provider: Optional[str] = None,
    environment: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all API keys (without showing actual keys)"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    keys = await service.list_api_keys(db, provider, environment)
    
    return {"api_keys": keys}

@api_keys_router.post("/")
async def add_api_key(
    request: AddAPIKeyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add a new API key"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    result = await service.add_api_key(
        db,
        request.name,
        request.provider,
        request.api_key,
        request.description,
        request.environment,
        rotation_reminder_days=request.rotation_reminder_days
    )
    
    return result

@api_keys_router.get("/{key_id}")
async def get_api_key(
    key_id: str,
    decrypt: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get an API key by ID"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    key = await service.get_api_key(db, key_id, decrypt)
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return key

@api_keys_router.put("/{key_id}")
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update an API key"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    
    try:
        result = await service.update_api_key(
            db, key_id,
            request.name,
            request.description,
            request.new_key,
            request.is_active
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@api_keys_router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    return await service.delete_api_key(db, key_id)

@api_keys_router.post("/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    new_key: str,
    db: AsyncSession = Depends(get_db)
):
    """Rotate an API key"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    return await service.rotate_key(db, key_id, new_key)

@api_keys_router.get("/{key_id}/usage")
async def get_api_key_usage(
    key_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics for an API key"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    stats = await service.get_usage_stats(db, key_id, days)
    
    if not stats:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return stats

@api_keys_router.get("/rotation/needed")
async def get_keys_needing_rotation(db: AsyncSession = Depends(get_db)):
    """Get API keys that need rotation"""
    from app.services.api_keys_service import APIKeyService
    
    service = APIKeyService()
    return await service.get_keys_needing_rotation(db)

# ============================================================
# Code Quality Endpoints
# ============================================================

@quality_router.post("/analyze/{project_id}")
async def analyze_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Analyze code quality for a project"""
    from app.services.code_quality_service import CodeQualityService
    
    service = CodeQualityService()
    
    try:
        result = await service.analyze_project(db, project_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@quality_router.get("/metrics/{project_id}")
async def get_metrics(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the latest quality metrics for a project"""
    from app.services.code_quality_service import CodeQualityService
    
    service = CodeQualityService()
    metrics = await service.get_metrics(db, project_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found. Run analysis first.")
    
    return metrics

@quality_router.get("/history/{project_id}")
async def get_metrics_history(
    project_id: str,
    limit: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get historical quality metrics"""
    from app.services.code_quality_service import CodeQualityService
    
    service = CodeQualityService()
    history = await service.get_metrics_history(db, project_id, limit)
    
    return {"history": history}

@quality_router.get("/report/{project_id}")
async def get_quality_report(
    project_id: str,
    format: str = "markdown",
    db: AsyncSession = Depends(get_db)
):
    """Generate a quality report"""
    from app.services.code_quality_service import CodeQualityService
    
    service = CodeQualityService()
    report = await service.generate_report(db, project_id, format)
    
    return {"report": report, "format": format}

# ============================================================
# Agent Collaboration Endpoints
# ============================================================

@collaboration_router.post("/messages")
async def send_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a message from one agent to another"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    result = await service.send_message(
        db,
        request.from_agent_id,
        request.to_agent_id,
        request.message_type,
        request.content,
        request.subject,
        request.metadata,
        request.priority,
        request.requires_response
    )
    
    return result

@collaboration_router.get("/messages/{agent_id}")
async def get_messages(
    agent_id: str,
    direction: str = "received",
    message_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get messages for an agent"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    messages = await service.get_messages(db, agent_id, direction, message_type, status, limit=limit)
    
    return {"messages": messages}

@collaboration_router.post("/messages/{message_id}/reply")
async def reply_to_message(
    message_id: str,
    from_agent_id: str,
    content: str,
    db: AsyncSession = Depends(get_db)
):
    """Reply to a message"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    return await service.reply_to_message(db, message_id, from_agent_id, content)

@collaboration_router.post("/context")
async def create_shared_context(
    request: CreateSharedContextRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a shared context"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    return await service.create_shared_context(
        db,
        request.name,
        request.context_type,
        request.data,
        request.creator_agent_id,
        request.project_id,
        request.participating_agents,
        request.description,
        request.expires_in_hours
    )

@collaboration_router.get("/context/{context_id}")
async def get_shared_context(
    context_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a shared context"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    context = await service.get_shared_context(db, context_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Context not found or expired")
    
    return context

@collaboration_router.get("/context")
async def list_shared_contexts(
    agent_id: Optional[str] = None,
    project_id: Optional[str] = None,
    context_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List shared contexts"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    contexts = await service.list_shared_contexts(db, agent_id, project_id, context_type)
    
    return {"contexts": contexts}

@collaboration_router.post("/delegate")
async def delegate_task(
    request: DelegateTaskRequest,
    db: AsyncSession = Depends(get_db)
):
    """Delegate a task to another agent"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    return await service.delegate_task(
        db,
        request.parent_agent_id,
        request.child_agent_id,
        request.task_description,
        request.delegation_type,
        instructions=request.instructions,
        reason=request.reason
    )

@collaboration_router.post("/delegate/{delegation_id}/accept")
async def accept_delegation(
    delegation_id: str,
    accepted: bool,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Accept or reject a task delegation"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    return await service.accept_delegation(db, delegation_id, accepted, reason)

@collaboration_router.post("/delegate/{delegation_id}/progress")
async def update_delegation_progress(
    delegation_id: str,
    progress: int,
    db: AsyncSession = Depends(get_db)
):
    """Update progress on a delegated task"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    await service.update_delegation_progress(db, delegation_id, progress)
    return {"status": "updated", "progress": progress}

@collaboration_router.post("/code-review")
async def request_code_review(
    request: CodeReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request a code review from another agent"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    return await service.request_code_review(
        db,
        request.author_agent_id,
        request.reviewer_agent_id,
        request.project_id,
        request.files,
        request.context,
        request.focus_areas,
        request.urgency
    )

@collaboration_router.post("/code-review/{review_id}/submit")
async def submit_code_review(
    review_id: str,
    request: SubmitReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit a code review"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    return await service.submit_review(
        db,
        review_id,
        request.approval_status,
        request.overall_feedback,
        request.comments,
        request.suggested_changes
    )

@collaboration_router.get("/graph")
async def get_collaboration_graph(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get the agent collaboration graph"""
    from app.services.agent_collaboration_service import AgentCollaborationService
    
    service = AgentCollaborationService()
    return await service.get_collaboration_graph(db, project_id)
