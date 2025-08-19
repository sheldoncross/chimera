"""Anthropic Claude API client."""

import json
from typing import Dict, Any, List
import aiohttp
import logging

from .base_llm_client import BaseLLMClient
# Settings are handled dynamically

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic Claude API."""
    
    def __init__(self, settings):
        super().__init__(settings)
        # Handle both dict and Settings object
        if isinstance(settings, dict):
            self.api_key = settings.get("anthropic_api_key", "test-anthropic-key")
            self.model = settings.get("anthropic_model", "claude-3-sonnet-20240229")
        else:
            self.api_key = settings.anthropic_api_key
            self.model = settings.anthropic_model
        self.base_url = "https://api.anthropic.com/v1"
        
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
    
    def _format_messages(self, 
                        prompt: str, 
                        conversation_history: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """Format messages for Anthropic API."""
        messages = []
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = msg["role"]
                # Map assistant_1/assistant_2 to assistant
                if role.startswith("assistant"):
                    role = "assistant"
                
                messages.append({
                    "role": role,
                    "content": msg["content"]
                })
        
        # Add the new prompt as user message
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    async def _make_request(self, 
                           prompt: str, 
                           conversation_history: List[Dict[str, str]] = None,
                           **kwargs) -> Dict[str, Any]:
        """Make request to Anthropic API."""
        messages = self._format_messages(prompt, conversation_history)
        
        # Prepare request data
        request_data = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.7),
            "messages": messages
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        logger.debug(f"Making Anthropic API request: {json.dumps(request_data, indent=2)}")
        
        async with self.session.post(
            f"{self.base_url}/messages",
            json=request_data,
            headers=headers
        ) as response:
            response_data = await response.json()
            
            if response.status != 200:
                error_msg = response_data.get("error", {}).get("message", "Unknown error")
                if response.status == 429:
                    raise Exception(f"Rate limit exceeded: {error_msg}")
                elif response.status == 400:
                    raise Exception(f"Bad request: {error_msg}")
                elif response.status == 401:
                    raise Exception(f"Authentication failed: {error_msg}")
                else:
                    raise Exception(f"API error {response.status}: {error_msg}")
            
            # Extract response content
            content = ""
            if "content" in response_data:
                for block in response_data["content"]:
                    if block.get("type") == "text":
                        content += block.get("text", "")
            
            # Calculate tokens
            usage = response_data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens
            
            # Map model name to our simplified format
            model_name = "claude-3-sonnet"
            if "haiku" in self.model.lower():
                model_name = "claude-3-haiku"
            elif "opus" in self.model.lower():
                model_name = "claude-3-opus"
            
            return {
                "content": content,
                "model": model_name,
                "tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check with a simple request."""
        try:
            response = await self.generate_response(
                "Hello, this is a health check.",
                conversation_history=[]
            )
            return {
                "healthy": True,
                "latency_ms": response.get("latency_ms"),
                "model": response.get("model"),
                "circuit_breaker_open": self._circuit_breaker_open
            }
        except Exception as e:
            logger.error(f"Anthropic health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
                "circuit_breaker_open": self._circuit_breaker_open
            }