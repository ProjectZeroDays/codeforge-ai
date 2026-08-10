from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import uvicorn
import asyncio
from typing import List, Dict, Any, Optional
import json
import tempfile
import os
from pathlib import Path

from app.services.venice_service import VeniceAIService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.github_service import GitHubService
from app.services.project_service import ProjectService
from app.services.local_llm_service import LocalLLMService, ModelConfig
from app.services.chat_parser_service import ChatParserService
from app.services.workflow_generator_service import WorkflowGeneratorService, WorkflowConfig
from app.services.code_completion_service import CodeCompletionService
from app.database.connection_unified import get_db, init_db
from app.models.schemas import (
    ChatRequest, ProjectRequest, AgentRequest,
    GitHubRepoRequest, SystemPromptUpdate,
    # Local LLM schemas
    LocalLLMConfigRequest, LocalLLMGenerateRequest, LocalLLMStatusResponse,
    # Chat Parser schemas
    ChatParserRequest, ChatExtractionResponse, CreateProjectFromExtractionRequest,
    # Workflow Generator schemas
    WorkflowConfigRequest, WorkflowGenerateResponse, WorkflowTemplateRequest,
    # Code Completion schemas
    CodeAnalysisRequest, CodeAnalysisResponse, CompleteFunctionRequest, CompletionResponse,
    # Wizard schemas
    WizardAnswerRequest, WizardSessionResponse, WizardScaffoldingResponse,
    # Common schemas
    UnifiedChatRequest, AIProvider, SuccessResponse, ErrorResponse
)
from app.websocket.manager import WebSocketManager

import os

app = FastAPI(
    title="CodeForge AI",
    description="AI-Powered Development Platform with Multi-Agent Orchestration, Local LLM Support, and Code Intelligence",
    version="2.0.0"
)

# CORS Configuration
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:7860"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager
ws_manager = WebSocketManager()

# Services initialization
venice_service = VeniceAIService()
local_llm_service = LocalLLMService()
chat_parser_service = ChatParserService()
workflow_generator_service = WorkflowGeneratorService()
code_completion_service = CodeCompletionService(ai_service=venice_service)
agent_orchestrator = AgentOrchestrator(venice_service, ws_manager)
github_service = GitHubService()
project_service = ProjectService()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("[STARTUP] CodeForge AI Backend Starting...")
    # Initialize database connection
    await init_db()
    print("[OK] Database connected")
    
    # Run seeds for default data
    try:
        from app.database.seeds import run_all_seeds
        await run_all_seeds()
        print("[OK] Default data seeded")
    except Exception as e:
        print(f"[WARN] Seeding skipped: {e}")
    
    print("[OK] Services initialized")
    print("[INFO] Local LLM: Available (not loaded)")
    print("[INFO] Chat Parser: Ready")
    print("[INFO] Workflow Generator: Ready")
    print("[INFO] Code Completion: Ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("[SHUTDOWN] Shutting down CodeForge AI...")
    await agent_orchestrator.shutdown_all_agents()
    
    # Unload local LLM if loaded
    if local_llm_service.is_loaded:
        await local_llm_service.unload_model()


# ================== Health Check ==================
@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "CodeForge AI",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "venice_ai": "ready",
        "active_agents": agent_orchestrator.get_active_agent_count()
    }


# ================== Chat & AI Endpoints ==================
@app.post("/api/chat")
async def chat(request: ChatRequest, db=Depends(get_db)):
    """
    Send a chat message and get AI response with streaming
    """
    async def generate_response():
        try:
            async for chunk in venice_service.stream_chat(
                messages=request.messages,
                model=request.model or "dolphin-2.9.2-qwen2-72b",
                system_prompt=request.system_prompt,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 4096
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate_response(), media_type="text/event-stream")


@app.post("/api/generate-code")
async def generate_code(request: ChatRequest, db=Depends(get_db)):
    """
    Generate code from natural language prompt
    """
    result = await venice_service.generate_code(
        prompt=request.messages[-1]['content'],
        context=request.context,
        language=request.language
    )
    
    # Save to database
    await project_service.save_generated_code(db, result)
    
    return result


@app.put("/api/system-prompt")
async def update_system_prompt(update: SystemPromptUpdate, db=Depends(get_db)):
    """
    Update system prompt configuration
    """
    await venice_service.update_system_prompt(db, update)
    return {"status": "success", "message": "System prompt updated"}


