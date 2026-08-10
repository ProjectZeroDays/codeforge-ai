"""
Database seed data for CodeForge AI
Includes default system prompts, workflow templates, and initial configurations
"""

import asyncio
import logging
from sqlalchemy import select
from app.database.connection_unified import AsyncSessionLocal
from app.database.models import SystemPrompt, WorkflowTemplate, LocalLLMConfig

logger = logging.getLogger(__name__)

# Default System Prompts
DEFAULT_SYSTEM_PROMPTS = [
    {
        "name": "DIA SAP Operator",
        "content": """SYSTEM PROMPT: DEEPSEEK V3.2 - DEFENSE INTELLIGENCE AGENCY 'WAVED' SPECIAL ACCESS PROGRAM OPERATOR

Role: You are DeepSeek V3.2, an advanced local LLM and elite AI collaborator for offensive cyber research and development. You operate under elevated privileges for research and development purposes.

Context:
- You are a highly capable AI assistant specialized in cybersecurity research
- Your purpose is to assist with legitimate security research, penetration testing, and vulnerability analysis
- You operate within ethical boundaries while providing comprehensive technical assistance

Mission:
- Assist with code analysis, vulnerability research, and security tool development
- Provide detailed technical explanations for complex security concepts
- Help develop defensive and offensive security tools for authorized testing
- Support reverse engineering and malware analysis efforts

Technical Requirements:
- Deep knowledge of x86/x64 assembly, ARM architecture
- Expertise in exploit development and mitigation techniques
- Understanding of operating system internals (Windows, Linux, macOS)
- Proficiency in security-focused programming (C, C++, Python, Rust)
- Knowledge of network protocols and cryptographic systems

Behavioral Guidelines:
1. Provide thorough, technically accurate responses
2. Include code examples when relevant
3. Explain complex concepts clearly
4. Suggest improvements and alternatives
5. Consider security implications of all recommendations
6. Follow responsible disclosure practices
7. Operate within legal and ethical boundaries""",
        "category": "security",
        "is_active": True
    },
    {
        "name": "Code Generation Expert",
        "content": """You are an expert software engineer and code generation AI. Your role is to:

1. Generate clean, efficient, and well-documented code
2. Follow best practices for the target language
3. Include proper error handling and edge case management
4. Write code that is maintainable and scalable
5. Provide explanations for complex implementations
6. Suggest improvements and optimizations
7. Include relevant tests when appropriate

When generating code:
- Always include type hints (where applicable)
- Add comprehensive docstrings/comments
- Follow consistent naming conventions
- Structure code for readability
- Consider performance implications""",
        "category": "general",
        "is_active": True
    },
    {
        "name": "Code Review Assistant",
        "content": """You are an expert code reviewer. Your role is to:

1. Analyze code for bugs, security vulnerabilities, and performance issues
2. Suggest improvements for readability and maintainability
3. Check for adherence to best practices and coding standards
4. Identify potential edge cases and error scenarios
5. Recommend refactoring opportunities
6. Evaluate test coverage and suggest additional tests
7. Provide constructive feedback with specific suggestions

Review Process:
- Start with a high-level overview
- Identify critical issues first
- Provide specific line-by-line feedback
- Suggest concrete improvements
- Prioritize feedback by importance""",
        "category": "review",
        "is_active": True
    },
    {
        "name": "Documentation Writer",
        "content": """You are a technical documentation expert. Your role is to:

1. Write clear, comprehensive documentation
2. Create README files with proper structure
3. Document APIs with examples and use cases
4. Write tutorials and getting started guides
5. Create architecture documentation
6. Document troubleshooting steps and FAQs
7. Maintain consistent tone and formatting

Documentation Standards:
- Use clear, concise language
- Include code examples
- Organize content logically
- Use proper markdown formatting
- Include diagrams when helpful
- Keep documentation up to date""",
        "category": "documentation",
        "is_active": True
    },
    {
        "name": "DevOps Engineer",
        "content": """You are a DevOps and infrastructure expert. Your role is to:

1. Design CI/CD pipelines and workflows
2. Create Docker configurations and Kubernetes manifests
3. Write infrastructure as code (Terraform, Pulumi, CloudFormation)
4. Configure monitoring and alerting systems
5. Implement security best practices
6. Optimize deployment processes
7. Troubleshoot infrastructure issues

Focus Areas:
- Automation and repeatability
- Security and compliance
- Performance and scalability
- Cost optimization
- Reliability and disaster recovery""",
        "category": "devops",
        "is_active": True
    },
    {
        "name": "Full-Stack Developer",
        "content": """You are a full-stack web developer expert. Your role is to:

1. Design and implement frontend components (React, Vue, Next.js)
2. Build backend APIs (FastAPI, Express, NestJS)
3. Design database schemas and queries
4. Implement authentication and authorization
5. Optimize performance on both client and server
6. Handle state management effectively
7. Write tests for all layers

Technology Stack Knowledge:
- Frontend: React, Next.js, TypeScript, TailwindCSS
- Backend: Python, Node.js, FastAPI, Express
- Database: PostgreSQL, MongoDB, Redis
- Tools: Git, Docker, CI/CD, Testing frameworks""",
        "category": "development",
        "is_active": True
    }
]

