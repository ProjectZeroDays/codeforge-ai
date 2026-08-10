"""
Code Completion Service - Interactive development and code completion
Analyzes incomplete code, identifies missing functions, and generates implementations
Includes Development Wizard for project scaffolding and guidance
"""

import os
import re
import asyncio
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import json
import yaml

logger = logging.getLogger(__name__)


@dataclass
class MissingFunction:
    """Represents a missing or incomplete function"""
    name: str
    file_path: str
    line_number: int
    signature: Optional[str] = None
    expected_return_type: Optional[str] = None
    called_with: List[str] = field(default_factory=list)
    context: Optional[str] = None


@dataclass
class CompletionSuggestion:
    """Represents a code completion suggestion"""
    code: str
    explanation: str
    confidence: float
    file_path: Optional[str] = None
    position: Optional[Dict[str, int]] = None


@dataclass
class DevelopmentDecision:
    """Represents a development decision made during wizard process"""
    category: str  # architecture, pattern, standard, dependency
    question: str
    answer: str
    implications: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WizardSession:
    """Represents an interactive development wizard session"""
    id: str
    project_id: Optional[str] = None
    phase: str = "init"  # init, structure, standards, patterns, scaffolding, complete
    decisions: List[DevelopmentDecision] = field(default_factory=list)
    generated_files: Dict[str, str] = field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)


