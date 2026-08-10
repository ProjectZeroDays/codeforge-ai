"""
API Key Management Service
Secure storage and management of API keys with encryption
"""

import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid
import base64
import json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

logger = logging.getLogger(__name__)


class APIKeyEncryption:
    """Handles encryption/decryption of API keys"""
    
    def __init__(self, master_key: Optional[str] = None):
        # Use environment variable or generate a key
        self.master_key = master_key or os.getenv("ENCRYPTION_KEY", self._generate_key())
        self.fernet = self._initialize_fernet()
    
    def _generate_key(self) -> str:
        """Generate a new encryption key"""
        return Fernet.generate_key().decode()
    
    def _initialize_fernet(self) -> Fernet:
        """Initialize Fernet with the master key"""
        # If key isn't proper Fernet format, derive one
        try:
            return Fernet(self.master_key.encode())
        except:
            # Derive a key from the master key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'codeforge_ai_salt',  # In production, use a random salt stored securely
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
            return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string"""
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string"""
        return self.fernet.decrypt(ciphertext.encode()).decode()
    
    def hash_key(self, key: str) -> str:
        """Create a SHA256 hash of the key for verification"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_prefix(self, key: str, length: int = 8) -> str:
        """Get the first few characters of a key for identification"""
        return key[:length] + "..." if len(key) > length else key


class APIKeyService:
    """Service for managing API keys"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption = APIKeyEncryption(encryption_key)
    
    async def add_api_key(
        self,
        db: AsyncSession,
        name: str,
        provider: str,
        api_key: str,
        description: Optional[str] = None,
        environment: str = "production",
        expires_at: Optional[datetime] = None,
        rotation_reminder_days: int = 90
    ) -> Dict:
        """Add a new API key with encryption"""
        from app.database.models_extended import APIKey
        
        # Encrypt the key
        encrypted_key = self.encryption.encrypt(api_key)
        key_hash = self.encryption.hash_key(api_key)
        key_prefix = self.encryption.get_prefix(api_key)
        
        # Validate the key (basic validation)
        is_valid, validation_error = await self._validate_key(provider, api_key)
        
        api_key_record = APIKey(
            name=name,
            provider=provider,
            encrypted_key=encrypted_key,
            key_hash=key_hash,
            key_prefix=key_prefix,
            description=description,
            environment=environment,
            expires_at=expires_at,
            rotation_reminder_days=rotation_reminder_days,
            is_active=True,
            is_validated=is_valid,
            validation_error=validation_error
        )
        
        db.add(api_key_record)
        await db.commit()
        
        return {
            "id": api_key_record.id,
            "name": name,
            "provider": provider,
            "key_prefix": key_prefix,
            "is_validated": is_valid,
            "message": "API key added successfully" if is_valid else f"Key added but validation failed: {validation_error}"
        }
    
    async def get_api_key(
        self,
        db: AsyncSession,
        key_id: str,
        decrypt: bool = False
    ) -> Optional[Dict]:
        """Get an API key by ID"""
        from app.database.models_extended import APIKey
        
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        key_record = result.scalar_one_or_none()
        
        if not key_record:
            return None
        
        response = {
            "id": key_record.id,
            "name": key_record.name,
            "provider": key_record.provider,
            "key_prefix": key_record.key_prefix,
            "description": key_record.description,
            "environment": key_record.environment,
            "expires_at": key_record.expires_at.isoformat() if key_record.expires_at else None,
            "is_active": key_record.is_active,
            "is_validated": key_record.is_validated,
            "usage_count": key_record.usage_count,
            "last_used_at": key_record.last_used_at.isoformat() if key_record.last_used_at else None,
            "created_at": key_record.created_at.isoformat()
        }
        
        if decrypt:
            response["api_key"] = self.encryption.decrypt(key_record.encrypted_key)
        
        return response
    
    async def list_api_keys(
        self,
        db: AsyncSession,
        provider: Optional[str] = None,
        environment: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict]:
        """List all API keys (without decryption)"""
        from app.database.models_extended import APIKey
        
        query = select(APIKey)
        
        if provider:
            query = query.where(APIKey.provider == provider)
        if environment:
            query = query.where(APIKey.environment == environment)
        if active_only:
            query = query.where(APIKey.is_active == True)
        
        result = await db.execute(query)
        keys = result.scalars().all()
        
        return [
            {
                "id": k.id,
                "name": k.name,
                "provider": k.provider,
                "key_prefix": k.key_prefix,
                "environment": k.environment,
                "is_active": k.is_active,
                "is_validated": k.is_validated,
                "usage_count": k.usage_count,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "needs_rotation": self._needs_rotation(k),
                "created_at": k.created_at.isoformat()
            }
            for k in keys
        ]
    
    async def update_api_key(
        self,
        db: AsyncSession,
        key_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        new_key: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict:
        """Update an API key"""
        from app.database.models_extended import APIKey
        
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        key_record = result.scalar_one_or_none()
        
        if not key_record:
            raise ValueError(f"API key {key_id} not found")
        
        if name:
            key_record.name = name
        if description:
            key_record.description = description
        if is_active is not None:
            key_record.is_active = is_active
        
        if new_key:
            # This is a key rotation
            key_record.encrypted_key = self.encryption.encrypt(new_key)
            key_record.key_hash = self.encryption.hash_key(new_key)
            key_record.key_prefix = self.encryption.get_prefix(new_key)
            key_record.last_rotated_at = datetime.utcnow()
            
            # Revalidate
            is_valid, validation_error = await self._validate_key(key_record.provider, new_key)
            key_record.is_validated = is_valid
            key_record.validation_error = validation_error
        
        await db.commit()
        
        return {
            "id": key_record.id,
            "name": key_record.name,
            "message": "API key updated successfully"
        }
    
    async def delete_api_key(self, db: AsyncSession, key_id: str) -> Dict:
        """Delete an API key"""
        from app.database.models_extended import APIKey
        
        await db.execute(
            delete(APIKey).where(APIKey.id == key_id)
        )
        await db.commit()
        
        return {"message": "API key deleted successfully"}
    
    async def rotate_key(
        self,
        db: AsyncSession,
        key_id: str,
        new_key: str
    ) -> Dict:
        """Rotate an API key to a new value"""
        return await self.update_api_key(db, key_id, new_key=new_key)
    
    async def use_key(self, db: AsyncSession, key_id: str) -> str:
        """Get decrypted key for use and log the usage"""
        from app.database.models_extended import APIKey, APIKeyUsageLog
        
        result = await db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        key_record = result.scalar_one_or_none()
        
        if not key_record:
            raise ValueError(f"API key {key_id} not found")
        
        if not key_record.is_active:
            raise ValueError(f"API key {key_id} is inactive")
        
        # Update usage
        key_record.usage_count += 1
        key_record.last_used_at = datetime.utcnow()
        
        # Update monthly usage
        month_key = datetime.utcnow().strftime("%Y-%m")
        monthly_usage = key_record.monthly_usage or {}
        monthly_usage[month_key] = monthly_usage.get(month_key, 0) + 1
        key_record.monthly_usage = monthly_usage
        
        await db.commit()
        
        return self.encryption.decrypt(key_record.encrypted_key)
    
    async def log_usage(
        self,
        db: AsyncSession,
        key_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        tokens_used: Optional[int] = None,
        cost_estimate: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Log detailed usage of an API key"""
        from app.database.models_extended import APIKeyUsageLog
        
        log = APIKeyUsageLog(
            api_key_id=key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            cost_estimate=cost_estimate,
            error_message=error_message
        )
        
        db.add(log)
        await db.commit()
    
    async def get_usage_stats(
        self,
        db: AsyncSession,
        key_id: str,
        days: int = 30
    ) -> Dict:
        """Get usage statistics for an API key"""
        from app.database.models_extended import APIKey, APIKeyUsageLog
        from sqlalchemy import func
        
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get key info
        key_result = await db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        key_record = key_result.scalar_one_or_none()
        
        if not key_record:
            return None
        
        # Get usage logs
        logs_result = await db.execute(
            select(APIKeyUsageLog).where(
                APIKeyUsageLog.api_key_id == key_id,
                APIKeyUsageLog.timestamp >= since
            )
        )
        logs = logs_result.scalars().all()
        
        total_requests = len(logs)
        total_tokens = sum(l.tokens_used or 0 for l in logs)
        total_cost = sum(l.cost_estimate or 0 for l in logs)
        avg_response_time = sum(l.response_time_ms or 0 for l in logs) / total_requests if total_requests > 0 else 0
        error_count = sum(1 for l in logs if l.status_code >= 400)
        
        return {
            "key_id": key_id,
            "key_name": key_record.name,
            "period_days": days,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_response_time_ms": round(avg_response_time, 2),
            "error_count": error_count,
            "error_rate": round(error_count / total_requests * 100, 2) if total_requests > 0 else 0,
            "monthly_usage": key_record.monthly_usage
        }
    
    async def get_keys_needing_rotation(self, db: AsyncSession) -> List[Dict]:
        """Get API keys that need rotation based on their settings"""
        from app.database.models_extended import APIKey
        
        result = await db.execute(
            select(APIKey).where(APIKey.is_active == True)
        )
        keys = result.scalars().all()
        
        return [
            {
                "id": k.id,
                "name": k.name,
                "provider": k.provider,
                "days_since_rotation": (datetime.utcnow() - (k.last_rotated_at or k.created_at)).days,
                "rotation_reminder_days": k.rotation_reminder_days
            }
            for k in keys
            if self._needs_rotation(k)
        ]
    
    def _needs_rotation(self, key_record) -> bool:
        """Check if a key needs rotation"""
        last_rotation = key_record.last_rotated_at or key_record.created_at
        days_since = (datetime.utcnow() - last_rotation).days
        return days_since >= key_record.rotation_reminder_days
    
    async def _validate_key(self, provider: str, api_key: str) -> tuple[bool, Optional[str]]:
        """Validate an API key by testing it"""
        import httpx
        
        try:
            if provider == "openai":
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"OpenAI API returned status {response.status_code}"
            
            elif provider == "anthropic":
                # Anthropic validation would go here
                return True, None  # Skip validation for now
            
            elif provider == "venice_ai":
                # Venice AI validation
                return True, None  # Skip validation for now
            
            elif provider == "github":
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.github.com/user",
                        headers={"Authorization": f"token {api_key}"},
                        timeout=10
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"GitHub API returned status {response.status_code}"
            
            elif provider == "huggingface":
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://huggingface.co/api/whoami-v2",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"HuggingFace API returned status {response.status_code}"
            
            # Unknown provider - skip validation
            return True, None
            
        except Exception as e:
            return False, str(e)


# Get active key for a provider
async def get_active_key_for_provider(db: AsyncSession, provider: str) -> Optional[str]:
    """Utility function to get the active API key for a provider"""
    service = APIKeyService()
    from app.database.models_extended import APIKey
    
    result = await db.execute(
        select(APIKey).where(
            APIKey.provider == provider,
            APIKey.is_active == True,
            APIKey.is_validated == True
        ).order_by(APIKey.created_at.desc())
    )
    key_record = result.scalar_one_or_none()
    
    if key_record:
        return service.encryption.decrypt(key_record.encrypted_key)
    return None
