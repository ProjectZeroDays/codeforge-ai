"""
Export/Import Service
Handles exporting projects and agents as ZIP/JSON and importing them back
"""

import os
import json
import asyncio
import logging
import tempfile
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid
from pathlib import Path
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting projects and agents"""
    
    EXPORT_VERSION = "1.0.0"
    
    async def export_project(
        self,
        db: AsyncSession,
        project_id: str,
        include_history: bool = False,
        include_metrics: bool = False,
        include_agents: bool = False
    ) -> BytesIO:
        """Export a project as a ZIP file"""
        from app.database.models import Project, File, Prompt
        
        # Get project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get files
        files_result = await db.execute(
            select(File).where(File.project_id == project_id)
        )
        files = files_result.scalars().all()
        
        # Create ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Create manifest
            manifest = {
                "export_version": self.EXPORT_VERSION,
                "export_type": "project",
                "exported_at": datetime.utcnow().isoformat(),
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "framework": project.framework,
                    "status": project.status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                },
                "files_count": len(files),
                "include_history": include_history,
                "include_metrics": include_metrics,
                "include_agents": include_agents
            }
            
            # Write manifest
            zf.writestr('.codeforge/manifest.json', json.dumps(manifest, indent=2))
            
            # Write project files
            for file in files:
                file_path = file.path.lstrip('/')
                zf.writestr(f"code/{file_path}", file.content or "")
                
                # Write file metadata
                file_meta = {
                    "id": file.id,
                    "path": file.path,
                    "language": file.language,
                    "created_at": file.created_at.isoformat() if file.created_at else None,
                    "updated_at": file.updated_at.isoformat() if file.updated_at else None
                }
                zf.writestr(f".codeforge/files/{file.id}.json", json.dumps(file_meta, indent=2))
            
            # Include history (prompts)
            if include_history:
                prompts_result = await db.execute(
                    select(Prompt).where(Prompt.project_id == project_id)
                )
                prompts = prompts_result.scalars().all()
                
                history = [
                    {
                        "id": p.id,
                        "prompt": p.prompt_text,
                        "response": p.response_text,
                        "model_used": p.model_used,
                        "tokens_used": p.tokens_used,
                        "created_at": p.created_at.isoformat() if p.created_at else None
                    }
                    for p in prompts
                ]
                zf.writestr('.codeforge/history.json', json.dumps(history, indent=2))
            
            # Include metrics
            if include_metrics:
                from app.database.models_extended import CodeQualityMetrics
                metrics_result = await db.execute(
                    select(CodeQualityMetrics)
                    .where(CodeQualityMetrics.project_id == project_id)
                    .order_by(CodeQualityMetrics.analyzed_at.desc())
                    .limit(1)
                )
                metrics = metrics_result.scalar_one_or_none()
                
                if metrics:
                    metrics_data = {
                        "total_files": metrics.total_files,
                        "total_lines": metrics.total_lines,
                        "language_breakdown": metrics.language_breakdown,
                        "overall_score": metrics.overall_score,
                        "grade": metrics.grade,
                        "analyzed_at": metrics.analyzed_at.isoformat() if metrics.analyzed_at else None
                    }
                    zf.writestr('.codeforge/metrics.json', json.dumps(metrics_data, indent=2))
            
            # Generate README
            readme = self._generate_export_readme(project, files, manifest)
            zf.writestr('README.md', readme)
        
        # Record export
        await self._record_export(db, "project", project_id, manifest)
        
        zip_buffer.seek(0)
        return zip_buffer
    
    async def export_agent(
        self,
        db: AsyncSession,
        agent_id: str,
        include_tasks: bool = True,
        include_activities: bool = True
    ) -> Dict:
        """Export an agent as JSON"""
        from app.database.models import AgentModel, TaskModel, AgentActivity
        
        # Get agent
        result = await db.execute(
            select(AgentModel).where(AgentModel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        export_data = {
            "export_version": self.EXPORT_VERSION,
            "export_type": "agent",
            "exported_at": datetime.utcnow().isoformat(),
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "capabilities": agent.capabilities,
                "system_prompt": agent.system_prompt,
                "parent_id": agent.parent_id,
                "status": agent.status,
                "created_at": agent.created_at.isoformat() if agent.created_at else None
            }
        }
        
        if include_tasks:
            tasks_result = await db.execute(
                select(TaskModel).where(TaskModel.agent_id == agent_id)
            )
            tasks = tasks_result.scalars().all()
            
            export_data["tasks"] = [
                {
                    "id": t.id,
                    "type": t.type,
                    "description": t.description,
                    "data": t.data,
                    "status": t.status,
                    "result": t.result,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in tasks
            ]
        
        if include_activities:
            activities_result = await db.execute(
                select(AgentActivity).where(AgentActivity.agent_id == agent_id)
            )
            activities = activities_result.scalars().all()
            
            export_data["activities"] = [
                {
                    "id": a.id,
                    "activity_type": a.activity_type,
                    "description": a.description,
                    "metadata": a.activity_data,  # Column renamed from 'metadata'
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None
                }
                for a in activities
            ]
        
        # Record export
        manifest = {
            "export_type": "agent",
            "agent_id": agent_id,
            "include_tasks": include_tasks,
            "include_activities": include_activities
        }
        await self._record_export(db, "agent", agent_id, manifest, is_agent=True)
        
        return export_data
    
    async def bulk_export(
        self,
        db: AsyncSession,
        project_ids: List[str] = None,
        agent_ids: List[str] = None
    ) -> BytesIO:
        """Bulk export multiple projects and agents"""
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "export_version": self.EXPORT_VERSION,
                "export_type": "bulk",
                "exported_at": datetime.utcnow().isoformat(),
                "projects": [],
                "agents": []
            }
            
            # Export projects
            if project_ids:
                for project_id in project_ids:
                    try:
                        project_zip = await self.export_project(db, project_id)
                        # Extract and add to bulk zip
                        with zipfile.ZipFile(project_zip, 'r') as pz:
                            for name in pz.namelist():
                                zf.writestr(f"projects/{project_id}/{name}", pz.read(name))
                        manifest["projects"].append(project_id)
                    except Exception as e:
                        logger.error(f"Failed to export project {project_id}: {e}")
            
            # Export agents
            if agent_ids:
                for agent_id in agent_ids:
                    try:
                        agent_data = await self.export_agent(db, agent_id)
                        zf.writestr(
                            f"agents/{agent_id}.json",
                            json.dumps(agent_data, indent=2)
                        )
                        manifest["agents"].append(agent_id)
                    except Exception as e:
                        logger.error(f"Failed to export agent {agent_id}: {e}")
            
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))
        
        zip_buffer.seek(0)
        return zip_buffer
    
    def _generate_export_readme(self, project, files, manifest) -> str:
        """Generate a README for the exported project"""
        return f"""# {project.name}