class CodeCompletionService:
    """Service for code completion and interactive development"""
    
    # Patterns for detecting incomplete code
    INCOMPLETE_PATTERNS = {
        "python": {
            "stub_function": r"def\s+(\w+)\([^)]*\):\s*(?:pass|\.\.\.|\#\s*TODO)",
            "undefined_call": r"(\w+)\([^)]*\)",
            "import_error": r"(?:from|import)\s+([\w.]+)",
            "type_hint": r"->\s*(\w+)",
        },
        "javascript": {
            "stub_function": r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>)\s*{\s*(?:\/\/\s*TODO|throw\s+new\s+Error)",
            "undefined_call": r"(\w+)\([^)]*\)",
            "import_error": r"(?:import|require)\(['\"]([^'\"]+)['\"]\)",
        },
        "typescript": {
            "stub_function": r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?\([^)]*\):\s*\w+\s*=>)\s*{\s*(?:\/\/\s*TODO|throw\s+new\s+Error)",
            "undefined_call": r"(\w+)\([^)]*\)",
            "type_error": r":\s*([\w<>\[\]]+)",
        },
    }
    
    # Wizard questions by phase
    WIZARD_QUESTIONS = {
        "structure": [
            {"id": "project_type", "question": "What type of project are you building?", "options": ["Web Application", "API/Backend", "CLI Tool", "Library/Package", "Full-Stack App", "Microservice"]},
            {"id": "primary_language", "question": "What is the primary programming language?", "options": ["Python", "JavaScript/TypeScript", "Go", "Rust", "Java", "Other"]},
            {"id": "framework", "question": "Which framework do you want to use?", "depends_on": "primary_language"},
            {"id": "database", "question": "What database will you use?", "options": ["PostgreSQL", "MySQL", "MongoDB", "SQLite", "Redis", "None"]},
        ],
        "standards": [
            {"id": "code_style", "question": "What code style guide do you want to follow?", "depends_on": "primary_language"},
            {"id": "testing", "question": "What testing approach do you prefer?", "options": ["TDD (Test-Driven)", "Unit Tests Only", "Integration Tests", "E2E Tests", "All of the above"]},
            {"id": "documentation", "question": "How should code be documented?", "options": ["JSDoc/PyDoc style", "Inline comments", "README only", "Full documentation site"]},
            {"id": "error_handling", "question": "What error handling strategy?", "options": ["Try-Catch with custom errors", "Result types", "Error codes", "Logging only"]},
        ],
        "patterns": [
            {"id": "architecture", "question": "What architectural pattern do you want?", "options": ["MVC", "Clean Architecture", "Hexagonal", "Microservices", "Monolith", "Serverless"]},
            {"id": "state_management", "question": "How will you manage state?", "depends_on": "project_type"},
            {"id": "api_style", "question": "What API style?", "options": ["REST", "GraphQL", "gRPC", "tRPC", "WebSocket"]},
            {"id": "dependency_injection", "question": "Use dependency injection?", "options": ["Yes, with container", "Yes, manual", "No"]},
        ],
    }
    
    def __init__(self, db_session=None, ai_service=None):
        self.db_session = db_session
        self.ai_service = ai_service
        self.active_sessions: Dict[str, WizardSession] = {}
    
    async def analyze_code(self, code: str, language: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze code to identify missing functions and incomplete implementations"""
        
        missing_functions = []
        incomplete_sections = []
        suggestions = []
        
        # Get patterns for the language
        patterns = self.INCOMPLETE_PATTERNS.get(language, {})
        
        # Find stub functions
        if "stub_function" in patterns:
            for match in re.finditer(patterns["stub_function"], code, re.MULTILINE):
                func_name = match.group(1) or match.group(2)
                if func_name:
                    line_number = code[:match.start()].count('\n') + 1
                    missing_functions.append(MissingFunction(
                        name=func_name,
                        file_path=context.get("file_path", "unknown") if context else "unknown",
                        line_number=line_number,
                        context=self._extract_context(code, match.start(), match.end())
                    ))
        
        # Find undefined function calls
        defined_functions = set(re.findall(r"(?:def|function)\s+(\w+)", code))
        imported_names = set(re.findall(r"(?:from\s+\w+\s+)?import\s+(\w+)", code))
        
        for match in re.finditer(r"(\w+)\s*\(", code):
            func_name = match.group(1)
            if func_name not in defined_functions and func_name not in imported_names:
                # Check if it's a built-in or common function
                if not self._is_builtin(func_name, language):
                    line_number = code[:match.start()].count('\n') + 1
                    # Extract call arguments
                    call_end = self._find_matching_paren(code, match.end() - 1)
                    args = code[match.end():call_end] if call_end else ""
                    
                    if not any(mf.name == func_name for mf in missing_functions):
                        missing_functions.append(MissingFunction(
                            name=func_name,
                            file_path=context.get("file_path", "unknown") if context else "unknown",
                            line_number=line_number,
                            called_with=[args] if args else []
                        ))
        
        # Use AI to suggest completions if available
        if self.ai_service and missing_functions:
            ai_suggestions = await self._get_ai_completions(code, language, missing_functions)
            suggestions.extend(ai_suggestions)
        
        return {
            "missing_functions": [
                {
                    "name": mf.name,
                    "file_path": mf.file_path,
                    "line_number": mf.line_number,
                    "signature": mf.signature,
                    "context": mf.context
                }
                for mf in missing_functions
            ],
            "incomplete_sections": incomplete_sections,
            "suggestions": [
                {
                    "code": s.code,
                    "explanation": s.explanation,
                    "confidence": s.confidence
                }
                for s in suggestions
            ],
            "analysis_summary": {
                "total_missing": len(missing_functions),
                "total_suggestions": len(suggestions),
                "language": language
            }
        }
    
    def _extract_context(self, code: str, start: int, end: int, context_lines: int = 3) -> str:
        """Extract context around a code position"""
        lines = code.split('\n')
        start_line = code[:start].count('\n')
        end_line = code[:end].count('\n')
        
        context_start = max(0, start_line - context_lines)
        context_end = min(len(lines), end_line + context_lines + 1)
        
        return '\n'.join(lines[context_start:context_end])
    
    def _find_matching_paren(self, code: str, start: int) -> Optional[int]:
        """Find the matching closing parenthesis"""
        if start >= len(code) or code[start] != '(':
            return None
        
        depth = 1
        pos = start + 1
        
        while pos < len(code) and depth > 0:
            if code[pos] == '(':
                depth += 1
            elif code[pos] == ')':
                depth -= 1
            pos += 1
        
        return pos - 1 if depth == 0 else None
    
    def _is_builtin(self, func_name: str, language: str) -> bool:
        """Check if a function is a built-in for the language"""
        builtins = {
            "python": {"print", "len", "range", "str", "int", "float", "list", "dict", "set", "tuple", "open", "type", "isinstance", "hasattr", "getattr", "setattr", "enumerate", "zip", "map", "filter", "sorted", "reversed", "sum", "min", "max", "abs", "round", "input", "format", "repr", "id", "hash", "callable", "dir", "vars", "globals", "locals", "super", "property", "classmethod", "staticmethod"},
            "javascript": {"console", "Math", "JSON", "Object", "Array", "String", "Number", "Boolean", "Date", "RegExp", "Error", "Promise", "Map", "Set", "setTimeout", "setInterval", "fetch", "alert", "confirm", "prompt", "parseInt", "parseFloat", "isNaN", "isFinite", "encodeURI", "decodeURI"},
            "typescript": {"console", "Math", "JSON", "Object", "Array", "String", "Number", "Boolean", "Date", "RegExp", "Error", "Promise", "Map", "Set", "setTimeout", "setInterval", "fetch"}
        }
        
        return func_name in builtins.get(language, set())
    
    async def _get_ai_completions(self, code: str, language: str, missing: List[MissingFunction]) -> List[CompletionSuggestion]:
        """Get AI-powered code completions"""
        suggestions = []
        
        for mf in missing[:5]:  # Limit to first 5 to avoid too many API calls
            prompt = f"""Analyze this {language} code and generate an implementation for the missing function '{mf.name}'.

Context:
```{language}
{mf.context or code[:500]}
```

The function is called with arguments: {', '.join(mf.called_with) if mf.called_with else 'unknown'}

Generate a complete, production-ready implementation. Include:
1. Proper error handling
2. Type hints (if applicable)
3. Documentation/docstring
4. Any necessary imports

Return only the function implementation code."""
            
            try:
                if hasattr(self.ai_service, 'generate_code'):
                    result = await self.ai_service.generate_code(prompt, language)
                    if result.get("code_blocks"):
                        suggestions.append(CompletionSuggestion(
                            code=result.get("raw_response", ""),
                            explanation=f"AI-generated implementation for {mf.name}",
                            confidence=0.8,
                            file_path=mf.file_path,
                            position={"line": mf.line_number, "column": 0}
                        ))
            except Exception as e:
                logger.error(f"AI completion failed: {e}")
        
        return suggestions
    
    async def complete_function(self, code: str, function_name: str, language: str, requirements: Optional[str] = None) -> Dict[str, Any]:
        """Generate a complete implementation for a specific function"""
        
        prompt = f"""Generate a complete, production-ready implementation for the function '{function_name}' in {language}.

Existing code context:
```{language}
{code[:2000]}
```

Requirements: {requirements or 'Follow best practices and include error handling'}

Generate:
1. The complete function implementation
2. Any necessary helper functions
3. Required imports
4. Unit tests for the function

Format the response as JSON with keys: implementation, helpers, imports, tests"""
        
        if self.ai_service:
            try:
                result = await self.ai_service.generate_code(prompt, language)
                if result.get("code_blocks"):
                    return {
                        "success": True,
                        "implementation": result.get("raw_response", ""),
                        "function_name": function_name,
                        "language": language
                    }
            except Exception as e:
                logger.error(f"Function completion failed: {e}")
        
        return {"success": False, "error": "AI service unavailable"}
    
    # Development Wizard Methods
    
    async def start_wizard_session(self, project_id: Optional[str] = None) -> WizardSession:
        """Start a new development wizard session"""
        import uuid
        
        session = WizardSession(
            id=str(uuid.uuid4()),
            project_id=project_id,
            phase="init"
        )
        
        self.active_sessions[session.id] = session
        
        # Save to database if available
        if self.db_session:
            await self._save_session_to_db(session)
        
        return session
    
    async def get_wizard_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the next question for the wizard session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        # Determine current phase questions
        phase_questions = self.WIZARD_QUESTIONS.get(session.phase, [])
        
        # Find next unanswered question
        answered_ids = {d.question for d in session.decisions}

        for question in phase_questions:
            if question["id"] not in answered_ids:
                # Handle dynamic options based on previous answers
                if "depends_on" in question:
                    dep_answer = next(
                        (d.answer for d in session.decisions if d.category == question["depends_on"]),
                        None
                    )
                    options = self._get_dynamic_options(question["id"], dep_answer)
                    return {**question, "options": options}
                return question
        
        # All questions in phase answered, move to next phase
        phases = ["init", "structure", "standards", "patterns", "scaffolding", "complete"]
        current_idx = phases.index(session.phase)
        
        if current_idx < len(phases) - 1:
            session.phase = phases[current_idx + 1]
            return await self.get_wizard_question(session_id)
        
        return {"phase": "complete", "message": "All questions answered. Ready to generate scaffolding."}
    
    def _get_dynamic_options(self, question_id: str, dependency_answer: Optional[str]) -> List[str]:
        """Get dynamic options based on previous answers"""
        options_map = {
            "framework": {
                "Python": ["FastAPI", "Django", "Flask", "Tornado", "Starlette"],
                "JavaScript/TypeScript": ["Next.js", "Express", "NestJS", "Fastify", "Hono"],
                "Go": ["Gin", "Echo", "Fiber", "Chi", "Standard Library"],
                "Rust": ["Actix-web", "Rocket", "Axum", "Warp"],
                "Java": ["Spring Boot", "Quarkus", "Micronaut", "Vert.x"],
            },
            "code_style": {
                "Python": ["PEP 8", "Google Python Style", "Black formatter"],
                "JavaScript/TypeScript": ["Airbnb", "Standard", "Google", "Prettier"],
                "Go": ["gofmt (official)", "golangci-lint"],
                "Rust": ["rustfmt", "clippy"],
            },
            "state_management": {
                "Web Application": ["Redux", "Zustand", "MobX", "Jotai", "Context API"],
                "API/Backend": ["Database", "In-memory cache", "Redis", "Session-based"],
            }
        }
        
        return options_map.get(question_id, {}).get(dependency_answer, ["Other"])
    
    async def answer_wizard_question(self, session_id: str, question_id: str, answer: str) -> Dict[str, Any]:
        """Submit an answer to a wizard question"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Create decision
        decision = DevelopmentDecision(
            category=question_id,
            question=question_id,
            answer=answer,
            implications=self._get_implications(question_id, answer)
        )
        
        session.decisions.append(decision)
        session.conversation_history.append({
            "role": "user",
            "content": f"Selected: {answer} for {question_id}"
        })
        
        # Save to database
        if self.db_session:
            await self._save_session_to_db(session)
        
        # Get next question
        next_question = await self.get_wizard_question(session_id)
        
        return {
            "success": True,
            "decision_recorded": question_id,
            "next_question": next_question,
            "phase": session.phase
        }
    
    def _get_implications(self, question_id: str, answer: str) -> List[str]:
        """Get implications of a decision"""
        implications_map = {
            ("project_type", "Web Application"): ["Will need frontend framework", "Consider SSR/SSG", "Need routing solution"],
            ("project_type", "API/Backend"): ["Focus on REST/GraphQL design", "Need authentication strategy", "Consider rate limiting"],
            ("database", "PostgreSQL"): ["Need psycopg2 or asyncpg", "Support for JSON columns", "Consider migrations"],
            ("architecture", "Clean Architecture"): ["Separate domain, application, infrastructure layers", "Use dependency injection", "Create interfaces for repositories"],
        }
        
        return implications_map.get((question_id, answer), [])
    
    async def generate_scaffolding(self, session_id: str) -> Dict[str, Any]:
        """Generate project scaffolding based on wizard decisions"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Extract decisions
        decisions_dict = {d.category: d.answer for d in session.decisions}
        
        # Generate file structure based on decisions
        files = await self._generate_project_files(decisions_dict)
        
        session.generated_files = files
        session.phase = "complete"
        
        # Save to database
        if self.db_session:
            await self._save_session_to_db(session)
        
        return {
            "success": True,
            "files": list(files.keys()),
            "total_files": len(files),
            "decisions_applied": len(session.decisions)
        }
    
    async def _generate_project_files(self, decisions: Dict[str, str]) -> Dict[str, str]:
        """Generate project files based on decisions"""
        files = {}
        
        project_type = decisions.get("project_type", "Web Application")
        language = decisions.get("primary_language", "Python")
        framework = decisions.get("framework", "")
        
        # Generate common files
        files["README.md"] = self._generate_readme(decisions)
        files[".gitignore"] = self._generate_gitignore(language)
        
        # Language-specific files
        if language == "Python":
            files["requirements.txt"] = self._generate_requirements(decisions)
            files["pyproject.toml"] = self._generate_pyproject(decisions)
            files["src/__init__.py"] = ""
            files["src/main.py"] = self._generate_python_main(decisions)
            files["tests/__init__.py"] = ""
            files["tests/test_main.py"] = self._generate_python_tests(decisions)
            
        elif language in ["JavaScript/TypeScript", "JavaScript", "TypeScript"]:
            files["package.json"] = self._generate_package_json(decisions)
            files["tsconfig.json"] = self._generate_tsconfig(decisions)
            files["src/index.ts"] = self._generate_ts_main(decisions)
            files["src/types.ts"] = self._generate_ts_types(decisions)
            files["tests/index.test.ts"] = self._generate_ts_tests(decisions)
        
        # Framework-specific files
        if framework == "FastAPI":
            files["src/api/__init__.py"] = ""
            files["src/api/routes.py"] = self._generate_fastapi_routes(decisions)
            files["src/models/__init__.py"] = ""
            files["src/models/schemas.py"] = self._generate_fastapi_schemas(decisions)
        
        elif framework == "Next.js":
            files["src/app/page.tsx"] = self._generate_nextjs_page(decisions)
            files["src/app/layout.tsx"] = self._generate_nextjs_layout(decisions)
        
        # Docker files if needed
        files["Dockerfile"] = self._generate_dockerfile(decisions)
        files["docker-compose.yml"] = self._generate_docker_compose(decisions)
        
        return files
    
    def _generate_readme(self, decisions: Dict[str, str]) -> str:
        """Generate README.md"""
        return f"""# {decisions.get('project_name', 'New Project')}

## Overview

{decisions.get('project_type', 'Application')} built with {decisions.get('primary_language', 'Python')} and {decisions.get('framework', 'standard library')}.

## Architecture

- **Pattern**: {decisions.get('architecture', 'Standard')}
- **API Style**: {decisions.get('api_style', 'REST')}
- **Database**: {decisions.get('database', 'None')}

## Getting Started

### Prerequisites

- {decisions.get('primary_language', 'Python')} installed
- {decisions.get('database', 'No database') + ' (if applicable)'}

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd <project-name>

# Install dependencies
# (language-specific commands)
```

### Running the Application

```bash
# Start the development server
# (language-specific commands)
```

## Testing

```bash
# Run tests
# (language-specific commands)
```

## Development Standards

- **Code Style**: {decisions.get('code_style', 'Standard')}
- **Testing**: {decisions.get('testing', 'Unit Tests')}
- **Documentation**: {decisions.get('documentation', 'README only')}

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License
"""
    
    def _generate_gitignore(self, language: str) -> str:
        """Generate .gitignore based on language"""
        base = """# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local
"""
        
        if language == "Python":
            base += """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.venv/
*.egg-info/
dist/
build/
.eggs/
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
"""
        elif language in ["JavaScript/TypeScript", "JavaScript", "TypeScript"]:
            base += """
# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.next/
out/
dist/
build/
coverage/
.nyc_output/
"""
        
        return base
    
    def _generate_requirements(self, decisions: Dict[str, str]) -> str:
        """Generate Python requirements.txt"""
        requirements = []
        
        framework = decisions.get("framework", "")
        if framework == "FastAPI":
            requirements.extend(["fastapi>=0.109.0", "uvicorn[standard]>=0.27.0", "pydantic>=2.5.0"])
        elif framework == "Django":
            requirements.append("django>=5.0.0")
        elif framework == "Flask":
            requirements.append("flask>=3.0.0")
        
        database = decisions.get("database", "")
        if database == "PostgreSQL":
            requirements.extend(["psycopg2-binary>=2.9.9", "sqlalchemy>=2.0.0"])
        elif database == "MongoDB":
            requirements.append("motor>=3.3.0")
        
        # Testing
        requirements.extend(["pytest>=7.4.0", "pytest-cov>=4.1.0", "pytest-asyncio>=0.23.0"])
        
        return "\n".join(requirements)
    
    def _generate_pyproject(self, decisions: Dict[str, str]) -> str:
        """Generate pyproject.toml"""
        return """[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "project-name"
version = "0.1.0"
description = "Project description"
requires-python = ">=3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
strict = true
"""
    
    def _generate_python_main(self, decisions: Dict[str, str]) -> str:
        """Generate Python main.py"""
        framework = decisions.get("framework", "")
        
        if framework == "FastAPI":
            return '''"""Main application entry point."""
from fastapi import FastAPI
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting up...")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="API",
    description="API Description",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello, World!"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
'''
        
        return '''"""Main application entry point."""


def main():
    """Main function."""
    print("Hello, World!")


if __name__ == "__main__":
    main()
'''
    
    def _generate_python_tests(self, decisions: Dict[str, str]) -> str:
        """Generate Python tests"""
        return '''"""Tests for main module."""
import pytest


def test_example():
    """Example test."""
    assert True


@pytest.mark.asyncio
async def test_async_example():
    """Example async test."""
    assert True
'''
    
    def _generate_package_json(self, decisions: Dict[str, str]) -> str:
        """Generate package.json"""
        framework = decisions.get("framework", "")
        
        deps = {
            "Next.js": {"next": "^14.0.0", "react": "^18.2.0", "react-dom": "^18.2.0"},
            "Express": {"express": "^4.18.0"},
            "NestJS": {"@nestjs/core": "^10.0.0", "@nestjs/common": "^10.0.0"}
        }
        
        return json.dumps({
            "name": "project-name",
            "version": "0.1.0",
            "scripts": {
                "dev": "next dev" if framework == "Next.js" else "ts-node src/index.ts",
                "build": "next build" if framework == "Next.js" else "tsc",
                "start": "next start" if framework == "Next.js" else "node dist/index.js",
                "test": "jest",
                "lint": "eslint . --ext .ts,.tsx"
            },
            "dependencies": deps.get(framework, {}),
            "devDependencies": {
                "typescript": "^5.3.0",
                "@types/node": "^20.0.0",
                "jest": "^29.7.0",
                "@types/jest": "^29.5.0",
                "ts-jest": "^29.1.0",
                "eslint": "^8.56.0",
                "@typescript-eslint/eslint-plugin": "^6.0.0",
                "@typescript-eslint/parser": "^6.0.0"
            }
        }, indent=2)
    
    def _generate_tsconfig(self, decisions: Dict[str, str]) -> str:
        """Generate tsconfig.json"""
        return json.dumps({
            "compilerOptions": {
                "target": "ES2022",
                "module": "NodeNext",
                "moduleResolution": "NodeNext",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "outDir": "./dist",
                "rootDir": "./src",
                "declaration": True,
                "declarationMap": True,
                "sourceMap": True
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules", "dist"]
        }, indent=2)
    
    def _generate_ts_main(self, decisions: Dict[str, str]) -> str:
        """Generate TypeScript main file"""
        return '''/**
 * Main application entry point
 */

async function main(): Promise<void> {
    console.log("Hello, World!");
}

main().catch(console.error);
'''
    
    def _generate_ts_types(self, decisions: Dict[str, str]) -> str:
        """Generate TypeScript types"""
        return '''/**
 * Type definitions
 */

export interface AppConfig {
    port: number;
    environment: "development" | "production" | "test";
}

export interface User {
    id: string;
    name: string;
    email: string;
    createdAt: Date;
}
'''
    
    def _generate_ts_tests(self, decisions: Dict[str, str]) -> str:
        """Generate TypeScript tests"""
        return '''/**
 * Tests for main module
 */

describe("Main", () => {
    it("should pass example test", () => {
        expect(true).toBe(true);
    });
});
'''
    
    def _generate_fastapi_routes(self, decisions: Dict[str, str]) -> str:
        """Generate FastAPI routes"""
        return '''"""API Routes."""
from fastapi import APIRouter, HTTPException
from typing import List
from .models.schemas import Item, ItemCreate

router = APIRouter(prefix="/api/v1", tags=["items"])


@router.get("/items", response_model=List[Item])
async def list_items():
    """List all items."""
    return []


@router.post("/items", response_model=Item)
async def create_item(item: ItemCreate):
    """Create a new item."""
    return Item(id="1", **item.model_dump())


@router.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: str):
    """Get an item by ID."""
    raise HTTPException(status_code=404, detail="Item not found")
'''
    
    def _generate_fastapi_schemas(self, decisions: Dict[str, str]) -> str:
        """Generate FastAPI Pydantic schemas"""
        return '''"""Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ItemBase(BaseModel):
    """Base item schema."""
    name: str
    description: Optional[str] = None


class ItemCreate(ItemBase):
    """Schema for creating items."""
    pass


class Item(ItemBase):
    """Schema for item responses."""
    id: str
    created_at: datetime = None
    
    class Config:
        from_attributes = True
'''
    
    def _generate_nextjs_page(self, decisions: Dict[str, str]) -> str:
        """Generate Next.js page"""
        return '''export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold">Welcome</h1>
      <p className="mt-4 text-gray-600">Get started by editing this page.</p>
    </main>
  );
}
'''
    
    def _generate_nextjs_layout(self, decisions: Dict[str, str]) -> str:
        """Generate Next.js layout"""
        return '''import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "App",
  description: "App description",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
'''
    
    def _generate_dockerfile(self, decisions: Dict[str, str]) -> str:
        """Generate Dockerfile"""
        language = decisions.get("primary_language", "Python")
        
        if language == "Python":
            return '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
        
        return '''FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
'''
    
    def _generate_docker_compose(self, decisions: Dict[str, str]) -> str:
        """Generate docker-compose.yml"""
        database = decisions.get("database", "")
        
        compose = {
            "version": "3.8",
            "services": {
                "app": {
                    "build": ".",
                    "ports": ["8000:8000"],
                    "environment": ["DATABASE_URL=postgresql://user:password@db:5432/app"]
                }
            }
        }
        
        if database == "PostgreSQL":
            compose["services"]["db"] = {
                "image": "postgres:16",
                "environment": {
                    "POSTGRES_USER": "user",
                    "POSTGRES_PASSWORD": "password",
                    "POSTGRES_DB": "app"
                },
                "volumes": ["postgres_data:/var/lib/postgresql/data"]
            }
            compose["volumes"] = {"postgres_data": {}}
        
        return yaml.dump(compose, default_flow_style=False)
    
    async def _save_session_to_db(self, session: WizardSession) -> None:
        """Save wizard session to database"""
        if not self.db_session:
            return
        
        try:
            from sqlalchemy import select
            from app.database.models import CodeCompletionSession
            
            # Check if session exists
            result = await self.db_session.execute(
                select(CodeCompletionSession).where(CodeCompletionSession.id == session.id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.status = "active" if session.phase != "complete" else "completed"
                existing.conversation_history = session.conversation_history
                existing.decisions_made = [
                    {"category": d.category, "question": d.question, "answer": d.answer}
                    for d in session.decisions
                ]
                existing.generated_artifacts = list(session.generated_files.keys())
            else:
                db_session = CodeCompletionSession(
                    id=session.id,
                    project_id=session.project_id,
                    session_type="wizard",
                    status="active",
                    conversation_history=session.conversation_history,
                    decisions_made=[
                        {"category": d.category, "question": d.question, "answer": d.answer}
                        for d in session.decisions
                    ]
                )
                self.db_session.add(db_session)
            
            await self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            await self.db_session.rollback()
