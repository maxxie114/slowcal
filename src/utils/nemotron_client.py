"""
Nemotron LLM client wrapper using OpenAI-compatible interface
"""

from openai import OpenAI
from .config import Config
import logging
import json

logger = logging.getLogger(__name__)

class NemotronClient:
    """Client for interacting with Nemotron LLM via NVIDIA API"""
    
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = base_url or Config.NEMOTRON_BASE_URL
        self.api_key = api_key or Config.NEMOTRON_API_KEY
        self.model = model or Config.NEMOTRON_MODEL
        
        if not self.api_key:
            raise ValueError("NEMOTRON_API_KEY environment variable must be set. Please set it in your .env file or environment. See .env.example for reference.")
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    def generate(self, prompt, system_prompt=None, max_tokens=16384, temperature=1, top_p=1, enable_reasoning=True):
        """
        Generate text using Nemotron LLM with reasoning support
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter
            enable_reasoning: Enable reasoning mode
        
        Returns:
            Generated text string
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            extra_body = {}
            if enable_reasoning:
                extra_body = {
                    "reasoning_budget": max_tokens,
                    "chat_template_kwargs": {"enable_thinking": True}
                }
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                extra_body=extra_body if enable_reasoning else None,
                stream=False
            )
            
            content = response.choices[0].message.content
            if content is None:
                logger.warning("Nemotron returned None content")
                return ""
            return content.strip()
        
        except Exception as e:
            logger.error(f"Error generating text with Nemotron: {e}")
            return f"Error: Unable to generate response. {str(e)}"
    
    def generate_streaming(self, prompt, system_prompt=None, max_tokens=16384, temperature=1, top_p=1, enable_reasoning=True):
        """
        Generate text with streaming support (for reasoning output)
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter
            enable_reasoning: Enable reasoning mode
        
        Yields:
            Tuple of (reasoning_content, content) strings
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            extra_body = {}
            if enable_reasoning:
                extra_body = {
                    "reasoning_budget": max_tokens,
                    "chat_template_kwargs": {"enable_thinking": True}
                }
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                extra_body=extra_body if enable_reasoning else None,
                stream=True
            )
            
            reasoning_content = ""
            content = ""
            
            for chunk in completion:
                reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                if reasoning:
                    reasoning_content += reasoning
                    yield (reasoning, None)
                
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content_chunk = chunk.choices[0].delta.content
                    content += content_chunk
                    yield (None, content_chunk)
        
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            yield (None, f"Error: {str(e)}")
    
    def generate_structured(self, prompt, system_prompt=None, format_instructions=None, temperature=0.3):
        """
        Generate structured output (e.g., JSON) with format instructions
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            format_instructions: Instructions for output format
            temperature: Lower temperature for more deterministic output
        
        Returns:
            Generated text (should be parsed as JSON if format_instructions provided)
        """
        full_prompt = prompt
        if format_instructions:
            full_prompt = f"{prompt}\n\nFormat your response as: {format_instructions}"
        
        return self.generate(full_prompt, system_prompt=system_prompt, temperature=temperature, enable_reasoning=True)