{project.description or 'Exported from CodeForge AI'}

## Export Information

- **Exported At**: {manifest['exported_at']}
- **Export Version**: {manifest['export_version']}
- **Files Count**: {manifest['files_count']}

## Project Structure

```
{self._generate_tree(files)}
```

## Import Instructions

To import this project back into CodeForge AI:

1. Go to the Import section
2. Upload this ZIP file
3. The project will be recreated with all files

## Files

| Path | Language |
|------|----------|
{chr(10).join(f"| {f.path} | {f.language or 'unknown'} |" for f in files)}

---

*Exported from CodeForge AI*
"""
    
    def _generate_tree(self, files) -> str:
        """Generate a file tree string"""
        if not files:
            return "(empty)"
        
        tree = []
        for f in sorted(files, key=lambda x: x.path):
            depth = f.path.count('/')
            indent = "  " * depth
            name = f.path.split('/')[-1]
            tree.append(f"{indent}├── {name}")
        
        return "\n".join(tree)
    
    async def _record_export(
        self,
        db: AsyncSession,
        export_type: str,
        item_id: str,
        manifest: Dict,
        is_agent: bool = False
    ):
        """Record an export in the database"""
        from app.database.models_extended import ExportRecord
        
        record = ExportRecord(
            export_type=export_type,
            project_id=item_id if not is_agent else None,
            agent_id=item_id if is_agent else None,
            format="zip" if export_type == "project" else "json",
            filename=f"{export_type}_{item_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            manifest=manifest,
            status="ready",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        db.add(record)
        await db.commit()


class ImportService:
    """Service for importing projects and agents"""
    
    SUPPORTED_VERSIONS = ["1.0.0"]
    
    async def import_project(
        self,
        db: AsyncSession,
        zip_file: BytesIO,
        new_name: Optional[str] = None
    ) -> Dict:
        """Import a project from a ZIP file"""
        from app.database.models import Project, File
        
        validation = await self.validate_import(zip_file, "project")
        if not validation["valid"]:
            raise ValueError(f"Invalid import file: {validation['errors']}")
        
        with zipfile.ZipFile(zip_file, 'r') as zf:
            # Read manifest
            manifest = json.loads(zf.read('.codeforge/manifest.json'))
            
            project_data = manifest["project"]
            
            # Create new project
            project = Project(
                name=new_name or project_data["name"],
                description=project_data.get("description"),
                framework=project_data.get("framework"),
                status="active"
            )
            
            db.add(project)
            await db.flush()
            
            # Import files
            created_files = []
            for name in zf.namelist():
                if name.startswith("code/") and not name.endswith("/"):
                    path = name[5:]  # Remove 'code/' prefix
                    content = zf.read(name).decode('utf-8', errors='replace')
                    
                    file = File(
                        project_id=project.id,
                        path=path,
                        content=content,
                        language=self._detect_language(path)
                    )
                    db.add(file)
                    created_files.append(path)
            
            await db.commit()
            
            # Record import
            await self._record_import(db, "project", project.id, manifest)
            
            return {
                "project_id": project.id,
                "name": project.name,
                "files_imported": len(created_files),
                "message": "Project imported successfully"
            }
    
    async def import_agent(
        self,
        db: AsyncSession,
        agent_json: Dict
    ) -> Dict:
        """Import an agent from JSON data"""
        from app.database.models import AgentModel, TaskModel
        
        # Validate
        if agent_json.get("export_type") != "agent":
            raise ValueError("Invalid agent export format")
        
        if agent_json.get("export_version") not in self.SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported export version: {agent_json.get('export_version')}")
        
        agent_data = agent_json["agent"]
        
        # Generate new ID
        new_id = str(uuid.uuid4())
        
        # Create agent
        agent = AgentModel(
            id=new_id,
            name=agent_data["name"],
            role=agent_data["role"],
            capabilities=agent_data.get("capabilities"),
            system_prompt=agent_data.get("system_prompt"),
            status="active"
        )
        
        db.add(agent)
        await db.commit()
        
        # Record import
        await self._record_import(db, "agent", new_id, agent_json)
        
        return {
            "agent_id": new_id,
            "name": agent.name,
            "role": agent.role,
            "message": "Agent imported successfully"
        }
    
    async def bulk_import(
        self,
        db: AsyncSession,
        zip_file: BytesIO
    ) -> Dict:
        """Import multiple projects and agents from a bulk export"""
        results = {
            "projects": [],
            "agents": [],
            "errors": []
        }
        
        with zipfile.ZipFile(zip_file, 'r') as zf:
            manifest = json.loads(zf.read('manifest.json'))
            
            # Import projects
            for project_id in manifest.get("projects", []):
                try:
                    # Extract project to temporary buffer
                    project_buffer = BytesIO()
                    with zipfile.ZipFile(project_buffer, 'w') as pz:
                        prefix = f"projects/{project_id}/"
                        for name in zf.namelist():
                            if name.startswith(prefix):
                                pz.writestr(
                                    name[len(prefix):],
                                    zf.read(name)
                                )
                    project_buffer.seek(0)
                    
                    result = await self.import_project(db, project_buffer)
                    results["projects"].append(result)
                except Exception as e:
                    results["errors"].append({
                        "type": "project",
                        "original_id": project_id,
                        "error": str(e)
                    })
            
            # Import agents
            for agent_id in manifest.get("agents", []):
                try:
                    agent_data = json.loads(zf.read(f"agents/{agent_id}.json"))
                    result = await self.import_agent(db, agent_data)
                    results["agents"].append(result)
                except Exception as e:
                    results["errors"].append({
                        "type": "agent",
                        "original_id": agent_id,
                        "error": str(e)
                    })
        
        return results
    
    async def validate_import(
        self,
        file: BytesIO,
        import_type: str
    ) -> Dict:
        """Validate an import file"""
        errors = []
        warnings = []
        
        try:
            if import_type == "project":
                with zipfile.ZipFile(file, 'r') as zf:
                    # Check for manifest
                    if '.codeforge/manifest.json' not in zf.namelist():
                        errors.append("Missing manifest file")
                    else:
                        manifest = json.loads(zf.read('.codeforge/manifest.json'))
                        
                        # Version check
                        if manifest.get("export_version") not in self.SUPPORTED_VERSIONS:
                            errors.append(f"Unsupported version: {manifest.get('export_version')}")
                        
                        # Check for code files
                        code_files = [n for n in zf.namelist() if n.startswith("code/")]
                        if not code_files:
                            warnings.append("No code files found in export")
                
                file.seek(0)  # Reset for later use
                
            elif import_type == "agent":
                # For JSON imports
                pass
                
        except zipfile.BadZipFile:
            errors.append("Invalid ZIP file")
        except json.JSONDecodeError:
            errors.append("Invalid JSON in manifest")
        except Exception as e:
            errors.append(str(e))
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _detect_language(self, path: str) -> str:
        """Detect language from file extension"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".css": "css",
            ".html": "html",
            ".sql": "sql",
            ".sh": "bash",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php"
        }
        _, ext = os.path.splitext(path.lower())
        return ext_map.get(ext, "text")
    
    async def _record_import(
        self,
        db: AsyncSession,
        import_type: str,
        item_id: str,
        data: Dict
    ):
        """Record an import in the database"""
        from app.database.models_extended import ImportRecord
        
        record = ImportRecord(
            import_type=import_type,
            source_filename=f"import_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            source_format="zip" if import_type == "project" else "json",
            created_project_id=item_id if import_type == "project" else None,
            created_agent_id=item_id if import_type == "agent" else None,
            validation_passed=True,
            status="completed",
            import_summary=data
        )
        
        db.add(record)
        await db.commit()
