"""
Workflow Generator Service - Generates GitHub Actions workflows
Supports linting, testing, security scanning, and deployment pipelines
"""

import os
import re
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


@dataclass
class WorkflowConfig:
    """Configuration for workflow generation"""
    name: str
    languages: List[str]
    include_linting: bool = True
    include_testing: bool = True
    include_security: bool = True
    include_build: bool = True
    include_deploy: bool = False
    node_version: str = "18"
    python_version: str = "3.11"
    go_version: str = "1.21"
    java_version: str = "17"
    deploy_target: Optional[str] = None  # vercel, aws, gcp, azure, docker
    custom_steps: Optional[List[Dict[str, Any]]] = None


class WorkflowGeneratorService:
    """Service for generating GitHub Actions workflows"""
    
    # Built-in workflow templates
    TEMPLATES = {
        "linting": {
            "python": {
                "name": "Python Linting",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Python", "uses": "actions/setup-python@v5", "with": {"python-version": "{{python_version}}"}},
                    {"name": "Install dependencies", "run": "pip install flake8 pylint black isort mypy"},
                    {"name": "Run flake8", "run": "flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics"},
                    {"name": "Run pylint", "run": "pylint --disable=all --enable=E **/*.py || true"},
                    {"name": "Check formatting with black", "run": "black --check ."},
                    {"name": "Check imports with isort", "run": "isort --check-only ."},
                ]
            },
            "javascript": {
                "name": "JavaScript Linting",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Node.js", "uses": "actions/setup-node@v4", "with": {"node-version": "{{node_version}}"}},
                    {"name": "Install dependencies", "run": "npm ci"},
                    {"name": "Run ESLint", "run": "npx eslint . --ext .js,.jsx,.ts,.tsx"},
                    {"name": "Run Prettier", "run": "npx prettier --check ."},
                ]
            },
            "typescript": {
                "name": "TypeScript Linting",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Node.js", "uses": "actions/setup-node@v4", "with": {"node-version": "{{node_version}}"}},
                    {"name": "Install dependencies", "run": "npm ci"},
                    {"name": "Run ESLint", "run": "npx eslint . --ext .ts,.tsx"},
                    {"name": "Run TypeScript compiler", "run": "npx tsc --noEmit"},
                    {"name": "Run Prettier", "run": "npx prettier --check ."},
                ]
            },
            "go": {
                "name": "Go Linting",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Go", "uses": "actions/setup-go@v5", "with": {"go-version": "{{go_version}}"}},
                    {"name": "Run golangci-lint", "uses": "golangci/golangci-lint-action@v4"},
                    {"name": "Run go vet", "run": "go vet ./..."},
                ]
            },
            "rust": {
                "name": "Rust Linting",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Rust", "uses": "actions-rs/toolchain@v1", "with": {"toolchain": "stable", "components": "clippy, rustfmt"}},
                    {"name": "Run cargo fmt", "run": "cargo fmt --all -- --check"},
                    {"name": "Run clippy", "run": "cargo clippy -- -D warnings"},
                ]
            }
        },
        "testing": {
            "python": {
                "name": "Python Tests",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Python", "uses": "actions/setup-python@v5", "with": {"python-version": "{{python_version}}"}},
                    {"name": "Install dependencies", "run": "pip install -r requirements.txt pytest pytest-cov"},
                    {"name": "Run pytest", "run": "pytest --cov=. --cov-report=xml"},
                    {"name": "Upload coverage", "uses": "codecov/codecov-action@v4", "with": {"files": "./coverage.xml"}},
                ]
            },
            "javascript": {
                "name": "JavaScript Tests",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Node.js", "uses": "actions/setup-node@v4", "with": {"node-version": "{{node_version}}"}},
                    {"name": "Install dependencies", "run": "npm ci"},
                    {"name": "Run Jest", "run": "npm test -- --coverage"},
                    {"name": "Upload coverage", "uses": "codecov/codecov-action@v4"},
                ]
            },
            "typescript": {
                "name": "TypeScript Tests",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Node.js", "uses": "actions/setup-node@v4", "with": {"node-version": "{{node_version}}"}},
                    {"name": "Install dependencies", "run": "npm ci"},
                    {"name": "Run Jest", "run": "npm test -- --coverage"},
                    {"name": "Upload coverage", "uses": "codecov/codecov-action@v4"},
                ]
            },
            "go": {
                "name": "Go Tests",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Go", "uses": "actions/setup-go@v5", "with": {"go-version": "{{go_version}}"}},
                    {"name": "Run tests", "run": "go test -v -race -coverprofile=coverage.out ./..."},
                    {"name": "Upload coverage", "uses": "codecov/codecov-action@v4", "with": {"files": "./coverage.out"}},
                ]
            },
            "rust": {
                "name": "Rust Tests",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Rust", "uses": "actions-rs/toolchain@v1", "with": {"toolchain": "stable"}},
                    {"name": "Run tests", "run": "cargo test --all-features"},
                ]
            }
        },
        "security": {
            "codeql": {
                "name": "CodeQL Analysis",
                "runs-on": "ubuntu-latest",
                "permissions": {"security-events": "write"},
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Initialize CodeQL", "uses": "github/codeql-action/init@v3", "with": {"languages": "{{languages}}"}},
                    {"name": "Autobuild", "uses": "github/codeql-action/autobuild@v3"},
                    {"name": "Perform CodeQL Analysis", "uses": "github/codeql-action/analyze@v3"},
                ]
            },
            "dependabot": {
                "name": "Dependency Review",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Dependency Review", "uses": "actions/dependency-review-action@v4"},
                ]
            },
            "snyk": {
                "name": "Snyk Security Scan",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Run Snyk", "uses": "snyk/actions/node@master", "env": {"SNYK_TOKEN": "${{ secrets.SNYK_TOKEN }}"}},
                ]
            },
            "trivy": {
                "name": "Trivy Security Scan",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Run Trivy", "uses": "aquasecurity/trivy-action@master", "with": {"scan-type": "fs", "scan-ref": "."}},
                ]
            }
        },
        "deploy": {
            "vercel": {
                "name": "Deploy to Vercel",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Deploy to Vercel", "uses": "amondnet/vercel-action@v25", "with": {"vercel-token": "${{ secrets.VERCEL_TOKEN }}", "vercel-org-id": "${{ secrets.VERCEL_ORG_ID }}", "vercel-project-id": "${{ secrets.VERCEL_PROJECT_ID }}", "vercel-args": "--prod"}},
                ]
            },
            "docker": {
                "name": "Build and Push Docker",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Docker Buildx", "uses": "docker/setup-buildx-action@v3"},
                    {"name": "Login to DockerHub", "uses": "docker/login-action@v3", "with": {"username": "${{ secrets.DOCKERHUB_USERNAME }}", "password": "${{ secrets.DOCKERHUB_TOKEN }}"}},
                    {"name": "Build and push", "uses": "docker/build-push-action@v5", "with": {"push": True, "tags": "{{docker_image}}:latest"}},
                ]
            },
            "aws": {
                "name": "Deploy to AWS",
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Configure AWS credentials", "uses": "aws-actions/configure-aws-credentials@v4", "with": {"aws-access-key-id": "${{ secrets.AWS_ACCESS_KEY_ID }}", "aws-secret-access-key": "${{ secrets.AWS_SECRET_ACCESS_KEY }}", "aws-region": "{{aws_region}}"}},
                    {"name": "Deploy", "run": "echo 'Add your AWS deployment commands here'"},
                ]
            }
        }
    }
    
    def __init__(self, db_session=None):
        self.db_session = db_session
    
    def generate_workflow(self, config: WorkflowConfig) -> Dict[str, str]:
        """Generate GitHub Actions workflow files based on configuration"""
        workflows = {}
        
        # Generate CI workflow
        ci_workflow = self._generate_ci_workflow(config)
        workflows[".github/workflows/ci.yml"] = ci_workflow
        
        # Generate security workflow if enabled
        if config.include_security:
            security_workflow = self._generate_security_workflow(config)
            workflows[".github/workflows/security.yml"] = security_workflow
        
        # Generate deploy workflow if enabled
        if config.include_deploy and config.deploy_target:
            deploy_workflow = self._generate_deploy_workflow(config)
            workflows[".github/workflows/deploy.yml"] = deploy_workflow
        
        # Generate dependabot.yml
        dependabot_config = self._generate_dependabot_config(config)
        workflows[".github/dependabot.yml"] = dependabot_config
        
        return workflows
    
    def _generate_ci_workflow(self, config: WorkflowConfig) -> str:
        """Generate the main CI workflow"""
        workflow = {
            "name": f"{config.name} CI",
            "on": {
                "push": {"branches": ["main", "master", "develop"]},
                "pull_request": {"branches": ["main", "master", "develop"]}
            },
            "jobs": {}
        }
        
        # Add linting jobs
        if config.include_linting:
            for lang in config.languages:
                if lang in self.TEMPLATES["linting"]:
                    job_name = f"lint-{lang}"
                    template = self.TEMPLATES["linting"][lang].copy()
                    template["steps"] = self._substitute_variables(template["steps"], config)
                    workflow["jobs"][job_name] = template
        
        # Add testing jobs
        if config.include_testing:
            for lang in config.languages:
                if lang in self.TEMPLATES["testing"]:
                    job_name = f"test-{lang}"
                    template = self.TEMPLATES["testing"][lang].copy()
                    template["steps"] = self._substitute_variables(template["steps"], config)
                    workflow["jobs"][job_name] = template
        
        # Add build job
        if config.include_build:
            build_job = self._generate_build_job(config)
            workflow["jobs"]["build"] = build_job
        
        # Add custom steps if provided
        if config.custom_steps:
            workflow["jobs"]["custom"] = {
                "name": "Custom Steps",
                "runs-on": "ubuntu-latest",
                "steps": [{"uses": "actions/checkout@v4"}] + config.custom_steps
            }
        
        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    
    def _generate_security_workflow(self, config: WorkflowConfig) -> str:
        """Generate security scanning workflow"""
        # Map languages to CodeQL languages
        codeql_lang_map = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "javascript",
            "java": "java",
            "go": "go",
            "cpp": "cpp",
            "c": "cpp",
            "ruby": "ruby",
            "csharp": "csharp"
        }
        
        codeql_languages = list(set(
            codeql_lang_map.get(lang, lang)
            for lang in config.languages
            if lang in codeql_lang_map
        ))
        
        workflow = {
            "name": f"{config.name} Security",
            "on": {
                "push": {"branches": ["main", "master"]},
                "pull_request": {"branches": ["main", "master"]},
                "schedule": [{"cron": "0 0 * * 0"}]  # Weekly on Sunday
            },
            "jobs": {}
        }
        
        # Add CodeQL analysis
        if codeql_languages:
            codeql_template = self.TEMPLATES["security"]["codeql"].copy()
            codeql_template["steps"] = self._substitute_variables(
                codeql_template["steps"],
                config,
                {"languages": ", ".join(codeql_languages)}
            )
            workflow["jobs"]["codeql"] = codeql_template
        
        # Add dependency review
        workflow["jobs"]["dependency-review"] = self.TEMPLATES["security"]["dependabot"].copy()
        
        # Add Trivy scan
        workflow["jobs"]["trivy"] = self.TEMPLATES["security"]["trivy"].copy()
        
        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    
    def _generate_deploy_workflow(self, config: WorkflowConfig) -> str:
        """Generate deployment workflow"""
        workflow = {
            "name": f"{config.name} Deploy",
            "on": {
                "push": {"branches": ["main", "master"]},
                "workflow_dispatch": {}
            },
            "jobs": {}
        }
        
        if config.deploy_target in self.TEMPLATES["deploy"]:
            deploy_template = self.TEMPLATES["deploy"][config.deploy_target].copy()
            deploy_template["steps"] = self._substitute_variables(deploy_template["steps"], config)
            workflow["jobs"]["deploy"] = deploy_template
        
        return yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    
    def _generate_build_job(self, config: WorkflowConfig) -> Dict[str, Any]:
        """Generate build job based on languages"""
        job = {
            "name": "Build",
            "runs-on": "ubuntu-latest",
            "steps": [{"uses": "actions/checkout@v4"}]
        }
        
        for lang in config.languages:
            if lang == "python":
                job["steps"].extend([
                    {"name": "Set up Python", "uses": "actions/setup-python@v5", "with": {"python-version": config.python_version}},
                    {"name": "Install dependencies", "run": "pip install -r requirements.txt"},
                ])
            elif lang in ["javascript", "typescript"]:
                job["steps"].extend([
                    {"name": "Set up Node.js", "uses": "actions/setup-node@v4", "with": {"node-version": config.node_version}},
                    {"name": "Install dependencies", "run": "npm ci"},
                    {"name": "Build", "run": "npm run build"},
                ])
            elif lang == "go":
                job["steps"].extend([
                    {"name": "Set up Go", "uses": "actions/setup-go@v5", "with": {"go-version": config.go_version}},
                    {"name": "Build", "run": "go build -v ./..."},
                ])
            elif lang == "rust":
                job["steps"].extend([
                    {"name": "Set up Rust", "uses": "actions-rs/toolchain@v1", "with": {"toolchain": "stable"}},
                    {"name": "Build", "run": "cargo build --release"},
                ])
            elif lang == "java":
                job["steps"].extend([
                    {"name": "Set up JDK", "uses": "actions/setup-java@v4", "with": {"java-version": config.java_version, "distribution": "temurin"}},
                    {"name": "Build with Maven", "run": "mvn -B package --file pom.xml"},
                ])
        
        return job
    
    def _generate_dependabot_config(self, config: WorkflowConfig) -> str:
        """Generate dependabot.yml configuration"""
        dependabot = {
            "version": 2,
            "updates": []
        }
        
        # Add package ecosystem updates based on languages
        ecosystem_map = {
            "python": "pip",
            "javascript": "npm",
            "typescript": "npm",
            "go": "gomod",
            "rust": "cargo",
            "java": "maven",
            "ruby": "bundler",
            "php": "composer"
        }
        
        added_ecosystems = set()
        for lang in config.languages:
            ecosystem = ecosystem_map.get(lang)
            if ecosystem and ecosystem not in added_ecosystems:
                dependabot["updates"].append({
                    "package-ecosystem": ecosystem,
                    "directory": "/",
                    "schedule": {"interval": "weekly"},
                    "open-pull-requests-limit": 10
                })
                added_ecosystems.add(ecosystem)
        
        # Always add GitHub Actions updates
        dependabot["updates"].append({
            "package-ecosystem": "github-actions",
            "directory": "/",
            "schedule": {"interval": "weekly"}
        })
        
        return yaml.dump(dependabot, default_flow_style=False, sort_keys=False)
    
    def _substitute_variables(self, steps: List[Dict[str, Any]], config: WorkflowConfig, extra_vars: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Substitute template variables in workflow steps"""
        variables = {
            "node_version": config.node_version,
            "python_version": config.python_version,
            "go_version": config.go_version,
            "java_version": config.java_version,
            "docker_image": f"${{{{ github.repository }}}}",
            "aws_region": "us-east-1"
        }
        
        if extra_vars:
            variables.update(extra_vars)
        
        def substitute(obj):
            if isinstance(obj, str):
                for key, value in variables.items():
                    obj = obj.replace(f"{{{{{key}}}}}", value)
                return obj
            elif isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute(item) for item in obj]
            return obj
        
        return substitute(steps)
    
    async def generate_for_project(self, project_id: str, config: WorkflowConfig) -> Dict[str, Any]:
        """Generate workflows for a specific project"""
        if not self.db_session:
            return {"success": False, "error": "No database session"}
        
        try:
            from sqlalchemy import select
            from app.database.models import Project, File
            
            # Get project
            result = await self.db_session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                return {"success": False, "error": "Project not found"}
            
            # Detect languages from project files
            result = await self.db_session.execute(
                select(File).where(File.project_id == project_id)
            )
            files = result.scalars().all()
            
            detected_languages = set()
            for file in files:
                if file.language:
                    detected_languages.add(file.language)
            
            # Update config with detected languages if not specified
            if not config.languages:
                config.languages = list(detected_languages)
            
            # Generate workflows
            workflows = self.generate_workflow(config)
            
            # Save workflow files to project
            for path, content in workflows.items():
                existing = await self.db_session.execute(
                    select(File).where(File.project_id == project_id, File.path == path)
                )
                existing_file = existing.scalar_one_or_none()
                
                if existing_file:
                    existing_file.content = content
                else:
                    new_file = File(
                        project_id=project_id,
                        path=path,
                        content=content,
                        language="yaml"
                    )
                    self.db_session.add(new_file)
            
            await self.db_session.commit()
            
            return {
                "success": True,
                "workflows": list(workflows.keys()),
                "languages_detected": list(detected_languages)
            }
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to generate workflows: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_template_to_db(self, name: str, category: str, content: str, description: str = None, variables: Dict = None, languages: List[str] = None) -> Dict[str, Any]:
        """Save a custom workflow template to the database"""
        if not self.db_session:
            return {"success": False, "error": "No database session"}
        
        try:
            from app.database.models import WorkflowTemplate
            
            template = WorkflowTemplate(
                name=name,
                description=description,
                category=category,
                template_content=content,
                variables=variables or {},
                languages=languages or [],
                is_built_in=False
            )
            
            self.db_session.add(template)
            await self.db_session.commit()
            await self.db_session.refresh(template)
            
            return {"success": True, "template_id": template.id}
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to save template: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_templates_from_db(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get workflow templates from the database"""
        if not self.db_session:
            return []
        
        try:
            from sqlalchemy import select
            from app.database.models import WorkflowTemplate
            
            query = select(WorkflowTemplate).where(WorkflowTemplate.is_active == True)
            if category:
                query = query.where(WorkflowTemplate.category == category)
            
            result = await self.db_session.execute(query.order_by(WorkflowTemplate.name))
            templates = result.scalars().all()
            
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "template_content": t.template_content,
                    "variables": t.variables,
                    "languages": t.languages,
                    "is_built_in": t.is_built_in
                }
                for t in templates
            ]
            
        except Exception as e:
            logger.error(f"Failed to get templates: {e}")
            return []
