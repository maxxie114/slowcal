"""
Nemotron LLM client wrapper using OpenAI-compatible interface
"""

from openai import OpenAI
from .config import Config
import logging

logger = logging.getLogger(__name__)

class NemotronClient:
    """Client for interacting with Nemotron LLM via OpenAI-compatible API"""
    
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = base_url or Config.NEMOTRON_BASE_URL
        self.api_key = api_key or Config.NEMOTRON_API_KEY
        self.model = model or Config.NEMOTRON_MODEL
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    def generate(self, prompt, system_prompt=None, max_tokens=1000, temperature=0.7):
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
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Error generating text with Nemotron: {e}")
            return f"Error: Unable to generate response. {str(e)}"
    
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
