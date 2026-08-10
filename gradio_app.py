#!/usr/bin/env python3
"""
=============================================================================
CodeForge AI - Gradio Interface
=============================================================================
Alternative lightweight interface for HuggingFace Spaces free tier.
Provides core functionality without the full Next.js frontend.
=============================================================================
"""

import os
import sys
import json
import asyncio
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

import gradio as gr
import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Environment configuration
VENICE_API_KEY = os.getenv("VENICE_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app/data/codeforge.db")

# Initialize database (async)
async def init_database():
    """Initialize SQLite database for Gradio app."""
    try:
        os.makedirs("/app/data", exist_ok=True)
        from backend.app.database.connection_unified import init_db
        await init_db()
        from backend.app.database.seeds import run_all_seeds
        await run_all_seeds()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

# ============================================================================
# AI Chat Functions
# ============================================================================

async def chat_with_ai(
    message: str,
    history: List[Tuple[str, str]],
    system_prompt: str,
    api_key: str
) -> Tuple[str, List[Tuple[str, str]]]:
    """Send message to AI and get response."""
    
    if not message.strip():
        return "", history
    
    # Use provided API key or environment variable
    key = api_key.strip() or VENICE_API_KEY
    
    if not key:
        response = """⚠️ **No API Key Configured**

Please provide your Venice AI API key in the settings below, or set the `VENICE_API_KEY` environment variable in HuggingFace Spaces settings.

You can get a Venice AI API key at: https://venice.ai/"""
        history.append((message, response))
        return "", history
    
    try:
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        
        messages.append({"role": "user", "content": message})
        
        # Call Venice AI API
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.venice.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "dolphin-2.9.2-qwen2-72b",
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.7
                }
            )
            
            if response.status_code != 200:
                error_text = f"API Error ({response.status_code}): {response.text[:500]}"
                history.append((message, error_text))
                return "", history
            
            data = response.json()
            ai_response = data["choices"][0]["message"]["content"]
            history.append((message, ai_response))
            return "", history
            
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        history.append((message, error_msg))
        return "", history

def sync_chat_with_ai(message, history, system_prompt, api_key):
    """Synchronous wrapper for chat function."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(loop.run_until_complete, chat_with_ai(message, history, system_prompt, api_key)).result()
    return asyncio.run(chat_with_ai(message, history, system_prompt, api_key))

# ============================================================================
# Code Generation Functions
# ============================================================================

async def generate_code(
    prompt: str,
    language: str,
    api_key: str
) -> str:
    """Generate code based on prompt."""
    
    if not prompt.strip():
        return "Please enter a code generation prompt."
    
    key = api_key.strip() or VENICE_API_KEY
    
    if not key:
        return "⚠️ Please configure your Venice AI API key in Settings."
    
    system_prompt = f"""You are an expert {language} programmer. Generate clean, well-documented, 
production-ready code. Include:
- Clear comments explaining the logic
- Error handling where appropriate
- Type hints (for languages that support them)
- Example usage in comments

Output ONLY the code with comments, no explanations outside code blocks."""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.venice.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "dolphin-2.9.2-qwen2-72b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                return f"API Error: {response.text[:500]}"
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except Exception as e:
        return f"❌ Error: {str(e)}"

def sync_generate_code(prompt, language, api_key):
    """Synchronous wrapper for code generation."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(loop.run_until_complete, generate_code(prompt, language, api_key)).result()
    return asyncio.run(generate_code(prompt, language, api_key))

# ============================================================================
# Chat Parser Functions
# ============================================================================

