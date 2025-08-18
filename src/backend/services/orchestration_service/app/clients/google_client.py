"""Google Gemini API client."""

import json
from typing import Dict, Any, List
import aiohttp
import logging

from .base_llm_client import BaseLLMClient
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class GoogleClient(BaseLLMClient):
    """Client for Google Gemini API."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.api_key = settings.google_api_key
        self.model = settings.google_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        if not self.api_key:
            raise ValueError("Google API key is required")
    
    def _format_messages(self, 
                        prompt: str, 
                        conversation_history: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Format messages for Google Gemini API."""
        contents = []
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = msg["role"]
                # Map roles for Google API
                if role.startswith("assistant"):
                    role = "model"  # Google uses "model" instead of "assistant"
                elif role == "system":
                    role = "user"  # Google doesn't have system role, map to user
                
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
        
        # Add the new prompt as user message
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        return contents
    
    async def _make_request(self, 
                           prompt: str, 
                           conversation_history: List[Dict[str, str]] = None,
                           **kwargs) -> Dict[str, Any]:
        """Make request to Google Gemini API."""
        contents = self._format_messages(prompt, conversation_history)
        
        # Prepare request data
        request_data = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40)
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }
        
        url = f"{self.base_url}/models/{self.model}:generateContent"
        params = {"key": self.api_key}
        
        headers = {
            "Content-Type": "application/json"
        }
        
        logger.debug(f"Making Google API request: {json.dumps(request_data, indent=2)}")
        
        async with self.session.post(
            url,
            json=request_data,
            headers=headers,
            params=params
        ) as response:
            response_data = await response.json()
            
            if response.status != 200:
                error_msg = response_data.get("error", {}).get("message", "Unknown error")
                error_code = response_data.get("error", {}).get("code", response.status)
                
                if response.status == 429 or error_code == 429:
                    raise Exception(f"Quota exceeded: {error_msg}")
                elif response.status == 400:
                    raise Exception(f"Bad request: {error_msg}")
                elif response.status == 403:
                    raise Exception(f"Permission denied: {error_msg}")
                else:
                    raise Exception(f"API error {response.status}: {error_msg}")
            
            # Check for safety filtering
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise Exception("No candidates returned from API")
            
            candidate = candidates[0]
            finish_reason = candidate.get("finishReason")
            
            if finish_reason == "SAFETY":
                safety_ratings = candidate.get("safetyRatings", [])
                safety_issues = [
                    rating["category"] for rating in safety_ratings 
                    if rating.get("probability") in ["HIGH", "MEDIUM"]
                ]
                raise Exception(f"Content filtered for safety: {', '.join(safety_issues)}")
            
            # Extract content
            content = ""
            if "content" in candidate:
                parts = candidate["content"].get("parts", [])
                for part in parts:
                    if "text" in part:
                        content += part["text"]
            
            if not content:
                raise Exception("Empty response from API")
            
            # Calculate tokens
            usage_metadata = response_data.get("usageMetadata", {})
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            candidate_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", prompt_tokens + candidate_tokens)
            
            return {
                "content": content,
                "model": "gemini-pro",
                "tokens": total_tokens,
                "input_tokens": prompt_tokens,
                "output_tokens": candidate_tokens,
                "finish_reason": finish_reason
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
            logger.error(f"Google health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
                "circuit_breaker_open": self._circuit_breaker_open
            }