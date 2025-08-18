"""Base LLM client with retry logic and rate limiting."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import aiohttp
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class BaseLLMClient(ABC):
    """Base class for LLM API clients with retry logic and rate limiting."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_tokens = []
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = 0
        self._circuit_breaker_open = False
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    async def start(self):
        """Start the client session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def stop(self):
        """Stop the client session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits."""
        current_time = time.time()
        window_start = current_time - self.settings.rate_limit_window_seconds
        
        # Remove old tokens
        self._rate_limit_tokens = [
            token_time for token_time in self._rate_limit_tokens 
            if token_time > window_start
        ]
        
        # Check if we're under the limit
        if len(self._rate_limit_tokens) >= self.settings.rate_limit_requests_per_minute:
            return False
        
        # Add current request token
        self._rate_limit_tokens.append(current_time)
        return True
    
    def _check_circuit_breaker(self):
        """Check circuit breaker status."""
        current_time = time.time()
        
        # If circuit breaker timeout has passed, reset
        if (self._circuit_breaker_open and 
            current_time - self._circuit_breaker_last_failure > self.settings.circuit_breaker_timeout_seconds):
            self._circuit_breaker_open = False
            self._circuit_breaker_failures = 0
            logger.info("Circuit breaker reset")
        
        if self._circuit_breaker_open:
            raise CircuitBreakerError("Circuit breaker is open")
    
    def _record_failure(self):
        """Record a failure for circuit breaker."""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()
        
        if self._circuit_breaker_failures >= self.settings.circuit_breaker_failure_threshold:
            self._circuit_breaker_open = True
            logger.warning(f"Circuit breaker opened after {self._circuit_breaker_failures} failures")
    
    def _record_success(self):
        """Record a success for circuit breaker."""
        self._circuit_breaker_failures = 0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True
    )
    async def generate_response(self, 
                              prompt: str, 
                              conversation_history: List[Dict[str, str]] = None,
                              **kwargs) -> Dict[str, Any]:
        """Generate response from LLM with retry logic."""
        try:
            # Check rate limiting
            if not self._check_rate_limit():
                raise Exception("Rate limit exceeded")
            
            # Check circuit breaker
            self._check_circuit_breaker()
            
            # Ensure session is started
            if not self.session:
                await self.start()
            
            start_time = time.time()
            
            # Make the actual request
            response = await self._make_request(prompt, conversation_history, **kwargs)
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            # Record success
            self._record_success()
            
            # Add latency to response
            response["latency_ms"] = latency_ms
            
            return response
            
        except Exception as e:
            # Record failure
            self._record_failure()
            logger.error(f"LLM request failed: {str(e)}")
            raise
    
    @abstractmethod
    async def _make_request(self, 
                           prompt: str, 
                           conversation_history: List[Dict[str, str]] = None,
                           **kwargs) -> Dict[str, Any]:
        """Make the actual API request. To be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _format_messages(self, 
                        prompt: str, 
                        conversation_history: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
        """Format messages for the specific API. To be implemented by subclasses."""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the LLM service."""
        try:
            # Try a simple request
            response = await self.generate_response("Hello", conversation_history=[])
            return {
                "healthy": True,
                "latency_ms": response.get("latency_ms"),
                "circuit_breaker_open": self._circuit_breaker_open
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "circuit_breaker_open": self._circuit_breaker_open
            }


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._clients: Dict[str, BaseLLMClient] = {}
    
    async def create_client(self, client_type: str) -> BaseLLMClient:
        """Create or get cached LLM client."""
        if client_type in self._clients:
            return self._clients[client_type]
        
        if client_type == "anthropic":
            from .anthropic_client import AnthropicClient
            client = AnthropicClient(self.settings)
        elif client_type == "google":
            from .google_client import GoogleClient
            client = GoogleClient(self.settings)
        else:
            raise ValueError(f"Unknown client type: {client_type}")
        
        await client.start()
        self._clients[client_type] = client
        return client
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all clients."""
        results = {}
        
        for client_type in ["anthropic", "google"]:
            try:
                client = await self.create_client(client_type)
                results[client_type] = await client.health_check()
            except Exception as e:
                results[client_type] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return results
    
    async def stop_all(self):
        """Stop all clients."""
        for client in self._clients.values():
            await client.stop()
        self._clients.clear()