def parse_chat_file(file) -> Tuple[str, str, str]:
    """Parse uploaded chat file and extract code blocks."""
    
    if file is None:
        return "No file uploaded", "", ""
    
    try:
        # Read file content
        file_path = file.name if hasattr(file, 'name') else file
        
        if file_path.endswith('.docx'):
            from docx import Document
            doc = Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
        elif file_path.endswith('.pdf'):
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            content = "\n".join([page.extract_text() for page in reader.pages])
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        # Extract code blocks
        import re
        
        # Pattern for markdown code blocks
        code_pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(code_pattern, content, re.DOTALL)
        
        code_blocks = []
        languages = set()
        
        for lang, code in matches:
            if code.strip():
                code_blocks.append({
                    "language": lang or "text",
                    "code": code.strip()
                })
                if lang:
                    languages.add(lang)
        
        # Summary
        summary = f"""## Extraction Summary

- **Total Code Blocks Found**: {len(code_blocks)}
- **Languages Detected**: {', '.join(languages) if languages else 'None'}
- **Source File**: {Path(file_path).name}
- **Extracted At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Format extracted code
        extracted = ""
        for i, block in enumerate(code_blocks, 1):
            extracted += f"\n### Block {i} ({block['language']})\n```{block['language']}\n{block['code']}\n```\n"
        
        # JSON data for download
        json_data = json.dumps(code_blocks, indent=2)
        
        return summary, extracted if extracted else "No code blocks found.", json_data
        
    except Exception as e:
        return f"❌ Error parsing file: {str(e)}", "", ""

# ============================================================================
# Project Management Functions
# ============================================================================

async def create_project(name: str, description: str) -> str:
    """Create a new project."""
    if not name.strip():
        return "Please enter a project name."
    
    try:
        from backend.app.database.connection_unified import AsyncSessionLocal
        from backend.app.database.models import Project
        import uuid
        
        async with AsyncSessionLocal() as session:
            project = Project(
                id=str(uuid.uuid4()),
                name=name.strip(),
                description=description.strip() if description else "",
                status="active"
            )
            session.add(project)
            await session.commit()
            
        return f"✅ Project '{name}' created successfully!"
    except Exception as e:
        return f"❌ Error creating project: {str(e)}"

def sync_create_project(name, description):
    """Synchronous wrapper."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(loop.run_until_complete, create_project(name, description)).result()
    return asyncio.run(create_project(name, description))

async def list_projects() -> str:
    """List all projects."""
    try:
        from backend.app.database.connection_unified import AsyncSessionLocal
        from backend.app.database.models import Project
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Project).order_by(Project.created_at.desc()))
            projects = result.scalars().all()
            
        if not projects:
            return "No projects found. Create one above!"
        
        output = "## Your Projects\n\n"
        for p in projects:
            output += f"### {p.name}\n"
            output += f"- **ID**: `{p.id[:8]}...`\n"
            output += f"- **Status**: {p.status or 'active'}\n"
            output += f"- **Description**: {p.description or 'No description'}\n\n"
        
        return output
    except Exception as e:
        return f"❌ Error listing projects: {str(e)}"

def sync_list_projects():
    """Synchronous wrapper."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(loop.run_until_complete, list_projects()).result()
    return asyncio.run(list_projects())

# ============================================================================
# Agent Management Functions
# ============================================================================

async def create_agent(
    name: str,
    role: str,
    capabilities: str,
    system_prompt: str
) -> str:
    """Create a new AI agent."""
    if not name.strip() or not role.strip():
        return "Please enter agent name and role."
    
    try:
        from backend.app.database.connection_unified import AsyncSessionLocal
        from backend.app.database.models import AgentModel
        import uuid
        
        caps = [c.strip() for c in capabilities.split(",") if c.strip()]
        
        async with AsyncSessionLocal() as session:
            agent = AgentModel(
                id=str(uuid.uuid4()),
                name=name.strip(),
                role=role.strip(),
                capabilities=caps,
                system_prompt=system_prompt.strip() if system_prompt else None,
                status="active"
            )
            session.add(agent)
            await session.commit()
            
        return f"✅ Agent '{name}' ({role}) created successfully!"
    except Exception as e:
        return f"❌ Error creating agent: {str(e)}"

def sync_create_agent(name, role, capabilities, system_prompt):
    """Synchronous wrapper."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(loop.run_until_complete, create_agent(name, role, capabilities, system_prompt)).result()
    return asyncio.run(create_agent(name, role, capabilities, system_prompt))