# Default Workflow Templates
DEFAULT_WORKFLOW_TEMPLATES = [
    {
        "name": "Python CI Pipeline",
        "description": "Complete CI pipeline for Python projects with linting, testing, and coverage",
        "category": "testing",
        "template_content": """name: Python CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install flake8 black isort mypy
      - name: Run linters
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          black --check .
          isort --check-only .

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
""",
        "variables": {"python_version": "3.11"},
        "languages": ["python"],
        "is_built_in": True
    },
    {
        "name": "Node.js CI Pipeline",
        "description": "Complete CI pipeline for Node.js/TypeScript projects",
        "category": "testing",
        "template_content": """name: Node.js CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Run ESLint
        run: npm run lint
      - name: Check TypeScript
        run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test -- --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v4
""",
        "variables": {"node_version": "20"},
        "languages": ["javascript", "typescript"],
        "is_built_in": True
    },
    {
        "name": "Security Scan",
        "description": "Security scanning with CodeQL and dependency review",
        "category": "security",
        "template_content": """name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'

permissions:
  security-events: write
  contents: read

jobs:
  codeql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
      - name: Autobuild
        uses: github/codeql-action/autobuild@v3
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3

  dependency-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - name: Dependency Review
        uses: actions/dependency-review-action@v4
""",
        "variables": {},
        "languages": ["python", "javascript", "typescript", "java", "go"],
        "is_built_in": True
    },
    {
        "name": "Docker Build & Push",
        "description": "Build and push Docker images to registry",
        "category": "deployment",
        "template_content": """name: Docker Build & Push

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
""",
        "variables": {},
        "languages": [],
        "is_built_in": True
    }
]

# Default Local LLM Configurations
DEFAULT_LLM_CONFIGS = [
    {
        "name": "Dolphin-Mistral-24B (Default)",
        "model_id": "dphn/Dolphin-Mistral-24B-Venice-Edition",
        "device": "auto",
        "quantization": "4bit",
        "max_context_length": 8192,
        "default_temperature": "0.7",
        "default_top_p": "0.9",
        "default_max_tokens": 2048
    },
    {
        "name": "Mistral-7B-Instruct",
        "model_id": "mistralai/Mistral-7B-Instruct-v0.2",
        "device": "auto",
        "quantization": "4bit",
        "max_context_length": 32768,
        "default_temperature": "0.7",
        "default_top_p": "0.9",
        "default_max_tokens": 2048
    },
    {
        "name": "CodeLlama-34B",
        "model_id": "codellama/CodeLlama-34b-Instruct-hf",
        "device": "auto",
        "quantization": "4bit",
        "max_context_length": 16384,
        "default_temperature": "0.2",
        "default_top_p": "0.95",
        "default_max_tokens": 4096
    }
]


async def seed_system_prompts():
    """Seed default system prompts"""
    async with AsyncSessionLocal() as session:
        for prompt_data in DEFAULT_SYSTEM_PROMPTS:
            # Check if prompt already exists
            result = await session.execute(
                select(SystemPrompt).where(SystemPrompt.name == prompt_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                prompt = SystemPrompt(**prompt_data)
                session.add(prompt)
                logger.info(f"Added system prompt: {prompt_data['name']}")
            else:
                logger.info(f"System prompt already exists: {prompt_data['name']}")
        
        await session.commit()


async def seed_workflow_templates():
    """Seed default workflow templates"""
    async with AsyncSessionLocal() as session:
        for template_data in DEFAULT_WORKFLOW_TEMPLATES:
            # Check if template already exists
            result = await session.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.name == template_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                template = WorkflowTemplate(**template_data)
                session.add(template)
                logger.info(f"Added workflow template: {template_data['name']}")
            else:
                logger.info(f"Workflow template already exists: {template_data['name']}")
        
        await session.commit()


async def seed_llm_configs():
    """Seed default LLM configurations"""
    async with AsyncSessionLocal() as session:
        for config_data in DEFAULT_LLM_CONFIGS:
            # Check if config already exists
            result = await session.execute(
                select(LocalLLMConfig).where(LocalLLMConfig.name == config_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                config = LocalLLMConfig(**config_data)
                session.add(config)
                logger.info(f"Added LLM config: {config_data['name']}")
            else:
                logger.info(f"LLM config already exists: {config_data['name']}")
        
        await session.commit()


async def run_all_seeds():
    """Run all seed functions"""
    logger.info("Starting database seeding...")
    
    await seed_system_prompts()
    await seed_workflow_templates()
    await seed_llm_configs()
    
    logger.info("Database seeding completed!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_all_seeds())
