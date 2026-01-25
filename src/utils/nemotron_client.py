"""
Nemotron LLM client wrapper using OpenAI-compatible interface

Supports:
- NVIDIA API (https://integrate.api.nvidia.com/v1) - requires NVIDIA_API_KEY
- Local NIM on DGX Spark (http://localhost:8000/v1)

Available models:
- nvidia/llama-3.1-nemotron-70b-instruct (recommended)
- nvidia/llama-3.1-nemotron-ultra-253b-v1 (highest quality)
- nvidia/nemotron-4-340b-instruct (legacy)
"""

import json
from openai import OpenAI
from .config import Config
import logging

logger = logging.getLogger(__name__)


class NemotronClient:
    """
    Client for interacting with Nemotron LLM via OpenAI-compatible API.
    
    Works with both NVIDIA's hosted API and local NIM deployments.
    
    Example usage:
        # Using NVIDIA API
        client = NemotronClient()  # Uses env vars
        
        # Using local NIM
        client = NemotronClient(
            base_url="http://localhost:8000/v1",
            api_key="local",
            model="nvidia/nemotron-4-340b-instruct"
        )
        
        response = client.generate("What is SF's zoning policy?")
    """
    
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = base_url or Config.NEMOTRON_BASE_URL
        self.api_key = api_key or Config.NEMOTRON_API_KEY
        self.model = model or Config.NEMOTRON_MODEL
        
        if not self.api_key:
            logger.warning(
                "No NVIDIA API key configured. Set NVIDIA_API_KEY or NEMOTRON_API_KEY "
                "environment variable for NVIDIA API access, or use local NIM."
            )
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "no-key"  # OpenAI client requires non-empty string
        )
        
        logger.info(f"NemotronClient initialized: base_url={self.base_url}, model={self.model}")
    
    def is_available(self) -> bool:
        """Check if the Nemotron API is available"""
        try:
            # Try a minimal request
            response = self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"Nemotron API not available: {e}")
            return False
    
    def generate(self, prompt, system_prompt=None, max_tokens=1024, temperature=0.7):
        """
        Generate text using Nemotron LLM
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
        
        Returns:
            Generated text string
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Debug output
            prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
            print(f"\033[95m[LLM] 🤖 Nemotron → Sending request (model: {self.model})\033[0m")
            print(f"\033[95m[LLM] 📝 Prompt: {prompt_preview}\033[0m")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            result = response.choices[0].message.content.strip()
            result_preview = result[:100] + "..." if len(result) > 100 else result
            print(f"\033[95m[LLM] ✓ Nemotron → Response received ({len(result)} chars)\033[0m")
            print(f"\033[95m[LLM] 📨 Response: {result_preview}\033[0m")
            
            return result
        
        except Exception as e:
            logger.error(f"Error generating text with Nemotron: {e}")
            print(f"\033[91m[LLM] ✗ Nemotron → Error: {e}\033[0m")
            return f"Error: Unable to generate response. {str(e)}"
    
    def generate_json(self, prompt, system_prompt=None, schema_hint=None, max_tokens=2048):
        """
        Generate structured JSON output.
        
        Args:
            prompt: User prompt describing what JSON to generate
            system_prompt: Optional system prompt
            schema_hint: Example JSON structure or schema description
            max_tokens: Maximum tokens
            
        Returns:
            Parsed JSON dict, or error dict if parsing fails
        """
        json_system = (system_prompt or "") + (
            "\n\nYou MUST respond with valid JSON only. "
            "Do not include markdown code blocks or explanatory text."
        )
        
        if schema_hint:
            prompt = f"{prompt}\n\nExpected JSON structure:\n{schema_hint}"
        
        response = self.generate(
            prompt, 
            system_prompt=json_system, 
            max_tokens=max_tokens, 
            temperature=0.2  # Lower temp for structured output
        )
        
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {"error": "JSON parse failed", "raw_response": response[:500]}
    
    def generate_structured(self, prompt, system_prompt=None, format_instructions=None):
        """
        Generate structured output (e.g., JSON) with format instructions
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            format_instructions: Instructions for output format
        
        Returns:
            Generated text (should be parsed as JSON if format_instructions provided)
        """
        full_prompt = prompt
        if format_instructions:
            full_prompt = f"{prompt}\n\nFormat your response as: {format_instructions}"
        
        return self.generate(full_prompt, system_prompt=system_prompt, temperature=0.3)
