import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class Agent:
    """Represents an AI agent with specific capabilities"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: List[str],
        system_prompt: str,
        parent_id: Optional[str] = None
    ):
        self.id = agent_id
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.system_prompt = system_prompt
        self.parent_id = parent_id
        self.children: List[str] = []
        self.status = "active"
        self.created_at = datetime.now()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.current_task: Optional[Dict[str, Any]] = None
        self.task_history: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "parent_id": self.parent_id,
            "children": self.children,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "current_task": self.current_task,
            "tasks_completed": len(self.task_history)
        }


class AgentOrchestrator:
    """
    Multi-Agent Orchestration System
    Manages creation, coordination, and task distribution among AI agents
    """
    
    def __init__(self, venice_service, ws_manager):
        self.venice_service = venice_service
        self.ws_manager = ws_manager
        self.agents: Dict[str, Agent] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}
    
    async def create_agent(
        self,
        name: str,
        role: str,
        capabilities: List[str],
        system_prompt: str,
        parent_id: Optional[str] = None,
        db = None
    ) -> Dict[str, Any]:
        """
        Create a new AI agent
        """
        agent_id = str(uuid.uuid4())
        
        agent = Agent(
            agent_id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities,
            system_prompt=system_prompt,
            parent_id=parent_id
        )
        
        self.agents[agent_id] = agent
        
        # If has parent, register as child
        if parent_id and parent_id in self.agents:
            self.agents[parent_id].children.append(agent_id)
        
        # Store in database
        if db:
            await self._save_agent_to_db(agent, db)
        
        # Start agent event loop
        task = asyncio.create_task(self._agent_event_loop(agent_id))
        self.agent_tasks[agent_id] = task
        
        # Broadcast creation
        await self.ws_manager.broadcast({
            "type": "agent_created",
            "agent": agent.to_dict()
        })
        
        return agent.to_dict()
    
    async def spawn_child_agent(
        self,
        parent_id: str,
        name: str,
        role: str,
        capabilities: List[str],
        reason: str,
        db = None
    ) -> Dict[str, Any]:
        """
        Spawn a child agent from a parent for specialized tasks
        """
        parent = self.agents.get(parent_id)
        if not parent:
            raise ValueError(f"Parent agent {parent_id} not found")
        
        # Build specialized system prompt
        system_prompt = f"""You are a specialized agent created by {parent.name}.

Your role: {role}
Your capabilities: {', '.join(capabilities)}
Spawn reason: {reason}

