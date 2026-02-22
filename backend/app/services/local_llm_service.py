"""
Local LLM Service - Enables hosting and running local LLMs using HuggingFace Transformers
Supports Dolphin-Mistral-24B-Venice-Edition and other models
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator, List
from dataclasses import dataclass
import torch
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for local LLM models"""
    model_id: str
    model_path: Optional[str] = None
    device: str = "auto"  # cuda, cpu, auto
    quantization: Optional[str] = None  # 4bit, 8bit, none
    max_context_length: int = 8192
    dtype: str = "auto"  # float16, bfloat16, float32, auto
    trust_remote_code: bool = True


class LocalLLMService:
    """Service for hosting and running local LLMs"""
    
    # Default model - Dolphin-Mistral-24B-Venice-Edition
    DEFAULT_MODEL = "dphn/Dolphin-Mistral-24B-Venice-Edition"
    MODELS_DIR = Path("/home/ubuntu/codeforge_ai/models")
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.model = None
        self.tokenizer = None
        self.current_config: Optional[ModelConfig] = None
        self.is_loaded = False
        self._loading_lock = asyncio.Lock()
        
        # Ensure models directory exists
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_device(self, device: str = "auto") -> str:
        """Determine the best device for inference"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device
    
    def _get_dtype(self, dtype: str = "auto", device: str = "cpu"):
        """Get the appropriate dtype for the device"""
        if dtype == "auto":
            if device == "cuda":
                return torch.float16
            elif device == "mps":
                return torch.float16
            else:
                return torch.float32
        
        dtype_map = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32
        }
        return dtype_map.get(dtype, torch.float32)
    
    async def download_model(self, model_id: str = None, force: bool = False) -> Dict[str, Any]:
        """Download a model from HuggingFace Hub"""
        model_id = model_id or self.DEFAULT_MODEL
        
        try:
            from huggingface_hub import snapshot_download
            
            model_path = self.MODELS_DIR / model_id.replace("/", "_")
            
            if model_path.exists() and not force:
                return {
                    "success": True,
                    "message": f"Model already downloaded at {model_path}",
                    "model_path": str(model_path)
                }
            
            logger.info(f"Downloading model {model_id}...")
            
            # Download in background
            downloaded_path = await asyncio.to_thread(
                snapshot_download,
                model_id,
                local_dir=str(model_path),
                local_dir_use_symlinks=False
            )
            
            return {
                "success": True,
                "message": f"Model {model_id} downloaded successfully",
                "model_path": downloaded_path
            }
            
        except Exception as e:
            logger.error(f"Failed to download model {model_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def load_model(self, config: ModelConfig = None) -> Dict[str, Any]:
        """Load a model into memory for inference"""
        async with self._loading_lock:
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
                
                config = config or ModelConfig(model_id=self.DEFAULT_MODEL)
                
                # Unload existing model if any
                if self.is_loaded:
                    await self.unload_model()
                
                device = self._get_device(config.device)
                dtype = self._get_dtype(config.dtype, device)
                
                # Determine model path
                model_path = config.model_path or str(self.MODELS_DIR / config.model_id.replace("/", "_"))
                
                # Check if model exists locally, otherwise use HF Hub
                if not Path(model_path).exists():
                    model_path = config.model_id
                    logger.info(f"Loading model from HuggingFace Hub: {model_path}")
                else:
                    logger.info(f"Loading model from local path: {model_path}")
                
                # Configure quantization
                quantization_config = None
                if config.quantization == "4bit":
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=dtype,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                elif config.quantization == "8bit":
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True
                    )
                
                # Load tokenizer
                logger.info("Loading tokenizer...")
                self.tokenizer = await asyncio.to_thread(
                    AutoTokenizer.from_pretrained,
                    model_path,
                    trust_remote_code=config.trust_remote_code
                )
                
                # Load model
                logger.info(f"Loading model on {device}...")
                load_kwargs = {
                    "trust_remote_code": config.trust_remote_code,
                    "device_map": "auto" if device == "cuda" else None,
                    "torch_dtype": dtype
                }
                
                if quantization_config:
                    load_kwargs["quantization_config"] = quantization_config
                
                self.model = await asyncio.to_thread(
                    AutoModelForCausalLM.from_pretrained,
                    model_path,
                    **load_kwargs
                )
                
                # Move to device if not using device_map
                if device != "cuda" or not load_kwargs.get("device_map"):
                    self.model = self.model.to(device)
                
                self.current_config = config
                self.is_loaded = True
                
                logger.info(f"Model {config.model_id} loaded successfully on {device}")
                
                return {
                    "success": True,
                    "message": f"Model loaded successfully",
                    "model_id": config.model_id,
                    "device": device,
                    "dtype": str(dtype)
                }
                
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
    
    async def unload_model(self) -> Dict[str, Any]:
        """Unload the current model from memory"""
        try:
            if self.model:
                del self.model
                self.model = None
            if self.tokenizer:
                del self.tokenizer
                self.tokenizer = None
            
            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.is_loaded = False
            self.current_config = None
            
            return {"success": True, "message": "Model unloaded successfully"}
            
        except Exception as e:
            logger.error(f"Failed to unload model: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
        stop_sequences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a response from the local LLM"""
        if not self.is_loaded:
            return {"success": False, "error": "No model loaded"}
        
        try:
            # Build the full prompt
            full_prompt = self._build_prompt(prompt, system_prompt)
            
            # Tokenize
            inputs = await asyncio.to_thread(
                self.tokenizer,
                full_prompt,
                return_tensors="pt"
            )
            inputs = inputs.to(self.model.device)
            
            # Generate
            generation_config = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": temperature > 0,
                "pad_token_id": self.tokenizer.eos_token_id
            }
            
            if stop_sequences:
                stop_ids = [self.tokenizer.encode(seq, add_special_tokens=False) for seq in stop_sequences]
                generation_config["stop_token_ids"] = stop_ids
            
            outputs = await asyncio.to_thread(
                self.model.generate,
                **inputs,
                **generation_config
            )
            
            # Decode
            response = await asyncio.to_thread(
                self.tokenizer.decode,
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            
            return {
                "success": True,
                "response": response.strip(),
                "model": self.current_config.model_id,
                "tokens_generated": len(outputs[0]) - inputs.input_ids.shape[1]
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream generate responses token by token"""
        if not self.is_loaded:
            yield '{"error": "No model loaded"}'
            return
        
        try:
            from transformers import TextIteratorStreamer
            from threading import Thread
            
            # Build the full prompt
            full_prompt = self._build_prompt(prompt, system_prompt)
            
            # Tokenize
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
            inputs = inputs.to(self.model.device)
            
            # Create streamer
            streamer = TextIteratorStreamer(
                self.tokenizer,
                skip_prompt=True,
                skip_special_tokens=True
            )
            
            # Generation kwargs
            generation_kwargs = {
                **inputs,
                "streamer": streamer,
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": temperature > 0,
                "pad_token_id": self.tokenizer.eos_token_id
            }
            
            # Run generation in a thread
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            
            # Stream tokens
            for text in streamer:
                yield text
                await asyncio.sleep(0)  # Allow other async tasks to run
            
            thread.join()
            
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            yield f'{{"error": "{str(e)}"}}'
    
    def _build_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Build the full prompt with optional system prompt"""
        if system_prompt:
            # ChatML format (common for Dolphin models)
            return f"""<|im_start|>system
{system_prompt}
<|im_end|>
<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
"""
        return f"""<|im_start|>user
{prompt}
<|im_end|>
<|im_start|>assistant
"""
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the LLM service"""
        status = {
            "is_loaded": self.is_loaded,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        }
        
        if self.is_loaded and self.current_config:
            status.update({
                "model_id": self.current_config.model_id,
                "device": self.current_config.device,
                "quantization": self.current_config.quantization
            })
            
            if torch.cuda.is_available():
                status["gpu_memory_allocated"] = f"{torch.cuda.memory_allocated() / 1e9:.2f} GB"
                status["gpu_memory_reserved"] = f"{torch.cuda.memory_reserved() / 1e9:.2f} GB"
        
        return status
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """List locally downloaded models"""
        models = []
        
        if self.MODELS_DIR.exists():
            for path in self.MODELS_DIR.iterdir():
                if path.is_dir():
                    config_file = path / "config.json"
                    if config_file.exists():
                        models.append({
                            "name": path.name,
                            "path": str(path),
                            "is_loaded": self.is_loaded and self.current_config and 
                                        self.current_config.model_id.replace("/", "_") == path.name
                        })
        
        return models
    
    # Database operations
    async def save_config_to_db(self, config: ModelConfig, name: str) -> Dict[str, Any]:
        """Save a model configuration to the database"""
        if not self.db_session:
            return {"success": False, "error": "No database session"}
        
        try:
            from app.database.models import LocalLLMConfig
            
            db_config = LocalLLMConfig(
                name=name,
                model_id=config.model_id,
                model_path=config.model_path,
                is_downloaded=Path(config.model_path).exists() if config.model_path else False,
                device=config.device,
                quantization=config.quantization,
                max_context_length=config.max_context_length
            )
            
            self.db_session.add(db_config)
            await self.db_session.commit()
            await self.db_session.refresh(db_config)
            
            return {"success": True, "config_id": db_config.id}
            
        except Exception as e:
            await self.db_session.rollback()
            return {"success": False, "error": str(e)}
    
    async def get_configs_from_db(self) -> List[Dict[str, Any]]:
        """Get all saved configurations from the database"""
        if not self.db_session:
            return []
        
        try:
            from sqlalchemy import select
            from app.database.models import LocalLLMConfig
            
            result = await self.db_session.execute(
                select(LocalLLMConfig).order_by(LocalLLMConfig.created_at.desc())
            )
            configs = result.scalars().all()
            
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "model_id": c.model_id,
                    "model_path": c.model_path,
                    "is_downloaded": c.is_downloaded,
                    "is_active": c.is_active,
                    "device": c.device,
                    "quantization": c.quantization,
                    "max_context_length": c.max_context_length
                }
                for c in configs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get configs: {e}")
            return []
