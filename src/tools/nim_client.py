"""
NIM (NVIDIA Inference Microservice) Client for Nemotron LLM

Provides OpenAI-compatible interface for:
- Chat completions with structured output
- Health checks
- Model discovery
- Low-temperature deterministic generation
"""

import logging
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

import requests
from requests.exceptions import RequestException

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class NIMResponse:
    """Response from NIM chat completion"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    latency_ms: float
    
    def parse_json(self) -> Optional[Dict[str, Any]]:
        """Attempt to parse content as JSON with multiple fallback strategies"""
        if not self.content:
            return None
            
        content = self.content.strip()
        
        # Strategy 1: Try direct JSON parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code blocks (```json ... ``` or ``` ... ```)
        try:
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if json_match:
                return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Find JSON object boundaries { ... }
        try:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = content[start:end + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Strategy 4: Find JSON array boundaries [ ... ]
        try:
            start = content.find('[')
            end = content.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_str = content[start:end + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Strategy 5: Try to fix common JSON issues
        try:
            # Remove trailing commas before } or ]
            fixed = re.sub(r',\s*([}\]])', r'\1', content)
            # Try to find JSON in the fixed content
            start = fixed.find('{')
            end = fixed.rfind('}')
            if start != -1 and end != -1:
                return json.loads(fixed[start:end + 1])
        except json.JSONDecodeError:
            pass
        
        logger.warning(f"Failed to parse response as JSON. Content preview: {content[:200]}...")
        return None


class NIMClient:
    """
    Client for NVIDIA NIM (Nemotron) with OpenAI-compatible API.
    
    Designed for DGX Spark deployment with:
    - Health monitoring
    - Structured JSON output
    - Low-temperature deterministic generation
    - Schema-guided prompting
    
    Example usage:
        client = NIMClient()
        
        # Check health
        if client.is_ready():
            # Simple generation
            response = client.chat("Summarize this risk profile...")
            
            # Structured output
            response = client.chat_structured(
                prompt="Generate action plan",
                schema=ActionPlanSchema,
                temperature=0.1
            )
    """
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        model: str = None,
        default_temperature: float = 0.3,
        default_max_tokens: int = 2000,
        timeout: float = 300.0,  # Increased timeout for slower models
    ):
        self.base_url = base_url or Config.NEMOTRON_BASE_URL
        self.api_key = api_key or Config.NEMOTRON_API_KEY
        self.model = model or Config.NEMOTRON_MODEL
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.timeout = timeout  # Store timeout
        
        # Initialize OpenAI client if available
        self.openai_client = None
        if OpenAI:
            self.openai_client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,  # Add timeout to OpenAI client
            )
    
    def is_ready(self) -> bool:
        """Check if NIM service is ready"""
        return self.health_check("ready")
    
    def is_live(self) -> bool:
        """Check if NIM service is live"""
        return self.health_check("live")
    
    def health_check(self, check_type: str = "ready") -> bool:
        """
        Perform NIM health check.
        
        Args:
            check_type: 'ready' or 'live'
        
        Returns:
            True if healthy
        """
        base = Config.get_nim_base_url()
        endpoint = Config.NIM_HEALTH_READY if check_type == "ready" else Config.NIM_HEALTH_LIVE
        url = f"{base}{endpoint}"
        
        try:
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except RequestException as e:
            logger.warning(f"NIM health check failed: {e}")
            return False
    
    def get_models(self) -> List[str]:
        """Get available models from NIM"""
        base = Config.get_nim_base_url()
        url = f"{base}{Config.NIM_MODELS_ENDPOINT}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m.get("id", m.get("name")) for m in data.get("data", [])]
        except RequestException as e:
            logger.warning(f"Failed to get NIM models: {e}")
            return []
    
    def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        stop: List[str] = None,
    ) -> NIMResponse:
        """
        Generate chat completion.
        
        Args:
            prompt: User message
            system_prompt: Optional system message
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
        
        Returns:
            NIMResponse with generated content
        """
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self._call_completions(messages, temperature, max_tokens, stop)
    
    def chat_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any] = None,
        system_prompt: str = None,
        temperature: float = 0.1,
        max_tokens: int = None,
        examples: List[Dict[str, str]] = None,
    ) -> NIMResponse:
        """
        Generate structured JSON output.
        
        Uses schema-guided prompting to ensure valid JSON output.
        
        Args:
            prompt: User message
            output_schema: JSON schema for expected output
            system_prompt: Optional system message
            temperature: Sampling temperature (default 0.1 for consistency)
            max_tokens: Maximum tokens
            examples: Optional few-shot examples
        
        Returns:
            NIMResponse (use .parse_json() to get dict)
        """
        max_tokens = max_tokens or self.default_max_tokens
        
        # Build system prompt with schema instructions
        schema_instruction = ""
        if output_schema:
            schema_str = json.dumps(output_schema, indent=2)
            schema_instruction = f"""