async def list_agents() -> str:
    """List all agents."""
    try:
        from backend.app.database.connection_unified import AsyncSessionLocal
        from backend.app.database.models import AgentModel
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AgentModel).order_by(AgentModel.created_at.desc()))
            agents = result.scalars().all()
            
        if not agents:
            return "No agents found. Create one above!"
        
        output = "## Your AI Agents\n\n"
        for a in agents:
            output += f"### {a.name}\n"
            output += f"- **Role**: {a.role}\n"
            output += f"- **Status**: {a.status or 'active'}\n"
            caps = a.capabilities if isinstance(a.capabilities, list) else []
            output += f"- **Capabilities**: {', '.join(caps) if caps else 'None specified'}\n\n"
        
        return output
    except Exception as e:
        return f"❌ Error listing agents: {str(e)}"

def sync_list_agents():
    """Synchronous wrapper."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(loop.run_until_complete, list_agents()).result()
    return asyncio.run(list_agents())

# ============================================================================
# Workflow Generator Functions
# ============================================================================

def generate_workflow(
    project_type: str,
    language: str,
    include_tests: bool,
    include_lint: bool,
    include_security: bool,
    include_deploy: bool
) -> str:
    """Generate GitHub Actions workflow."""
    
    workflows = {}
    
    # CI Workflow
    if include_tests or include_lint:
        ci_jobs = {}
        
        if include_lint:
            if language == "python":
                ci_jobs["lint"] = {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
                        {"run": "pip install flake8 black"},
                        {"run": "flake8 . --max-line-length=120"},
                        {"run": "black --check ."}
                    ]
                }
            elif language in ["javascript", "typescript"]:
                ci_jobs["lint"] = {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"uses": "actions/setup-node@v4", "with": {"node-version": "18"}},
                        {"run": "npm ci"},
                        {"run": "npm run lint"}
                    ]
                }
        
        if include_tests:
            if language == "python":
                ci_jobs["test"] = {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"uses": "actions/setup-python@v5", "with": {"python-version": "3.11"}},
                        {"run": "pip install -r requirements.txt"},
                        {"run": "pip install pytest pytest-cov"},
                        {"run": "pytest --cov=. --cov-report=xml"}
                    ]
                }
            elif language in ["javascript", "typescript"]:
                ci_jobs["test"] = {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"uses": "actions/setup-node@v4", "with": {"node-version": "18"}},
                        {"run": "npm ci"},
                        {"run": "npm test"}
                    ]
                }
        
        workflows["ci.yml"] = {
            "name": "CI",
            "on": {"push": {"branches": ["main", "develop"]}, "pull_request": {"branches": ["main"]}},
            "jobs": ci_jobs
        }
    
    # Security Workflow
    if include_security:
        workflows["security.yml"] = {
            "name": "Security Scan",
            "on": {"push": {"branches": ["main"]}, "schedule": [{"cron": "0 0 * * 0"}]},
            "jobs": {
                "security": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"name": "Run Trivy", "uses": "aquasecurity/trivy-action@master", 
                         "with": {"scan-type": "fs", "scan-ref": "."}}
                    ]
                }
            }
        }
    
    # Deploy Workflow
    if include_deploy:
        workflows["deploy.yml"] = {
            "name": "Deploy",
            "on": {"push": {"branches": ["main"]}},
            "jobs": {
                "deploy": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"name": "Deploy", "run": "echo 'Add your deployment steps here'"}
                    ]
                }
            }
        }
    
    # Format output
    import yaml
    output = "## Generated GitHub Actions Workflows\n\n"
    
    for filename, workflow in workflows.items():
        output += f"### `.github/workflows/{filename}`\n```yaml\n"
        output += yaml.dump(workflow, default_flow_style=False, sort_keys=False)
        output += "```\n\n"
    
    if not workflows:
        output = "Please select at least one workflow option."
    
    return output

# ============================================================================
# Gradio Interface
# ============================================================================

def create_interface():
    """Create the Gradio interface."""
    
    # Custom CSS
    css = """
    .gradio-container { max-width: 1200px !important; }
    .code-output { font-family: 'Fira Code', monospace; }
    """
    
    with gr.Blocks(title="CodeForge AI", css=css, theme=gr.themes.Soft()) as app:
        
        gr.Markdown("""
        # 🔧 CodeForge AI
        
        AI-powered code generation and development platform. Generate code, manage projects, 
        create AI agents, and parse chat transcripts.
        """)
        
        with gr.Tabs():
            # ---- AI Chat Tab ----
            with gr.Tab("💬 AI Chat"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            label="Chat with AI",
                            height=500,
                            show_copy_button=True
                        )
                        with gr.Row():
                            msg = gr.Textbox(
                                placeholder="Ask the AI to generate code, explain concepts, or help with development...",
                                label="Message",
                                scale=4
                            )
                            send_btn = gr.Button("Send", variant="primary", scale=1)
                        
                        clear_btn = gr.Button("Clear Chat")
                    
                    with gr.Column(scale=1):
                        system_prompt = gr.Textbox(
                            label="System Prompt",
                            placeholder="Optional: Customize AI behavior...",
                            lines=5,
                            value="You are an expert software developer. Help the user with code generation, debugging, and software architecture."
                        )
                        api_key_chat = gr.Textbox(
                            label="Venice API Key",
                            placeholder="Enter API key or set VENICE_API_KEY env var",
                            type="password"
                        )
                
                # Event handlers
                send_btn.click(
                    sync_chat_with_ai,
                    inputs=[msg, chatbot, system_prompt, api_key_chat],
                    outputs=[msg, chatbot]
                )
                msg.submit(
                    sync_chat_with_ai,
                    inputs=[msg, chatbot, system_prompt, api_key_chat],
                    outputs=[msg, chatbot]
                )
                clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])
            
            # ---- Code Generation Tab ----
            with gr.Tab("⚡ Code Generator"):
                with gr.Row():
                    with gr.Column():
                        code_prompt = gr.Textbox(
                            label="What code do you need?",
                            placeholder="Describe the code you want to generate...",
                            lines=4
                        )
                        code_language = gr.Dropdown(
                            choices=["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "SQL"],
                            value="Python",
                            label="Programming Language"
                        )
                        api_key_code = gr.Textbox(
                            label="Venice API Key",
                            type="password"
                        )
                        generate_btn = gr.Button("Generate Code", variant="primary")
                    
                    with gr.Column():
                        code_output = gr.Markdown(
                            label="Generated Code",
                            elem_classes=["code-output"]
                        )
                
                generate_btn.click(
                    sync_generate_code,
                    inputs=[code_prompt, code_language, api_key_code],
                    outputs=[code_output]
                )
            
            # ---- Chat Parser Tab ----
            with gr.Tab("📄 Chat Parser"):
                gr.Markdown("### Extract Code from Chat Transcripts\nUpload a chat transcript (DOCX, PDF, TXT, MD) to extract code blocks.")
                
                with gr.Row():
                    with gr.Column():
                        file_upload = gr.File(
                            label="Upload Chat File",
                            file_types=[".docx", ".pdf", ".txt", ".md", ".html"]
                        )
                        parse_btn = gr.Button("Parse & Extract Code", variant="primary")
                    
                    with gr.Column():
                        parse_summary = gr.Markdown(label="Summary")
                
                extracted_code = gr.Markdown(label="Extracted Code Blocks")
                json_output = gr.Textbox(label="JSON Data", lines=10, visible=False)
                
                parse_btn.click(
                    parse_chat_file,
                    inputs=[file_upload],
                    outputs=[parse_summary, extracted_code, json_output]
                )
            
            # ---- Projects Tab ----
            with gr.Tab("📁 Projects"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Create New Project")
                        project_name = gr.Textbox(label="Project Name", placeholder="my-awesome-project")
                        project_desc = gr.Textbox(label="Description", placeholder="Project description...", lines=2)
                        create_project_btn = gr.Button("Create Project", variant="primary")
                        project_result = gr.Markdown()
                    
                    with gr.Column():
                        gr.Markdown("### Your Projects")
                        refresh_projects_btn = gr.Button("Refresh List")
                        projects_list = gr.Markdown()
                
                create_project_btn.click(
                    sync_create_project,
                    inputs=[project_name, project_desc],
                    outputs=[project_result]
                )
                refresh_projects_btn.click(sync_list_projects, outputs=[projects_list])
                app.load(sync_list_projects, outputs=[projects_list])
            
            # ---- Agents Tab ----
            with gr.Tab("🤖 AI Agents"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Create New Agent")
                        agent_name = gr.Textbox(label="Agent Name", placeholder="CodeReviewer")
                        agent_role = gr.Dropdown(
                            choices=["code_generator", "code_reviewer", "architect", "tester", "documenter"],
                            value="code_generator",
                            label="Role"
                        )
                        agent_caps = gr.Textbox(
                            label="Capabilities (comma-separated)",
                            placeholder="python, javascript, testing"
                        )
                        agent_prompt = gr.Textbox(
                            label="System Prompt",
                            placeholder="Custom instructions for this agent...",
                            lines=3
                        )
                        create_agent_btn = gr.Button("Create Agent", variant="primary")
                        agent_result = gr.Markdown()
                    
                    with gr.Column():
                        gr.Markdown("### Your Agents")
                        refresh_agents_btn = gr.Button("Refresh List")
                        agents_list = gr.Markdown()
                
                create_agent_btn.click(
                    sync_create_agent,
                    inputs=[agent_name, agent_role, agent_caps, agent_prompt],
                    outputs=[agent_result]
                )
                refresh_agents_btn.click(sync_list_agents, outputs=[agents_list])
                app.load(sync_list_agents, outputs=[agents_list])
            
            # ---- Workflows Tab ----
            with gr.Tab("⚙️ Workflow Generator"):
                gr.Markdown("### Generate GitHub Actions Workflows")
                
                with gr.Row():
                    with gr.Column():
                        wf_project_type = gr.Dropdown(
                            choices=["web", "api", "cli", "library", "microservice"],
                            value="api",
                            label="Project Type"
                        )
                        wf_language = gr.Dropdown(
                            choices=["python", "javascript", "typescript", "go", "rust"],
                            value="python",
                            label="Language"
                        )
                        wf_tests = gr.Checkbox(label="Include Tests", value=True)
                        wf_lint = gr.Checkbox(label="Include Linting", value=True)
                        wf_security = gr.Checkbox(label="Include Security Scan", value=True)
                        wf_deploy = gr.Checkbox(label="Include Deployment", value=False)
                        generate_wf_btn = gr.Button("Generate Workflows", variant="primary")
                    
                    with gr.Column():
                        wf_output = gr.Markdown(label="Generated Workflows")
                
                generate_wf_btn.click(
                    generate_workflow,
                    inputs=[wf_project_type, wf_language, wf_tests, wf_lint, wf_security, wf_deploy],
                    outputs=[wf_output]
                )
            
            # ---- Settings Tab ----
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("""
                ### Configuration
                
                Set these as environment variables in HuggingFace Spaces settings for persistent configuration:
                
                | Variable | Description |
                |----------|-------------|
                | `VENICE_API_KEY` | Venice AI API key for code generation |
                | `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub token for repository integration |
                | `GITHUB_USERNAME` | Your GitHub username |
                | `SECRET_KEY` | Application secret key |
                
                #### Current Status
                """)
                
                status_text = f"""
                - **Venice API Key**: {'✅ Configured' if VENICE_API_KEY else '❌ Not set'}
                - **GitHub Token**: {'✅ Configured' if GITHUB_TOKEN else '❌ Not set'}
                - **GitHub Username**: {GITHUB_USERNAME if GITHUB_USERNAME else '❌ Not set'}
                - **Database**: {DATABASE_URL.split('://')[0].upper() if '://' in DATABASE_URL else 'Unknown'}
                """
                gr.Markdown(status_text)
                
                gr.Markdown("""
                #### About CodeForge AI
                
                CodeForge AI is an AI-powered development platform that helps you:
                - Generate code using AI
                - Manage development projects
                - Create and orchestrate AI agents
                - Parse and extract code from chat transcripts
                - Generate CI/CD workflows
                
                [View on GitHub](https://github.com/your-username/codeforge-ai) | [Documentation](https://github.com/your-username/codeforge-ai/docs)
                """)
    
    return app

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Initialize database
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(loop.run_until_complete, init_database()).result()
        else:
            asyncio.run(init_database())
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    
    # Create and launch app
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 7860)),
        share=False,
        show_error=True
    )
