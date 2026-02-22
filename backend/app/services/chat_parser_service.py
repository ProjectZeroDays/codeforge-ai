"""
Chat Parser Service - Extracts code blocks from AI chat transcripts
Supports DOCX, PDF, TXT, HTML, and Markdown files
Automatically identifies programming languages and reconstructs project structures
"""

import os
import re
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import tempfile
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CodeBlock:
    """Represents an extracted code block"""
    content: str
    language: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    confidence: float = 1.0
    source_format: Optional[str] = None


@dataclass
class ExtractedProject:
    """Represents an extracted project structure"""
    files: Dict[str, str] = field(default_factory=dict)  # path -> content
    code_blocks: List[CodeBlock] = field(default_factory=list)
    languages_detected: List[str] = field(default_factory=list)
    source_format: Optional[str] = None
    readme_content: Optional[str] = None


class ChatParserService:
    """Service for parsing chat logs and extracting code"""
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": [r"\.py$", r"^#!/usr/bin/env python", r"^#!/usr/bin/python", r"import\s+\w+", r"from\s+\w+\s+import", r"def\s+\w+\(", r"class\s+\w+:"],
        "javascript": [r"\.js$", r"const\s+\w+\s*=", r"let\s+\w+\s*=", r"function\s+\w+\(", r"=>\s*{", r"require\(", r"module\.exports"],
        "typescript": [r"\.ts$", r"\.tsx$", r"interface\s+\w+", r"type\s+\w+\s*=", r":\s*(string|number|boolean|any)\b"],
        "java": [r"\.java$", r"public\s+class", r"private\s+\w+\s+\w+;", r"System\.out\.println"],
        "go": [r"\.go$", r"package\s+\w+", r"func\s+\w+\(", r"import\s+\""],
        "rust": [r"\.rs$", r"fn\s+\w+\(", r"let\s+mut\s+", r"impl\s+\w+", r"use\s+\w+::"],
        "cpp": [r"\.cpp$", r"\.cc$", r"\.cxx$", r"#include\s*<", r"std::", r"int\s+main\("],
        "c": [r"\.c$", r"\.h$", r"#include\s*<", r"int\s+main\(", r"printf\("],
        "html": [r"\.html$", r"\.htm$", r"<!DOCTYPE", r"<html", r"<head", r"<body"],
        "css": [r"\.css$", r"\.scss$", r"\.sass$", r"\.\w+\s*{", r"@media", r"@import"],
        "sql": [r"\.sql$", r"SELECT\s+", r"INSERT\s+INTO", r"CREATE\s+TABLE", r"ALTER\s+TABLE"],
        "shell": [r"\.sh$", r"\.bash$", r"^#!/bin/bash", r"^#!/bin/sh", r"echo\s+", r"export\s+"],
        "yaml": [r"\.ya?ml$", r"^\s*\w+:\s*$", r"^\s*-\s+\w+"],
        "json": [r"\.json$", r"^\s*{", r"^\s*\["],
        "markdown": [r"\.md$", r"^#\s+", r"^\*\*", r"```"],
        "dockerfile": [r"^Dockerfile$", r"^FROM\s+", r"^RUN\s+", r"^COPY\s+"],
        "toml": [r"\.toml$", r"^\[[\w\.]+\]$"],
        "xml": [r"\.xml$", r"<\?xml", r"<[\w:]+>"],
        "ruby": [r"\.rb$", r"def\s+\w+", r"class\s+\w+\s*<", r"require\s+['\"]"],
        "php": [r"\.php$", r"<\?php", r"function\s+\w+\(", r"\$\w+\s*="],
        "swift": [r"\.swift$", r"func\s+\w+\(", r"var\s+\w+:", r"let\s+\w+:"],
        "kotlin": [r"\.kt$", r"fun\s+\w+\(", r"val\s+\w+", r"var\s+\w+"],
    }
    
    # File path patterns in code comments
    FILE_PATH_PATTERNS = [
        r"(?:\/\/|#|<!--)\s*(?:file|path|location):\s*([^\s\n]+)",
        r"(?:\/\/|#)\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)$",
        r"File:\s*`?([^`\n]+)`?",
        r"Path:\s*`?([^`\n]+)`?",
        r"// src/[a-zA-Z0-9_/]+\.[a-z]+",
    ]
    
    # Chat format detection patterns
    CHAT_FORMAT_PATTERNS = {
        "ChatGPT": [r"ChatGPT", r"gpt-4", r"gpt-3\.5", r"OpenAI"],
        "Claude": [r"Claude", r"Anthropic", r"claude-"],
        "Gemini": [r"Gemini", r"Google AI", r"gemini-"],
        "Venice": [r"Venice", r"dolphin", r"venice\.ai"],
        "DeepSeek": [r"DeepSeek", r"deepseek-"],
        "Kimi": [r"Kimi", r"moonshot"],
    }
    
    def __init__(self, db_session=None):
        self.db_session = db_session
    
    async def parse_document(self, file_path: str, file_type: Optional[str] = None) -> ExtractedProject:
        """Parse a document and extract code blocks"""
        
        # Detect file type if not provided
        if not file_type:
            file_type = self._detect_file_type(file_path)
        
        # Read content based on file type
        content = await self._read_document(file_path, file_type)
        
        # Detect chat format
        source_format = self._detect_chat_format(content)
        
        # Extract code blocks
        code_blocks = self._extract_code_blocks(content)
        
        # Identify languages
        for block in code_blocks:
            if not block.language or block.language == "text":
                block.language = self._detect_language(block.content)
        
        # Extract file paths
        code_blocks = self._extract_file_paths(code_blocks, content)
        
        # Reconstruct project structure
        project = self._reconstruct_project(code_blocks)
        project.source_format = source_format
        project.languages_detected = list(set(b.language for b in code_blocks if b.language))
        
        # Generate README
        project.readme_content = self._generate_readme(project)
        
        return project
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect the file type from extension"""
        ext = Path(file_path).suffix.lower()
        type_map = {
            ".docx": "docx",
            ".doc": "docx",
            ".pdf": "pdf",
            ".txt": "txt",
            ".html": "html",
            ".htm": "html",
            ".md": "md",
            ".markdown": "md",
        }
        return type_map.get(ext, "txt")
    
    async def _read_document(self, file_path: str, file_type: str) -> str:
        """Read document content based on file type"""
        
        if file_type == "docx":
            return await self._read_docx(file_path)
        elif file_type == "pdf":
            return await self._read_pdf(file_path)
        elif file_type == "html":
            return await self._read_html(file_path)
        elif file_type == "md":
            return await self._read_markdown(file_path)
        else:  # txt or fallback
            return await self._read_text(file_path)
    
    async def _read_docx(self, file_path: str) -> str:
        """Read DOCX file content"""
        try:
            from docx import Document
            
            def read_sync():
                doc = Document(file_path)
                paragraphs = []
                for para in doc.paragraphs:
                    paragraphs.append(para.text)
                return "\n".join(paragraphs)
            
            return await asyncio.to_thread(read_sync)
        except ImportError:
            logger.warning("python-docx not installed, falling back to text extraction")
            return await self._read_text(file_path)
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            return ""
    
    async def _read_pdf(self, file_path: str) -> str:
        """Read PDF file content"""
        try:
            import PyPDF2
            
            def read_sync():
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = []
                    for page in reader.pages:
                        text.append(page.extract_text())
                    return "\n".join(text)
            
            return await asyncio.to_thread(read_sync)
        except ImportError:
            logger.warning("PyPDF2 not installed")
            return ""
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return ""
    
    async def _read_html(self, file_path: str) -> str:
        """Read HTML file content"""
        try:
            from bs4 import BeautifulSoup
            
            def read_sync():
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    soup = BeautifulSoup(file.read(), 'html.parser')
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    return soup.get_text(separator="\n")
            
            return await asyncio.to_thread(read_sync)
        except ImportError:
            logger.warning("BeautifulSoup not installed")
            return await self._read_text(file_path)
        except Exception as e:
            logger.error(f"Error reading HTML: {e}")
            return ""
    
    async def _read_markdown(self, file_path: str) -> str:
        """Read Markdown file content"""
        return await self._read_text(file_path)
    
    async def _read_text(self, file_path: str) -> str:
        """Read plain text file content"""
        try:
            async def read_async():
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    return file.read()
            return await asyncio.to_thread(lambda: open(file_path, 'r', encoding='utf-8', errors='ignore').read())
        except Exception as e:
            logger.error(f"Error reading text file: {e}")
            return ""
    
    def _detect_chat_format(self, content: str) -> Optional[str]:
        """Detect the AI chat format"""
        for format_name, patterns in self.CHAT_FORMAT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return format_name
        return None
    
    def _extract_code_blocks(self, content: str) -> List[CodeBlock]:
        """Extract code blocks from content"""
        code_blocks = []
        
        # Pattern for markdown-style code blocks
        markdown_pattern = r"```(\w*)\n(.*?)```"
        for match in re.finditer(markdown_pattern, content, re.DOTALL):
            language = match.group(1).lower() or "text"
            code = match.group(2).strip()
            if code:
                code_blocks.append(CodeBlock(
                    content=code,
                    language=language,
                    line_number=content[:match.start()].count('\n') + 1
                ))
        
        # Pattern for indented code blocks (4 spaces)
        lines = content.split('\n')
        current_block = []
        block_start = None
        
        for i, line in enumerate(lines):
            if line.startswith('    ') or line.startswith('\t'):
                if not current_block:
                    block_start = i + 1
                current_block.append(line.lstrip())
            else:
                if current_block and len(current_block) > 2:
                    code = '\n'.join(current_block)
                    # Check if this code is not already captured
                    if not any(code in b.content for b in code_blocks):
                        code_blocks.append(CodeBlock(
                            content=code,
                            language="text",
                            line_number=block_start
                        ))
                current_block = []
        
        return code_blocks
    
    def _detect_language(self, code: str) -> str:
        """Detect programming language from code content"""
        scores = {}
        
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, code, re.MULTILINE):
                    score += 1
            if score > 0:
                scores[language] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "text"
    
    def _extract_file_paths(self, code_blocks: List[CodeBlock], full_content: str) -> List[CodeBlock]:
        """Extract file paths from code blocks and surrounding context"""
        
        for block in code_blocks:
            # Check within the code block itself
            for pattern in self.FILE_PATH_PATTERNS:
                match = re.search(pattern, block.content, re.MULTILINE)
                if match:
                    block.file_path = match.group(1).strip()
                    break
            
            # If no path found, check surrounding context
            if not block.file_path and block.line_number:
                # Look at lines before the code block
                lines = full_content.split('\n')
                start_line = max(0, block.line_number - 5)
                context = '\n'.join(lines[start_line:block.line_number])
                
                for pattern in self.FILE_PATH_PATTERNS:
                    match = re.search(pattern, context, re.MULTILINE)
                    if match:
                        block.file_path = match.group(1).strip()
                        break
            
            # Generate file path from language if still not found
            if not block.file_path:
                block.file_path = self._generate_file_path(block)
        
        return code_blocks
    
    def _generate_file_path(self, block: CodeBlock) -> str:
        """Generate a file path based on language and content analysis"""
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "cpp": ".cpp",
            "c": ".c",
            "html": ".html",
            "css": ".css",
            "sql": ".sql",
            "shell": ".sh",
            "yaml": ".yml",
            "json": ".json",
            "markdown": ".md",
            "dockerfile": "Dockerfile",
            "toml": ".toml",
            "xml": ".xml",
            "ruby": ".rb",
            "php": ".php",
            "swift": ".swift",
            "kotlin": ".kt",
        }
        
        ext = ext_map.get(block.language, ".txt")
        
        # Try to extract a meaningful name from the code
        name = "code"
        
        # Check for class/function names
        class_match = re.search(r"class\s+(\w+)", block.content)
        func_match = re.search(r"(?:function|def|func)\s+(\w+)", block.content)
        
        if class_match:
            name = class_match.group(1).lower()
        elif func_match:
            name = func_match.group(1).lower()
        
        if ext == "Dockerfile":
            return ext
        
        return f"{name}{ext}"
    
    def _reconstruct_project(self, code_blocks: List[CodeBlock]) -> ExtractedProject:
        """Reconstruct project structure from code blocks"""
        project = ExtractedProject(code_blocks=code_blocks)
        
        # Group files by path
        file_contents = {}
        for block in code_blocks:
            if block.file_path:
                # Handle duplicate paths
                path = block.file_path
                if path in file_contents:
                    # Append to existing file or create numbered version
                    counter = 1
                    base, ext = os.path.splitext(path)
                    while path in file_contents:
                        path = f"{base}_{counter}{ext}"
                        counter += 1
                
                file_contents[path] = block.content
        
        project.files = file_contents
        return project
    
    def _generate_readme(self, project: ExtractedProject) -> str:
        """Generate a README.md for the extracted project"""
        
        readme = f"""# Extracted Project

