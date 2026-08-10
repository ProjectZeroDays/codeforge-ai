from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import json


class ProjectService:
    """
    Project Management Service
    Handles project creation, file management, and metadata
    """
    
    async def create_project(
        self,
        name: str,
        description: str,
        framework: Optional[str] = None,
        db = None
    ) -> Dict[str, Any]:
        """
        Create a new project
        """
        from app.database.models import Project
        
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            framework=framework,
            status="active"
        )
        
        if db:
            db.add(project)
            await db.commit()
            await db.refresh(project)
        
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "framework": project.framework,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        }
    
    async def get_all_projects(self, db) -> List[Dict[str, Any]]:
        """
        Get all projects
        """
        from app.database.models import Project
        from sqlalchemy import select
        
        result = await db.execute(select(Project).order_by(Project.created_at.desc()))
        projects = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "framework": p.framework,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "file_count": len(p.files) if hasattr(p, 'files') else 0
            }
            for p in projects
        ]
    
    async def get_project(self, project_id: str, db) -> Optional[Dict[str, Any]]:
        """
        Get project by ID
        """
        from app.database.models import Project
        from sqlalchemy import select
        
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "framework": project.framework,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        }
    
    async def get_project_files(self, project_id: str, db) -> List[Dict[str, Any]]:
        """
        Get all files in a project
        """
        from app.database.models import File
        from sqlalchemy import select
        
        result = await db.execute(
            select(File).where(File.project_id == project_id)
        )
        files = result.scalars().all()
        
        return [
            {
                "id": f.id,
                "path": f.path,
                "content": f.content,
                "language": f.language,
                "size": len(f.content) if f.content else 0,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat()
            }
            for f in files
        ]
    
    async def save_file(
        self,
        project_id: str,
        path: str,
        content: str,
        language: Optional[str] = None,
        db = None
    ) -> Dict[str, Any]:
        """
        Save or update a file
        """
        from app.database.models import File
        from sqlalchemy import select
        
        # Check if file exists
        result = await db.execute(
            select(File).where(
                File.project_id == project_id,
                File.path == path
            )
        )
        existing_file = result.scalar_one_or_none()
        
        if existing_file:
            # Update existing
            existing_file.content = content
            existing_file.language = language or self._detect_language(path)
            # Don't manually set updated_at - let SQLAlchemy handle it via onupdate
            file_obj = existing_file
        else:
            # Create new
            file_obj = File(
                id=str(uuid.uuid4()),
                project_id=project_id,
                path=path,
                content=content,
                language=language or self._detect_language(path)
            )
            db.add(file_obj)
        
        await db.commit()
        await db.refresh(file_obj)
        
        return {
            "id": file_obj.id,
            "path": file_obj.path,
            "content": file_obj.content,
            "language": file_obj.language,
            "created_at": file_obj.created_at.isoformat(),
            "updated_at": file_obj.updated_at.isoformat()
        }
    
    async def delete_file(self, project_id: str, file_id: str, db):
        """
        Delete a file
        """
        from app.database.models import File
        from sqlalchemy import select, delete
        
        await db.execute(
            delete(File).where(
                File.id == file_id,
                File.project_id == project_id
            )
        )
        await db.commit()
    
    async def save_generated_code(self, db, result: Dict[str, Any]):
        """
        Save AI-generated code to database
        """
        from app.database.models import GeneratedCode
        
        code_entry = GeneratedCode(
            id=str(uuid.uuid4()),
            raw_response=result.get('raw_response', ''),
            code_blocks=result.get('code_blocks', []),
            language=result.get('language'),
            timestamp=result.get('timestamp')
        )
        
        db.add(code_entry)
        await db.commit()
    
    def _detect_language(self, path: str) -> str:
        """
        Detect programming language from file extension
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'bash',
        }
        
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        
        return 'text'