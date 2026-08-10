import os
import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime


class VeniceAIService:
    """
    Venice AI Integration Service
    Handles communication with Venice AI API using Dolphin uncensored model
    """
    
    def __init__(self):
        self.api_key = os.getenv("VENICE_API_KEY")
        self.api_secret = os.getenv("VENICE_API_SECRET")
        self.base_url = "https://api.venice.ai/api/v1"
        self.default_model = "dolphin-2.9.2-qwen2-72b"  # Dolphin uncensored
        self._available = bool(self.api_key and self.api_secret)
        
        if not self._available:
            print("[WARN] Venice AI credentials not configured - Venice AI features disabled")
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def _check_available(self):
        if not self._available:
            raise ValueError("Venice AI credentials not configured. Set VENICE_API_KEY and VENICE_API_SECRET environment variables.")
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completions from Venice AI
        """
        self._check_available()
        model = model or self.default_model
        
        # Prepare messages with system prompt
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        formatted_messages.extend(messages)
        
        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Secret": self.api_secret,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            
                            if data == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    
                                    if content:
                                        yield {
                                            "type": "content",
                                            "content": content,
                                            "model": model,
                                            "timestamp": datetime.now().isoformat()
                                        }
                                    
                                    # Handle tool calls if present
                                    if "tool_calls" in delta:
                                        yield {
                                            "type": "tool_call",
                                            "tool_calls": delta["tool_calls"],
                                            "timestamp": datetime.now().isoformat()
                                        }
                            except json.JSONDecodeError:
                                continue
            
            except httpx.HTTPError as e:
                yield {
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
    
    async def generate_code(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate code from natural language prompt
        """
        system_prompt = self._build_code_generation_prompt(language)
        
        messages = []
        if context:
            messages.append({
                "role": "user",
                "content": f"Context: {json.dumps(context)}\n\nTask: {prompt}"
            })
        else:
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        full_response = ""
        async for chunk in self.stream_chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for code generation
        ):
            if chunk['type'] == 'content':
                full_response += chunk['content']
        
        # Parse code blocks from response
        code_blocks = self._extract_code_blocks(full_response)
        
        return {
            "raw_response": full_response,
            "code_blocks": code_blocks,
            "language": language,
            "timestamp": datetime.now().isoformat()
        }
    
    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response with tool calling support
        """
        payload = {
            "model": self.default_model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.7
        }
        
        if system_prompt:
            payload["messages"].insert(0, {
                "role": "system",
                "content": system_prompt
            })
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Secret": self.api_secret,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    def _build_code_generation_prompt(self, language: Optional[str] = None) -> str:
        """
        Build system prompt for code generation
        """
        base_prompt = """You are an expert software engineer specialized in generating clean, efficient, and well-documented code.

When generating code:
1. Write production-ready code with proper error handling
2. Include comprehensive comments explaining complex logic
3. Follow language-specific best practices and conventions
4. Use meaningful variable and function names
5. Include type hints where applicable
6. Add docstrings for functions and classes
7. Consider edge cases and validation
8. Make code modular and maintainable

Format your response with clear code blocks using markdown syntax."""
        
        if language:
            base_prompt += f"\n\nGenerate code in {language} language."
        
        return base_prompt
    
    def _extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from markdown formatted text
        """
        code_blocks = []
        lines = text.split("\n")
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("```"):
                # Extract language
                language = line.strip()[3:].strip()
                
                # Collect code
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                
                code_blocks.append({
                    "language": language or "text",
                    "code": "\n".join(code_lines)
                })
            
            i += 1
        
        return code_blocks
    
    async def update_system_prompt(self, db, update_data: Dict[str, Any]):
        """
        Update and store custom system prompt
        """
        # Store in database
        from app.database.models import SystemPrompt
        
        prompt = SystemPrompt(
            name=update_data.get('name', 'default'),
            content=update_data['content'],
            category=update_data.get('category', 'general'),
            is_active=update_data.get('is_active', True)
        )
        
        db.add(prompt)
        await db.commit()
        await db.refresh(prompt)
        
        return prompt
    
    async def get_system_prompts(self, db, category: Optional[str] = None):
        """
        Retrieve stored system prompts
        """
        from app.database.models import SystemPrompt
        from sqlalchemy import select
        
        query = select(SystemPrompt)
        if category:
            query = query.where(SystemPrompt.category == category)
        
        result = await db.execute(query)
        prompts = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "name": p.name,
                "content": p.content,
                "category": p.category,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat()
            }
            for p in prompts
        ]