Generated by CodeForge AI Chat Parser
Extraction Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview

This project was extracted from an AI chat transcript.

**Source Format:** {project.source_format or "Unknown"}
**Languages Detected:** {", ".join(project.languages_detected) or "None"}
**Total Files:** {len(project.files)}

## Project Structure

```
"""
        
        # Add file tree
        for path in sorted(project.files.keys()):
            readme += f"{path}\n"
        
        readme += """```

## Files

"""
        
        # Add file descriptions
        for path, content in sorted(project.files.items()):
            lines = len(content.split('\n'))
            readme += f"### `{path}`\n\n"
            readme += f"- **Lines:** {lines}\n"
            readme += f"- **Language:** {self._detect_language(content)}\n\n"
        
        readme += """
## Setup Instructions

1. Review the extracted files for completeness
2. Install required dependencies based on the detected languages
3. Configure any environment variables or settings
4. Run the application according to its type

## Troubleshooting

- If code blocks are incomplete, check the original chat transcript
- Some file paths may have been inferred; rename as needed
- Dependencies may need to be manually identified and installed

## Development Checklist

- [ ] Review extracted code for completeness
- [ ] Fix any syntax errors from extraction
- [ ] Add missing imports/dependencies
- [ ] Write tests
- [ ] Add proper error handling
- [ ] Document the code