You should focus on your specific role and report back to your parent agent when tasks are complete."""
        
        child = await self.create_agent(
            name=f"{parent.name}-{role}",
            role=role,
            capabilities=capabilities,
            system_prompt=system_prompt,
            parent_id=parent_id,
            db=db
        )
        
        print(f"🌱 Agent {parent.name} spawned child: {child['name']} for {reason}")
        
        return child
    
    async def assign_task(
        self,
        agent_id: str,
        task: Dict[str, Any],
        db = None
    ) -> Dict[str, Any]:
        """
        Assign a task to an agent
        """
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        task_data = {
            "id": str(uuid.uuid4()),
            "type": task.get('type', 'general'),
            "description": task.get('description', ''),
            "data": task.get('data', {}),
            "assigned_at": datetime.now().isoformat(),
            "status": "queued"
        }
        
        await agent.task_queue.put(task_data)
        
        # Save to database
        if db:
            await self._save_task_to_db(agent_id, task_data, db)
        
        return task_data
    
    async def _agent_event_loop(self, agent_id: str):
        """
        Main event loop for an agent - processes tasks from queue
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return
        
        print(f"🤖 Agent {agent.name} event loop started")
        
        while agent.status == "active":
            try:
                # Get next task with timeout
                task = await asyncio.wait_for(
                    agent.task_queue.get(),
                    timeout=60.0  # Check status every minute
                )
                
                agent.current_task = task
                task['status'] = 'in_progress'
                
                # Broadcast task start
                await self.ws_manager.broadcast({
                    "type": "agent_task_started",
                    "agent_id": agent_id,
                    "task": task
                })
                
                # Process task based on type
                result = await self._process_task(agent, task)
                
                # Update task
                task['status'] = 'completed'
                task['result'] = result
                task['completed_at'] = datetime.now().isoformat()
                
                agent.task_history.append(task)
                agent.current_task = None
                
                # Broadcast completion
                await self.ws_manager.broadcast({
                    "type": "agent_task_completed",
                    "agent_id": agent_id,
                    "task": task
                })
                
            except asyncio.TimeoutError:
                # No tasks, continue waiting
                continue
            except Exception as e:
                print(f"❌ Error in agent {agent.name} event loop: {e}")
                if agent.current_task:
                    agent.current_task['status'] = 'failed'
                    agent.current_task['error'] = str(e)
                    agent.task_history.append(agent.current_task)
                    agent.current_task = None
    
    async def _process_task(self, agent: Agent, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task using Venice AI
        """
        # Build messages for AI
        messages = [
            {
                "role": "user",
                "content": f"Task Type: {task['type']}\n\nDescription: {task['description']}\n\nData: {json.dumps(task.get('data', {}), indent=2)}"
            }
        ]
        
        # Check if task requires child agent
        if task.get('requires_specialization'):
            # Spawn child agent for this task
            child = await self.spawn_child_agent(
                parent_id=agent.id,
                name=f"Specialist-{task['type']}",
                role=task['type'],
                capabilities=[task['type']],
                reason=f"Specialized task: {task['type']}",
                db=None
            )
            
            # Delegate to child
            return await self.assign_task(child['id'], task, db=None)
        
        # Process with Venice AI
        full_response = ""
        async for chunk in self.venice_service.stream_chat(
            messages=messages,
            system_prompt=agent.system_prompt,
            temperature=0.7
        ):
            if chunk['type'] == 'content':
                full_response += chunk['content']
                
                # Stream progress to websocket
                await self.ws_manager.broadcast({
                    "type": "agent_progress",
                    "agent_id": agent.id,
                    "task_id": task['id'],
                    "content": chunk['content']
                })
        
        return {
            "response": full_response,
            "timestamp": datetime.now().isoformat()
        }
    
    async def terminate_agent(self, agent_id: str, db = None):
        """
        Terminate an agent and its children
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return
        
        # Terminate children first
        for child_id in agent.children:
            await self.terminate_agent(child_id, db)
        
        # Cancel event loop
        if agent_id in self.agent_tasks:
            self.agent_tasks[agent_id].cancel()
            del self.agent_tasks[agent_id]
        
        # Update status
        agent.status = "terminated"
        
        # Broadcast termination
        await self.ws_manager.broadcast({
            "type": "agent_terminated",
            "agent_id": agent_id
        })
        
        print(f"🛑 Agent {agent.name} terminated")
    
    async def get_all_agents(self, db = None) -> List[Dict[str, Any]]:
        """
        Get all active agents
        """
        return [agent.to_dict() for agent in self.agents.values()]
    
    async def get_agent(self, agent_id: str, db = None) -> Optional[Dict[str, Any]]:
        """
        Get specific agent details
        """
        agent = self.agents.get(agent_id)
        return agent.to_dict() if agent else None
    
    async def get_agent_activity(self, agent_id: str, db = None) -> List[Dict[str, Any]]:
        """
        Get agent activity history
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return []
        
        return agent.task_history
    
    def get_active_agent_count(self) -> int:
        """
        Get count of active agents
        """
        return len([a for a in self.agents.values() if a.status == "active"])
    
    async def shutdown_all_agents(self):
        """
        Shutdown all agents
        """
        for agent_id in list(self.agents.keys()):
            await self.terminate_agent(agent_id)
    
    async def _save_agent_to_db(self, agent: Agent, db):
        """Save agent to database"""
        from app.database.models import AgentModel
        
        db_agent = AgentModel(
            id=agent.id,
            name=agent.name,
            role=agent.role,
            capabilities=agent.capabilities,
            system_prompt=agent.system_prompt,
            parent_id=agent.parent_id,
            status=agent.status
        )
        
        db.add(db_agent)
        await db.commit()
    
    async def _save_task_to_db(self, agent_id: str, task: Dict[str, Any], db):
        """Save task to database"""
        from app.database.models import TaskModel
        
        db_task = TaskModel(
            id=task['id'],
            agent_id=agent_id,
            type=task['type'],
            description=task['description'],
            data=task.get('data', {}),
            status=task['status']
        )
        
        db.add(db_task)
        await db.commit()