# ================== Agent Orchestration ==================
@app.post("/api/agents/create")
async def create_agent(request: AgentRequest, db=Depends(get_db)):
    """
    Create a new AI agent for specific tasks
    """
    agent = await agent_orchestrator.create_agent(
        name=request.name,
        role=request.role,
        capabilities=request.capabilities,
        system_prompt=request.system_prompt,
        db=db
    )
    return agent


@app.get("/api/agents")
async def list_agents(db=Depends(get_db)):
    """
    List all active agents
    """
    agents = await agent_orchestrator.get_all_agents(db)
    return {"agents": agents}


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str, db=Depends(get_db)):
    """
    Get agent details and activity
    """
    agent = await agent_orchestrator.get_agent(agent_id, db)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.post("/api/agents/{agent_id}/task")
async def assign_task_to_agent(agent_id: str, task: Dict[str, Any], db=Depends(get_db)):
    """
    Assign a task to a specific agent
    """
    result = await agent_orchestrator.assign_task(
        agent_id=agent_id,
        task=task,
        db=db
    )
    return result


@app.delete("/api/agents/{agent_id}")
async def terminate_agent(agent_id: str, db=Depends(get_db)):
    """
    Terminate an agent
    """
    await agent_orchestrator.terminate_agent(agent_id, db)
    return {"status": "success", "message": f"Agent {agent_id} terminated"}


@app.get("/api/agents/{agent_id}/activity")
async def get_agent_activity(agent_id: str, db=Depends(get_db)):
    """
    Get agent activity log
    """
    activity = await agent_orchestrator.get_agent_activity(agent_id, db)
    return {"activity": activity}


# ================== Project Management ==================
@app.post("/api/projects")
async def create_project(request: ProjectRequest, db=Depends(get_db)):
    """
    Create a new project
    """
    project = await project_service.create_project(
        name=request.name,
        description=request.description,
        framework=request.framework,
        db=db
    )
    return project