## AI Prompts for Further Development

To continue development with AI assistance:

1. "Review this extracted code and identify any missing functions or incomplete implementations"
2. "Add proper error handling and logging to this code"
3. "Generate unit tests for the main functionality"
4. "Suggest improvements for code quality and performance"

---
*This README was auto-generated by CodeForge AI*
"""
        
        return readme
    
    async def create_project_zip(self, project: ExtractedProject, output_path: Optional[str] = None) -> str:
        """Create a ZIP file from the extracted project"""
        import zipfile
        
        if not output_path:
            output_path = tempfile.mktemp(suffix=".zip")
        
        def create_zip():
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add code files
                for path, content in project.files.items():
                    zipf.writestr(path, content)
                
                # Add README
                if project.readme_content:
                    zipf.writestr("README.md", project.readme_content)
            
            return output_path
        
        return await asyncio.to_thread(create_zip)
    
    async def save_extraction_to_db(self, filename: str, file_type: str, project: ExtractedProject) -> Dict[str, Any]:
        """Save extraction record to database"""
        if not self.db_session:
            return {"success": False, "error": "No database session"}
        
        try:
            from app.database.models import ChatExtraction
            
            extraction = ChatExtraction(
                filename=filename,
                file_type=file_type,
                source_format=project.source_format,
                extracted_files=project.files,
                project_structure=list(project.files.keys()),
                code_blocks_count=len(project.code_blocks),
                languages_detected=project.languages_detected,
                status="completed",
                completed_at=datetime.now()
            )
            
            self.db_session.add(extraction)
            await self.db_session.commit()
            await self.db_session.refresh(extraction)
            
            return {"success": True, "extraction_id": extraction.id}
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to save extraction: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_project_from_extraction(self, extraction_id: str, project_name: str) -> Dict[str, Any]:
        """Create a new project from an extraction"""
        if not self.db_session:
            return {"success": False, "error": "No database session"}
        
        try:
            from sqlalchemy import select
            from app.database.models import ChatExtraction, Project, File
            
            # Get extraction
            result = await self.db_session.execute(
                select(ChatExtraction).where(ChatExtraction.id == extraction_id)
            )
            extraction = result.scalar_one_or_none()
            
            if not extraction:
                return {"success": False, "error": "Extraction not found"}
            
            # Create project
            project = Project(
                name=project_name,
                description=f"Extracted from {extraction.filename}",
                framework=extraction.languages_detected[0] if extraction.languages_detected else None
            )
            
            self.db_session.add(project)
            await self.db_session.flush()
            
            # Create files
            for path, content in (extraction.extracted_files or {}).items():
                file = File(
                    project_id=project.id,
                    path=path,
                    content=content,
                    language=self._detect_language(content)
                )
                self.db_session.add(file)
            
            # Update extraction with project reference
            extraction.project_id = project.id
            
            await self.db_session.commit()
            
            return {"success": True, "project_id": project.id}
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}
