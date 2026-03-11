import os
import json
import logging
import asyncio
import litellm
import requests
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Completely suppress litellm's verbose telemetry/info logs by default
litellm.suppress_debug_info = True
litellm.telemetry = False
os.environ["LITELLM_LOG"] = "ERROR" # Only show critical errors

# Silence the litellm python logger
logging.getLogger('LiteLLM').setLevel(logging.ERROR)

class LLMFactory:
    """Factory pattern for initializing the correct LLM provider."""
    
    @staticmethod
    def get_provider() -> Optional['LLMProvider']:
        # 1. Check for Local AI configuration
        api_base = os.getenv("LOCAL_AI_API_BASE")
        if api_base:
            provider_type = os.getenv("LOCAL_AI_PROVIDER")
            model_name = os.getenv("LOCAL_AI_MODEL")
            
            # Auto-detect provider if not explicitly set
            if not provider_type:
                parsed_url = urlparse(api_base)
                port = parsed_url.port
                if port == 11434:
                    provider_type = "ollama"
                elif port == 1234:
                    provider_type = "lmstudio"
                elif port == 8080:
                    provider_type = "llamacpp"
                else:
                    # Fallback to a standard openai compatible server
                    provider_type = "openai_compatible"
            
            return LocalAIProvider(provider_type, api_base, model_name)

        # 2. Check for OpenAI Fallback
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            return OpenAIProvider()

        # 3. No fallback configured
        return None

class LLMProvider:
    """Base interface for all LLM providers."""
    async def generate_json(self, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class LocalAIProvider(LLMProvider):
    """Provider handling various Local AI backends (Ollama, LM Studio, Llama.cpp)."""
    def __init__(self, provider_type: str, api_base: str, model_name: Optional[str] = None):
        self.provider_type = provider_type.lower()
        self.api_base = api_base.rstrip('/')
        self.model_name = model_name

    async def generate_json(self, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> Dict[str, Any]:
        messages_copy = list(messages)
        messages_copy.append({
            "role": "user",
            "content": f"Please provide the output as a JSON object adhering exactly to this JSON schema:\n{json.dumps(schema, indent=2)}\n\nOnly output the JSON object."
        })

        model_string = await asyncio.to_thread(self._get_model_string)

        # Ollama via litellm expects the base URL without /v1 sometimes, but litellm handles "ollama/" routing.
        # For OpenAI compatible endpoints, we need to pass the base URL directly.
        api_base = self.api_base
        if self.provider_type == "ollama" and api_base.endswith("/v1"):
            api_base = api_base[:-3] # Strip /v1 for ollama native

        try:
            response = await litellm.acompletion(
                model=model_string,
                messages=messages_copy,
                api_base=api_base,
                api_key="sk-no-key-required",
                response_format={"type": "json_object"},
                temperature=0.1, # Low temperature for precise formatting
                max_tokens=800,  # CRITICAL: Clamp output tokens to prevent VRAM explosions
                num_ctx=2048,    # CRITICAL: Force small context window for Ollama/Local backends
                drop_params=True # Ignore unsupported params depending on the backend
            )
            content = response.choices[0].message.content
            return self._clean_json(content)
        except Exception as e:
            logger.error(f"Local AI Error ({self.provider_type}): {e}")
            return {}

    def _get_model_string(self) -> str:
        if self.provider_type == "ollama":
            model = self.model_name or self._fetch_ollama_model()
            return f"ollama/{model}"
        elif self.provider_type in ["lmstudio", "llamacpp", "openai_compatible"]:
            model = self.model_name or self._fetch_openai_compatible_model()
            return f"openai/{model}"
        return self.model_name or "local-model"

    def _fetch_ollama_model(self) -> str:
        try:
            # Ollama API endpoints are at the root
            base = self.api_base.replace("/v1", "")
            response = requests.get(f"{base}/api/tags", timeout=5)
            if response.ok:
                models = response.json().get("models", [])
                if models:
                    return models[0]["name"]
        except Exception as e:
            logger.warning(f"Could not auto-detect Ollama model: {e}")
        return "qwen2.5"

    def _fetch_openai_compatible_model(self) -> str:
        try:
            response = requests.get(f"{self.api_base}/models", timeout=5)
            if response.ok:
                models = response.json().get("data", [])
                
                # FIRST PASS: Check if any model is currently loaded in VRAM
                for m in models:
                    status = m.get("status")
                    if isinstance(status, dict) and status.get("value") == "loaded":
                        return m["id"]
                    elif isinstance(status, str) and status == "loaded":
                        return m["id"]

                # CRITICAL VRAM FIX: If no model is explicitly loaded, DO NOT blindly
                # grab models[0]. In LM Studio, that could be a 122B model, which will 
                # cause a massive JIT-load and instantly crash the machine's VRAM.
                # Instead, fallback to a generic string. LM Studio will route to whatever
                # default is loaded in the GUI.
                return "local-model"
        except Exception as e:
            logger.warning(f"Could not auto-detect model from {self.api_base}: {e}")
        return "local-model"

    def _clean_json(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            logger.error(f"JSON decode failure. Raw output: {content}")
            return {}

class OpenAIProvider(LLMProvider):
    """Fallback provider for cloud OpenAI or OpenAI compatible endpoints explicitly set via OPENAI_API_KEY."""
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip('/')
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def generate_json(self, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> Dict[str, Any]:
        messages_copy = list(messages)
        messages_copy.append({
            "role": "user",
            "content": f"Please provide the output as a JSON object adhering exactly to this JSON schema:\n{json.dumps(schema, indent=2)}\n\nOnly output the JSON object."
        })

        try:
            response = await litellm.acompletion(
                model=self.model_name,
                messages=messages_copy,
                api_base=self.api_base,
                api_key=self.api_key,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,  # CRITICAL: Prevent runaway generation costs/VRAM
            )
            content = response.choices[0].message.content
            return self._clean_json(content)
        except Exception as e:
            logger.error(f"OpenAI Provider Error: {e}")
            return {}

    def _clean_json(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            logger.error(f"JSON decode failure. Raw output: {content}")
            return {}