@app.get("/api/projects")
async def list_projects(db=Depends(get_db)):
    """
    List all projects
    """
    projects = await project_service.get_all_projects(db)
    return {"projects": projects}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str, db=Depends(get_db)):
    """
    Get project details
    """
    project = await project_service.get_project(project_id, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.get("/api/projects/{project_id}/files")
async def get_project_files(project_id: str, db=Depends(get_db)):
    """
    Get all files in a project
    """
    files = await project_service.get_project_files(project_id, db)
    return {"files": files}


@app.post("/api/projects/{project_id}/files")
async def save_file(project_id: str, file_data: Dict[str, Any], db=Depends(get_db)):
    """
    Save or update a file in the project
    """
    file = await project_service.save_file(
        project_id=project_id,
        path=file_data['path'],
        content=file_data['content'],
        db=db
    )
    return file


@app.delete("/api/projects/{project_id}/files/{file_id}")
async def delete_file(project_id: str, file_id: str, db=Depends(get_db)):
    """
    Delete a file from the project
    """
    await project_service.delete_file(project_id, file_id, db)
    return {"status": "success"}


# ================== GitHub Integration ==================
@app.post("/api/github/repos")
async def create_github_repo(request: GitHubRepoRequest, db=Depends(get_db)):
    """
    Create a new GitHub repository
    """
    repo = await github_service.create_repository(
        name=request.name,
        description=request.description,
        private=request.private
    )
    return repo


@app.post("/api/github/push")
async def push_to_github(request: Dict[str, Any], db=Depends(get_db)):
    """
    Push project files to GitHub
    """
    result = await github_service.push_files(
        repo_name=request['repo_name'],
        files=request['files'],
        commit_message=request['commit_message'],
        branch=request.get('branch', 'main')
    )
    return result


@app.get("/api/github/repos")
async def list_github_repos():
    """
    List user's GitHub repositories
    """
    repos = await github_service.list_repositories()
    return {"repos": repos}


@app.get("/api/github/repos/{repo_name}/status")
async def get_repo_status(repo_name: str):
    """
    Get repository status
    """
    status = await github_service.get_repo_status(repo_name)
    return status


# ================== WebSocket for Real-time Updates ==================
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await ws_manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message['type'] == 'agent_update':
                await ws_manager.broadcast_to_client(
                    client_id,
                    {"type": "agent_status", "data": message}
                )
            elif message['type'] == 'task_progress':
                await ws_manager.broadcast_to_client(
                    client_id,
                    {"type": "progress", "data": message}
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)


# ================== Local LLM Endpoints ==================
@app.get("/api/local-llm/status")
async def get_local_llm_status():
    """
    Get the status of the local LLM service
    """
    return local_llm_service.get_status()


@app.post("/api/local-llm/download")
async def download_local_llm(model_id: Optional[str] = None):
    """
    Download a model from HuggingFace Hub
    """
    result = await local_llm_service.download_model(model_id)
    return result


@app.post("/api/local-llm/load")
async def load_local_llm(request: LocalLLMConfigRequest):
    """
    Load a local LLM into memory
    """
    config = ModelConfig(
        model_id=request.model_id,
        device=request.device,
        quantization=request.quantization,
        max_context_length=request.max_context_length
    )
    result = await local_llm_service.load_model(config)
    return result


@app.post("/api/local-llm/unload")
async def unload_local_llm():
    """
    Unload the current local LLM from memory
    """
    result = await local_llm_service.unload_model()
    return result


@app.post("/api/local-llm/generate")
async def generate_with_local_llm(request: LocalLLMGenerateRequest):
    """
    Generate text using the local LLM
    """
    result = await local_llm_service.generate(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        top_p=request.top_p,
        max_tokens=request.max_tokens,
        stop_sequences=request.stop_sequences
    )
    return result


@app.post("/api/local-llm/stream")
async def stream_generate_with_local_llm(request: LocalLLMGenerateRequest):
    """
    Stream generate text using the local LLM
    """
    async def generate_stream():
        async for chunk in local_llm_service.stream_generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@app.get("/api/local-llm/models")
async def list_local_models():
    """
    List available local models
    """
    models = await local_llm_service.list_available_models()
    return {"models": models}


@app.get("/api/local-llm/configs", tags=["Local LLM"])
async def get_llm_configs(db=Depends(get_db)):
    """
    Get saved LLM configurations from database
    """
    local_llm_service.db_session = db
    configs = await local_llm_service.get_configs_from_db()
    return {"configs": configs}


# ================== Unified Chat Endpoint ==================
@app.post("/api/unified-chat")
async def unified_chat(request: UnifiedChatRequest, db=Depends(get_db)):
    """
    Unified chat endpoint supporting both Venice API and local LLM
    """
    # Get system prompt from database if ID provided
    system_prompt = request.system_prompt
    if request.system_prompt_id:
        from sqlalchemy import select
        from app.database.models import SystemPrompt
        result = await db.execute(
            select(SystemPrompt).where(SystemPrompt.id == request.system_prompt_id)
        )
        prompt = result.scalar_one_or_none()
        if prompt:
            system_prompt = prompt.content
    
    if request.provider == AIProvider.LOCAL:
        # Use local LLM
        if not local_llm_service.is_loaded:
            raise HTTPException(status_code=400, detail="Local LLM not loaded. Load a model first.")
        
        # Get the last user message
        user_message = next((m['content'] for m in reversed(request.messages) if m['role'] == 'user'), "")
        
        if request.stream:
            async def generate_stream():
                async for chunk in local_llm_service.stream_generate(
                    prompt=user_message,
                    system_prompt=system_prompt,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens
                ):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        else:
            result = await local_llm_service.generate(
                prompt=user_message,
                system_prompt=system_prompt,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens
            )
            return result
    else:
        # Use Venice API
        if request.stream:
            async def generate_response():
                try:
                    async for chunk in venice_service.stream_chat(
                        messages=request.messages,
                        model=request.model or "dolphin-2.9.2-qwen2-72b",
                        system_prompt=system_prompt,
                        temperature=request.temperature or 0.7,
                        max_tokens=request.max_tokens or 4096
                    ):
                        yield f"data: {json.dumps(chunk)}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(generate_response(), media_type="text/event-stream")
        else:
            result = await venice_service.generate_code(
                prompt=request.messages[-1]['content'],
                context=request.context,
                language=None
            )
            return result


# ================== Chat Parser Endpoints ==================
@app.post("/api/chat-parser/upload")
async def upload_and_parse_chat(
    file: UploadFile = File(...),
    file_type: Optional[str] = None,
    db=Depends(get_db)
):
    """
    Upload a chat document and extract code blocks
    """
    # Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        # Initialize service with db session
        chat_parser_service.db_session = db
        
        # Parse document
        project = await chat_parser_service.parse_document(temp_path, file_type)
        
        # Save extraction to database
        save_result = await chat_parser_service.save_extraction_to_db(
            filename=file.filename,
            file_type=file_type or chat_parser_service._detect_file_type(temp_path),
            project=project
        )
        
        return ChatExtractionResponse(
            success=True,
            extraction_id=save_result.get("extraction_id"),
            files=project.files,
            code_blocks_count=len(project.code_blocks),
            languages_detected=project.languages_detected,
            source_format=project.source_format,
            readme_content=project.readme_content
        )
        
    except Exception as e:
        return ChatExtractionResponse(success=False, error=str(e))
    
    finally:
        # Cleanup temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/api/chat-parser/create-project")
async def create_project_from_extraction(request: CreateProjectFromExtractionRequest, db=Depends(get_db)):
    """
    Create a new project from a chat extraction
    """
    chat_parser_service.db_session = db
    result = await chat_parser_service.create_project_from_extraction(
        extraction_id=request.extraction_id,
        project_name=request.project_name
    )
    return result


@app.post("/api/chat-parser/download-zip")
async def download_extraction_as_zip(
    file: UploadFile = File(...),
    file_type: Optional[str] = None
):
    """
    Parse a chat document and return as a ZIP file
    """
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        # Parse document
        project = await chat_parser_service.parse_document(temp_path, file_type)
        
        # Create ZIP
        zip_path = await chat_parser_service.create_project_zip(project)
        
        return FileResponse(
            path=zip_path,
            filename="extracted_project.zip",
            media_type="application/zip"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/chat-parser/extractions")
async def list_extractions(db=Depends(get_db)):
    """
    List all chat extractions
    """
    from sqlalchemy import select
    from app.database.models import ChatExtraction
    
    result = await db.execute(
        select(ChatExtraction).order_by(ChatExtraction.created_at.desc())
    )
    extractions = result.scalars().all()
    
    return {
        "extractions": [
            {
                "id": e.id,
                "filename": e.filename,
                "file_type": e.file_type,
                "source_format": e.source_format,
                "code_blocks_count": e.code_blocks_count,
                "languages_detected": e.languages_detected,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in extractions
        ]
    }


# ================== Workflow Generator Endpoints ==================
@app.post("/api/workflows/generate")
async def generate_workflows(request: WorkflowConfigRequest, db=Depends(get_db)):
    """
    Generate GitHub Actions workflows based on configuration
    """
    config = WorkflowConfig(
        name=request.name,
        languages=request.languages,
        include_linting=request.include_linting,
        include_testing=request.include_testing,
        include_security=request.include_security,
        include_build=request.include_build,
        include_deploy=request.include_deploy,
        node_version=request.node_version,
        python_version=request.python_version,
        go_version=request.go_version,
        java_version=request.java_version,
        deploy_target=request.deploy_target,
        custom_steps=request.custom_steps
    )
    
    workflows = workflow_generator_service.generate_workflow(config)
    
    return WorkflowGenerateResponse(
        success=True,
        workflows=list(workflows.keys()),
        languages_detected=request.languages
    )


@app.post("/api/workflows/generate-for-project/{project_id}")
async def generate_workflows_for_project(
    project_id: str,
    request: WorkflowConfigRequest,
    db=Depends(get_db)
):
    """
    Generate and save workflows for a specific project
    """
    workflow_generator_service.db_session = db
    
    config = WorkflowConfig(
        name=request.name,
        languages=request.languages,
        include_linting=request.include_linting,
        include_testing=request.include_testing,
        include_security=request.include_security,
        include_build=request.include_build,
        include_deploy=request.include_deploy,
        node_version=request.node_version,
        python_version=request.python_version,
        go_version=request.go_version,
        java_version=request.java_version,
        deploy_target=request.deploy_target
    )
    
    result = await workflow_generator_service.generate_for_project(project_id, config)
    return result


@app.post("/api/workflows/templates")
async def create_workflow_template(request: WorkflowTemplateRequest, db=Depends(get_db)):
    """
    Create a custom workflow template
    """
    workflow_generator_service.db_session = db
    result = await workflow_generator_service.save_template_to_db(
        name=request.name,
        category=request.category.value,
        content=request.template_content,
        description=request.description,
        variables=request.variables,
        languages=request.languages
    )
    return result


@app.get("/api/workflows/templates")
async def list_workflow_templates(category: Optional[str] = None, db=Depends(get_db)):
    """
    List available workflow templates
    """
    workflow_generator_service.db_session = db
    templates = await workflow_generator_service.get_templates_from_db(category)
    return {"templates": templates}


# ================== Code Completion Endpoints ==================
@app.post("/api/code-completion/analyze")
async def analyze_code(request: CodeAnalysisRequest, db=Depends(get_db)):
    """
    Analyze code for missing functions and incomplete implementations
    """
    code_completion_service.db_session = db
    
    result = await code_completion_service.analyze_code(
        code=request.code,
        language=request.language,
        context={"file_path": request.file_path} if request.file_path else None
    )
    
    return result


@app.post("/api/code-completion/complete-function")
async def complete_function(request: CompleteFunctionRequest, db=Depends(get_db)):
    """
    Generate a complete implementation for a specific function
    """
    code_completion_service.db_session = db
    
    result = await code_completion_service.complete_function(
        code=request.code,
        function_name=request.function_name,
        language=request.language,
        requirements=request.requirements
    )
    
    return result


# ================== Development Wizard Endpoints ==================
@app.post("/api/wizard/start")
async def start_wizard_session(project_id: Optional[str] = None, db=Depends(get_db)):
    """
    Start a new development wizard session
    """
    code_completion_service.db_session = db
    
    session = await code_completion_service.start_wizard_session(project_id)
    next_question = await code_completion_service.get_wizard_question(session.id)
    
    return WizardSessionResponse(
        session_id=session.id,
        phase=session.phase,
        decisions_count=len(session.decisions),
        next_question=next_question
    )


@app.post("/api/wizard/answer")
async def answer_wizard_question(request: WizardAnswerRequest, db=Depends(get_db)):
    """
    Submit an answer to a wizard question
    """
    code_completion_service.db_session = db
    
    result = await code_completion_service.answer_wizard_question(
        session_id=request.session_id,
        question_id=request.question_id,
        answer=request.answer
    )
    
    return result


@app.post("/api/wizard/{session_id}/generate")
async def generate_scaffolding(session_id: str, db=Depends(get_db)):
    """
    Generate project scaffolding based on wizard decisions
    """
    code_completion_service.db_session = db
    
    result = await code_completion_service.generate_scaffolding(session_id)
    
    return WizardScaffoldingResponse(
        success=result.get("success", False),
        files=result.get("files", []),
        total_files=result.get("total_files", 0),
        decisions_applied=result.get("decisions_applied", 0),
        error=result.get("error")
    )


@app.get("/api/wizard/{session_id}/files")
async def get_wizard_generated_files(session_id: str, db=Depends(get_db)):
    """
    Get the generated files from a wizard session
    """
    session = code_completion_service.active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "phase": session.phase,
        "files": session.generated_files,
        "decisions": [
            {"category": d.category, "question": d.question, "answer": d.answer}
            for d in session.decisions
        ]
    }


# ================== System Prompts Endpoints ==================
@app.get("/api/system-prompts")
async def list_system_prompts(db=Depends(get_db)):
    """
    List all available system prompts
    """
    from sqlalchemy import select
    from app.database.models import SystemPrompt
    
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.is_active == True).order_by(SystemPrompt.name)
    )
    prompts = result.scalars().all()
    
    return {
        "prompts": [
            {
                "id": p.id,
                "name": p.name,
                "content": p.content,
                "category": p.category,
                "is_active": p.is_active
            }
            for p in prompts
        ]
    }


@app.get("/api/system-prompts/{prompt_id}")
async def get_system_prompt(prompt_id: str, db=Depends(get_db)):
    """
    Get a specific system prompt
    """
    from sqlalchemy import select
    from app.database.models import SystemPrompt
    
    result = await db.execute(
        select(SystemPrompt).where(SystemPrompt.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="System prompt not found")
    
    return {
        "id": prompt.id,
        "name": prompt.name,
        "content": prompt.content,
        "category": prompt.category,
        "is_active": prompt.is_active
    }


# ================== Extended API Routes ==================
# Import and register extended routes for high-value features
from app.api.extended_routes import (
    templates_router,
    export_router,
    import_router,
    api_keys_router,
    quality_router,
    collaboration_router
)

app.include_router(templates_router)
app.include_router(export_router)
app.include_router(import_router)
app.include_router(api_keys_router)
app.include_router(quality_router)
app.include_router(collaboration_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )