"""
Agent Collaboration Service
Enables agents to communicate, share context, and collaborate on tasks
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

logger = logging.getLogger(__name__)


class AgentCollaborationService:
    """Service for agent-to-agent collaboration"""
    
    def __init__(self, websocket_manager=None, ai_service=None):
        self.ws_manager = websocket_manager
        self.ai_service = ai_service
    
    # ==========================================
    # Agent Messaging
    # ==========================================
    
    async def send_message(
        self,
        db: AsyncSession,
        from_agent_id: str,
        to_agent_id: str,
        message_type: str,
        content: str,
        subject: Optional[str] = None,
        metadata: Optional[Dict] = None,
        priority: str = "normal",
        requires_response: bool = False,
        thread_id: Optional[str] = None
    ) -> Dict:
        """Send a message from one agent to another"""
        from app.database.models_extended import AgentMessage
        
        message = AgentMessage(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            message_type=message_type,
            subject=subject,
            content=content,
            message_data=metadata,  # Column renamed from 'metadata'
            thread_id=thread_id or str(uuid.uuid4()),
            priority=priority,
            requires_response=requires_response,
            status="sent"
        )
        
        db.add(message)
        await db.commit()
        
        # Notify via WebSocket
        if self.ws_manager:
            await self.ws_manager.publish_to_topic(
                f"agent:{to_agent_id}:messages",
                {
                    "type": "new_message",
                    "message_id": message.id,
                    "from_agent": from_agent_id,
                    "message_type": message_type,
                    "subject": subject,
                    "priority": priority
                }
            )
        
        return {
            "message_id": message.id,
            "thread_id": message.thread_id,
            "status": "sent"
        }
    
    async def get_messages(
        self,
        db: AsyncSession,
        agent_id: str,
        direction: str = "received",  # "received", "sent", "all"
        message_type: Optional[str] = None,
        status: Optional[str] = None,
        thread_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get messages for an agent"""
        from app.database.models_extended import AgentMessage
        
        query = select(AgentMessage)
        
        if direction == "received":
            query = query.where(AgentMessage.to_agent_id == agent_id)
        elif direction == "sent":
            query = query.where(AgentMessage.from_agent_id == agent_id)
        else:
            query = query.where(
                or_(
                    AgentMessage.to_agent_id == agent_id,
                    AgentMessage.from_agent_id == agent_id
                )
            )
        
        if message_type:
            query = query.where(AgentMessage.message_type == message_type)
        if status:
            query = query.where(AgentMessage.status == status)
        if thread_id:
            query = query.where(AgentMessage.thread_id == thread_id)
        
        query = query.order_by(AgentMessage.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        return [
            {
                "id": m.id,
                "from_agent_id": m.from_agent_id,
                "to_agent_id": m.to_agent_id,
                "message_type": m.message_type,
                "subject": m.subject,
                "content": m.content,
                "metadata": m.message_data,  # Column renamed from 'metadata'
                "thread_id": m.thread_id,
                "status": m.status,
                "priority": m.priority,
                "requires_response": m.requires_response,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]
    
    async def reply_to_message(
        self,
        db: AsyncSession,
        original_message_id: str,
        from_agent_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Reply to a message"""
        from app.database.models_extended import AgentMessage
        
        # Get original message
        result = await db.execute(
            select(AgentMessage).where(AgentMessage.id == original_message_id)
        )
        original = result.scalar_one_or_none()
        
        if not original:
            raise ValueError(f"Message {original_message_id} not found")
        
        # Create reply
        reply = AgentMessage(
            from_agent_id=from_agent_id,
            to_agent_id=original.from_agent_id,
            message_type="response",
            subject=f"Re: {original.subject}" if original.subject else None,
            content=content,
            metadata=metadata,
            thread_id=original.thread_id,
            parent_message_id=original_message_id,
            status="sent"
        )
        
        db.add(reply)
        
        # Update original message
        original.response_id = reply.id
        original.responded_at = datetime.utcnow()
        original.status = "processed"
        
        await db.commit()
        
        return {
            "message_id": reply.id,
            "thread_id": reply.thread_id,
            "status": "sent"
        }
    
    async def mark_message_read(
        self,
        db: AsyncSession,
        message_id: str
    ):
        """Mark a message as read"""
        from app.database.models_extended import AgentMessage
        
        await db.execute(
            update(AgentMessage)
            .where(AgentMessage.id == message_id)
            .values(status="read")
        )
        await db.commit()
    
    # ==========================================
    # Shared Context
    # ==========================================
    
    async def create_shared_context(
        self,
        db: AsyncSession,
        name: str,
        context_type: str,
        data: Dict,
        creator_agent_id: str,
        project_id: Optional[str] = None,
        participating_agents: Optional[List[str]] = None,
        description: Optional[str] = None,
        expires_in_hours: Optional[int] = None
    ) -> Dict:
        """Create a shared context that agents can access"""
        from app.database.models_extended import SharedContext
        
        context = SharedContext(
            name=name,
            description=description,
            context_type=context_type,
            data=data,
            project_id=project_id,
            scope="project" if project_id else "global",
            participating_agents=participating_agents or [],
            creator_agent_id=creator_agent_id,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours) if expires_in_hours else None,
            is_active=True
        )
        
        db.add(context)
        await db.commit()
        
        return {
            "context_id": context.id,
            "name": name,
            "context_type": context_type,
            "message": "Shared context created"
        }
    
    async def get_shared_context(
        self,
        db: AsyncSession,
        context_id: str
    ) -> Optional[Dict]:
        """Get a shared context by ID"""
        from app.database.models_extended import SharedContext
        
        result = await db.execute(
            select(SharedContext).where(
                SharedContext.id == context_id,
                SharedContext.is_active == True
            )
        )
        context = result.scalar_one_or_none()
        
        if not context:
            return None
        
        # Check expiry
        if context.expires_at and context.expires_at < datetime.utcnow():
            return None
        
        return {
            "id": context.id,
            "name": context.name,
            "description": context.description,
            "context_type": context.context_type,
            "data": context.data,
            "project_id": context.project_id,
            "scope": context.scope,
            "participating_agents": context.participating_agents,
            "creator_agent_id": context.creator_agent_id,
            "version": context.version,
            "created_at": context.created_at.isoformat() if context.created_at else None
        }
    
    async def update_shared_context(
        self,
        db: AsyncSession,
        context_id: str,
        data: Dict,
        merge: bool = True
    ) -> Dict:
        """Update a shared context"""
        from app.database.models_extended import SharedContext
        
        result = await db.execute(
            select(SharedContext).where(SharedContext.id == context_id)
        )
        context = result.scalar_one_or_none()
        
        if not context:
            raise ValueError(f"Context {context_id} not found")
        
        if merge:
            # Merge new data with existing
            existing_data = context.data or {}
            existing_data.update(data)
            context.data = existing_data
        else:
            context.data = data
        
        context.version += 1
        context.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Notify participating agents
        if self.ws_manager and context.participating_agents:
            for agent_id in context.participating_agents:
                await self.ws_manager.publish_to_topic(
                    f"agent:{agent_id}:context",
                    {
                        "type": "context_updated",
                        "context_id": context_id,
                        "version": context.version
                    }
                )
        
        return {
            "context_id": context_id,
            "version": context.version,
            "message": "Context updated"
        }
    
    async def list_shared_contexts(
        self,
        db: AsyncSession,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        context_type: Optional[str] = None
    ) -> List[Dict]:
        """List available shared contexts"""
        from app.database.models_extended import SharedContext
        
        query = select(SharedContext).where(SharedContext.is_active == True)
        
        if project_id:
            query = query.where(SharedContext.project_id == project_id)
        if context_type:
            query = query.where(SharedContext.context_type == context_type)
        
        result = await db.execute(query)
        contexts = result.scalars().all()
        
        # Filter by agent access if specified
        if agent_id:
            contexts = [
                c for c in contexts
                if not c.participating_agents or agent_id in c.participating_agents
            ]
        
        return [
            {
                "id": c.id,
                "name": c.name,
                "context_type": c.context_type,
                "project_id": c.project_id,
                "version": c.version,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in contexts
        ]
    
    # ==========================================
    # Task Delegation
    # ==========================================
    
    async def delegate_task(
        self,
        db: AsyncSession,
        parent_agent_id: str,
        child_agent_id: str,
        task_description: str,
        delegation_type: str = "full",  # full, partial, assistance
        original_task_id: Optional[str] = None,
        instructions: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict:
        """Delegate a task from one agent to another"""
        from app.database.models import TaskModel
        from app.database.models_extended import TaskDelegation
        
        # Create the delegated task
        delegated_task = TaskModel(
            id=str(uuid.uuid4()),
            agent_id=child_agent_id,
            type="delegated",
            description=task_description,
            data={
                "delegated_from": parent_agent_id,
                "delegation_type": delegation_type,
                "instructions": instructions
            },
            status="pending"
        )
        
        db.add(delegated_task)
        await db.flush()
        
        # Create delegation record
        delegation = TaskDelegation(
            parent_agent_id=parent_agent_id,
            child_agent_id=child_agent_id,
            original_task_id=original_task_id,
            delegated_task_id=delegated_task.id,
            delegation_type=delegation_type,
            reason=reason,
            instructions=instructions,
            status="pending"
        )
        
        db.add(delegation)
        await db.commit()
        
        # Notify child agent
        await self.send_message(
            db,
            from_agent_id=parent_agent_id,
            to_agent_id=child_agent_id,
            message_type="task_delegation",
            subject=f"Task delegated: {task_description[:50]}",
            content=task_description,
            metadata={
                "delegation_id": delegation.id,
                "task_id": delegated_task.id,
                "delegation_type": delegation_type
            },
            priority="high",
            requires_response=True
        )
        
        return {
            "delegation_id": delegation.id,
            "task_id": delegated_task.id,
            "status": "pending"
        }
    
    async def accept_delegation(
        self,
        db: AsyncSession,
        delegation_id: str,
        accepted: bool,
        reason: Optional[str] = None
    ) -> Dict:
        """Accept or reject a task delegation"""
        from app.database.models_extended import TaskDelegation
        
        result = await db.execute(
            select(TaskDelegation).where(TaskDelegation.id == delegation_id)
        )
        delegation = result.scalar_one_or_none()
        
        if not delegation:
            raise ValueError(f"Delegation {delegation_id} not found")
        
        delegation.accepted = accepted
        delegation.acceptance_reason = reason
        delegation.status = "accepted" if accepted else "rejected"
        
        await db.commit()
        
        # Notify parent agent
        await self.send_message(
            db,
            from_agent_id=delegation.child_agent_id,
            to_agent_id=delegation.parent_agent_id,
            message_type="delegation_response",
            subject=f"Task delegation {'accepted' if accepted else 'rejected'}",
            content=reason or ("Task accepted" if accepted else "Task rejected"),
            metadata={"delegation_id": delegation_id}
        )
        
        return {
            "delegation_id": delegation_id,
            "accepted": accepted,
            "status": delegation.status
        }
    
    async def update_delegation_progress(
        self,
        db: AsyncSession,
        delegation_id: str,
        progress: int,
        status_update: Optional[str] = None
    ):
        """Update progress on a delegated task"""
        from app.database.models_extended import TaskDelegation
        
        result = await db.execute(
            select(TaskDelegation).where(TaskDelegation.id == delegation_id)
        )
        delegation = result.scalar_one_or_none()
        
        if not delegation:
            raise ValueError(f"Delegation {delegation_id} not found")
        
        delegation.progress_percentage = min(100, max(0, progress))
        if progress >= 100:
            delegation.status = "completed"
            delegation.completed_at = datetime.utcnow()
        else:
            delegation.status = "in_progress"
        
        await db.commit()
        
        # Notify parent of progress
        if self.ws_manager:
            await self.ws_manager.publish_to_topic(
                f"agent:{delegation.parent_agent_id}:delegations",
                {
                    "type": "progress_update",
                    "delegation_id": delegation_id,
                    "progress": progress,
                    "status": delegation.status
                }
            )
    
    async def complete_delegation(
        self,
        db: AsyncSession,
        delegation_id: str,
        result_summary: str,
        artifacts: Optional[List[Dict]] = None
    ) -> Dict:
        """Complete a delegated task"""
        from app.database.models_extended import TaskDelegation
        
        result = await db.execute(
            select(TaskDelegation).where(TaskDelegation.id == delegation_id)
        )
        delegation = result.scalar_one_or_none()
        
        if not delegation:
            raise ValueError(f"Delegation {delegation_id} not found")
        
        delegation.status = "completed"
        delegation.progress_percentage = 100
        delegation.completed_at = datetime.utcnow()
        delegation.result_summary = result_summary
        delegation.artifacts = artifacts
        
        await db.commit()
        
        # Notify parent agent
        await self.send_message(
            db,
            from_agent_id=delegation.child_agent_id,
            to_agent_id=delegation.parent_agent_id,
            message_type="delegation_complete",
            subject="Delegated task completed",
            content=result_summary,
            metadata={
                "delegation_id": delegation_id,
                "artifacts": artifacts
            },
            priority="high"
        )
        
        return {
            "delegation_id": delegation_id,
            "status": "completed"
        }
    
    # ==========================================
    # Code Review
    # ==========================================
    
    async def request_code_review(
        self,
        db: AsyncSession,
        author_agent_id: str,
        reviewer_agent_id: str,
        project_id: str,
        files: List[Dict],  # [{path, content, diff}]
        context: Optional[str] = None,
        focus_areas: Optional[List[str]] = None,
        urgency: str = "normal"
    ) -> Dict:
        """Request a code review from another agent"""
        from app.database.models_extended import CodeReviewRequest
        
        review = CodeReviewRequest(
            author_agent_id=author_agent_id,
            reviewer_agent_id=reviewer_agent_id,
            project_id=project_id,
            files=files,
            context=context,
            focus_areas=focus_areas or ["correctness", "security", "performance"],
            urgency=urgency,
            status="pending"
        )
        
        db.add(review)
        await db.commit()
        
        # Notify reviewer
        await self.send_message(
            db,
            from_agent_id=author_agent_id,
            to_agent_id=reviewer_agent_id,
            message_type="code_review",
            subject=f"Code review requested for {len(files)} file(s)",
            content=context or "Please review the attached code changes",
            metadata={
                "review_id": review.id,
                "file_count": len(files),
                "focus_areas": focus_areas
            },
            priority="high" if urgency == "high" else "normal",
            requires_response=True
        )
        
        return {
            "review_id": review.id,
            "status": "pending"
        }
    
    async def submit_review(
        self,
        db: AsyncSession,
        review_id: str,
        approval_status: str,  # approved, changes_requested, needs_discussion
        overall_feedback: str,
        comments: Optional[List[Dict]] = None,  # [{file, line, comment, severity}]
        suggested_changes: Optional[List[Dict]] = None
    ) -> Dict:
        """Submit a code review"""
        from app.database.models_extended import CodeReviewRequest
        
        result = await db.execute(
            select(CodeReviewRequest).where(CodeReviewRequest.id == review_id)
        )
        review = result.scalar_one_or_none()
        
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        review.status = "completed"
        review.approval_status = approval_status
        review.overall_feedback = overall_feedback
        review.review_comments = comments
        review.suggested_changes = suggested_changes
        review.reviewed_at = datetime.utcnow()
        
        await db.commit()
        
        # Notify author
        await self.send_message(
            db,
            from_agent_id=review.reviewer_agent_id,
            to_agent_id=review.author_agent_id,
            message_type="review_complete",
            subject=f"Code review: {approval_status}",
            content=overall_feedback,
            metadata={
                "review_id": review_id,
                "approval_status": approval_status,
                "comments_count": len(comments) if comments else 0
            },
            priority="high" if approval_status == "changes_requested" else "normal"
        )
        
        return {
            "review_id": review_id,
            "approval_status": approval_status,
            "status": "completed"
        }
    
    async def ai_assisted_review(
        self,
        db: AsyncSession,
        review_id: str
    ) -> Dict:
        """Use AI to assist with code review"""
        from app.database.models_extended import CodeReviewRequest
        
        result = await db.execute(
            select(CodeReviewRequest).where(CodeReviewRequest.id == review_id)
        )
        review = result.scalar_one_or_none()
        
        if not review or not self.ai_service:
            return {"error": "Review not found or AI service unavailable"}
        
        # Build prompt for AI review
        files_content = "\n\n".join([
            f"### File: {f['path']}\n```\n{f.get('content', f.get('diff', ''))}\n```"
            for f in review.files
        ])
        
        prompt = f"""Review the following code changes:

Context: {review.context or 'General code changes'}
Focus areas: {', '.join(review.focus_areas or [])}

{files_content}

Provide:
1. Overall assessment
2. Specific issues (with file and line if applicable)
3. Suggestions for improvement
4. Security concerns
5. Performance considerations

Format your response as JSON with structure:
{{
    "overall_assessment": "string",
    "approval_recommendation": "approved|changes_requested|needs_discussion",
    "issues": [{{"file": "path", "line": number, "severity": "error|warning|info", "message": "string"}}],
    "suggestions": ["string"],
    "security_concerns": ["string"],
    "performance_notes": ["string"]
}}"""

        try:
            response = await self.ai_service.generate_code(prompt)
            
            # Parse AI response
            import json
            ai_review = json.loads(response)
            
            return {
                "review_id": review_id,
                "ai_review": ai_review
            }
        except Exception as e:
            logger.error(f"AI review failed: {e}")
            return {"error": str(e)}
    
    # ==========================================
    # Collaboration Graph
    # ==========================================
    
    async def get_collaboration_graph(
        self,
        db: AsyncSession,
        project_id: Optional[str] = None,
        agent_ids: Optional[List[str]] = None
    ) -> Dict:
        """Get the collaboration graph showing agent relationships"""
        from app.database.models import AgentModel
        from app.database.models_extended import AgentMessage, TaskDelegation
        
        # Get agents
        agents_query = select(AgentModel)
        if agent_ids:
            agents_query = agents_query.where(AgentModel.id.in_(agent_ids))
        
        result = await db.execute(agents_query)
        agents = result.scalars().all()
        
        # Build nodes
        nodes = [
            {
                "id": a.id,
                "name": a.name,
                "role": a.role,
                "status": a.status
            }
            for a in agents
        ]
        
        agent_id_set = set(a.id for a in agents)
        
        # Build edges from messages
        edges = []
        message_counts = {}
        
        messages_result = await db.execute(
            select(AgentMessage)
        )
        messages = messages_result.scalars().all()
        
        for msg in messages:
            if msg.from_agent_id in agent_id_set and msg.to_agent_id in agent_id_set:
                key = (msg.from_agent_id, msg.to_agent_id)
                message_counts[key] = message_counts.get(key, 0) + 1
        
        for (from_id, to_id), count in message_counts.items():
            edges.append({
                "source": from_id,
                "target": to_id,
                "type": "message",
                "weight": count
            })
        
        # Add delegation edges
        delegations_result = await db.execute(select(TaskDelegation))
        delegations = delegations_result.scalars().all()
        
        for delegation in delegations:
            if delegation.parent_agent_id in agent_id_set and delegation.child_agent_id in agent_id_set:
                edges.append({
                    "source": delegation.parent_agent_id,
                    "target": delegation.child_agent_id,
                    "type": "delegation",
                    "status": delegation.status
                })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_agents": len(nodes),
                "total_connections": len(edges),
                "active_delegations": sum(1 for e in edges if e["type"] == "delegation" and e.get("status") == "in_progress")
            }
        }