You must respond with valid JSON that conforms to this schema:
```json
{schema_str}
```
Do not include any text before or after the JSON. Only output the JSON object."""
        
        full_system = system_prompt or ""
        if schema_instruction:
            full_system = f"{full_system}\n\n{schema_instruction}".strip()
        
        # Add examples if provided
        messages = []
        if full_system:
            messages.append({"role": "system", "content": full_system})
        
        if examples:
            for ex in examples:
                messages.append({"role": "user", "content": ex.get("input", "")})
                messages.append({"role": "assistant", "content": ex.get("output", "")})
        
        messages.append({"role": "user", "content": prompt})
        
        return self._call_completions(messages, temperature, max_tokens)
    
    def chat_with_evidence(
        self,
        prompt: str,
        evidence_pack: Dict[str, Any],
        output_schema: Dict[str, Any] = None,
        system_prompt: str = None,
        temperature: float = 0.1,
    ) -> NIMResponse:
        """
        Generate response grounded in evidence.
        
        Enforces evidence-first approach:
        - All claims must reference evidence IDs
        - No external knowledge claims
        
        Args:
            prompt: User message
            evidence_pack: Evidence data with refs
            output_schema: Expected output schema
            system_prompt: Base system prompt
        
        Returns:
            NIMResponse
        """
        evidence_str = json.dumps(evidence_pack, indent=2)
        
        grounding_instruction = f"""
You have access to the following evidence. Base your response ONLY on this evidence.
Every claim or recommendation must include an evidence_ref from the evidence provided.
If you cannot support a claim with evidence, say so explicitly.

EVIDENCE:
{evidence_str}

CRITICAL: Do not make claims that are not supported by the evidence above.
"""
        
        full_system = f"{system_prompt or ''}\n\n{grounding_instruction}".strip()
        
        return self.chat_structured(
            prompt=prompt,
            output_schema=output_schema,
            system_prompt=full_system,
            temperature=temperature,
        )
    
    def _call_completions(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        stop: List[str] = None,
    ) -> NIMResponse:
        """Internal method to call chat completions API"""
        start_time = datetime.utcnow()
        
        try:
            if self.openai_client:
                # Use OpenAI SDK
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if stop:
                    kwargs["stop"] = stop
                
                response = self.openai_client.chat.completions.create(**kwargs)
                
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return NIMResponse(
                    content=response.choices[0].message.content.strip(),
                    model=response.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                    finish_reason=response.choices[0].finish_reason,
                    latency_ms=latency_ms,
                )
            else:
                # Use raw requests
                url = f"{self.base_url}/chat/completions"
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if stop:
                    payload["stop"] = stop
                
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, json=payload, headers=headers, timeout=120)
                response.raise_for_status()
                
                data = response.json()
                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return NIMResponse(
                    content=data["choices"][0]["message"]["content"].strip(),
                    model=data.get("model", self.model),
                    usage=data.get("usage", {}),
                    finish_reason=data["choices"][0].get("finish_reason", "stop"),
                    latency_ms=latency_ms,
                )
                
        except Exception as e:
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"NIM chat completion failed: {e}")
            
            return NIMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                usage={},
                finish_reason="error",
                latency_ms=latency_ms,
            )


# Convenience function for simple chat
def nim_chat(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """
    Simple function interface for NIM chat.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name (uses Config default)
        temperature: Sampling temperature
        max_tokens: Maximum tokens
    
    Returns:
        Generated content string
    """
    client = NIMClient(model=model)
    
    # Extract system and user messages
    system_msg = None
    user_msg = ""
    
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        elif msg["role"] == "user":
            user_msg = msg["content"]
    
    response = client.chat(
        prompt=user_msg,
        system_prompt=system_msg,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    return response.content
