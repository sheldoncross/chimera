"""Tests for LLM clients."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import asyncio
from tenacity import RetryError


class TestBaseLLMClient:
    """Test cases for the base LLM client."""

    @pytest_asyncio.fixture
    async def base_client(self, mock_settings):
        """Create a base LLM client instance."""
        from app.clients.base_llm_client import BaseLLMClient
        return BaseLLMClient(mock_settings)

    async def test_rate_limiting(self, base_client):
        """Test that rate limiting is properly enforced."""
        # This test defines the expected rate limiting behavior
        # The implementation should prevent too many requests per minute
        with patch('time.time', side_effect=[0, 0.5, 1.0, 1.5]):  # 4 requests in 1.5 seconds
            # First 3 requests should succeed (under rate limit)
            for _ in range(3):
                result = await base_client._check_rate_limit()
                assert result is True
            
            # 4th request should be rate limited
            result = await base_client._check_rate_limit()
            assert result is False

    async def test_retry_on_failure(self, base_client):
        """Test retry logic with exponential backoff."""
        # This test ensures the client retries on failures
        with patch.object(base_client, '_make_request') as mock_request:
            # First two calls fail, third succeeds
            mock_request.side_effect = [
                aiohttp.ClientError("Network error"),
                aiohttp.ClientError("Network error"),
                {"content": "Success"}
            ]
            
            result = await base_client.generate_response("test prompt")
            
            assert mock_request.call_count == 3
            assert result["content"] == "Success"

    async def test_max_retries_exceeded(self, base_client):
        """Test behavior when max retries are exceeded."""
        with patch.object(base_client, '_make_request') as mock_request:
            mock_request.side_effect = aiohttp.ClientError("Persistent error")
            
            with pytest.raises(RetryError):
                await base_client.generate_response("test prompt")

    async def test_circuit_breaker_pattern(self, base_client):
        """Test circuit breaker functionality."""
        # After multiple failures, circuit should open
        with patch.object(base_client, '_make_request') as mock_request:
            mock_request.side_effect = aiohttp.ClientError("Service down")
            
            # Trigger multiple failures to open circuit
            for _ in range(5):
                try:
                    await base_client.generate_response("test prompt")
                except:
                    pass
            
            # Circuit should now be open
            assert base_client._circuit_breaker_open is True
            
            # Next request should fail fast without actual HTTP call
            with pytest.raises(Exception, match="Circuit breaker"):
                await base_client.generate_response("test prompt")


class TestAnthropicClient:
    """Test cases for Anthropic (Claude) client."""

    @pytest_asyncio.fixture
    async def anthropic_client(self, mock_settings):
        """Create an Anthropic client instance."""
        from app.clients.anthropic_client import AnthropicClient
        mock_settings["anthropic_api_key"] = "test-anthropic-key"
        return AnthropicClient(mock_settings)

    async def test_successful_request(self, anthropic_client):
        """Test successful API request to Anthropic."""
        mock_response = {
            "content": [{"text": "This is Claude's response."}],
            "model": "claude-3-sonnet-20240229",
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await anthropic_client.generate_response(
                "What are the benefits of renewable energy?",
                conversation_history=[]
            )
            
            assert result["content"] == "This is Claude's response."
            assert result["model"] == "claude-3-sonnet"
            assert result["tokens"] == 30  # input + output tokens
            assert "latency_ms" in result

    async def test_request_formatting(self, anthropic_client):
        """Test that requests are properly formatted for Anthropic API."""
        conversation_history = [
            {"role": "assistant", "content": "Previous message"},
            {"role": "user", "content": "User response"}
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "content": [{"text": "Response"}],
                "model": "claude-3-sonnet-20240229",
                "usage": {"input_tokens": 5, "output_tokens": 5}
            })
            mock_post.return_value.__aenter__.return_value.status = 200
            
            await anthropic_client.generate_response(
                "New message",
                conversation_history=conversation_history
            )
            
            # Check the request was formatted correctly
            call_args = mock_post.call_args
            request_data = call_args[1]["json"]
            
            assert "messages" in request_data
            assert len(request_data["messages"]) == 3  # history + new message
            assert request_data["model"] == "claude-3-sonnet-20240229"
            assert request_data["max_tokens"] > 0

    async def test_error_handling(self, anthropic_client):
        """Test error handling for Anthropic API errors."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 429  # Rate limited
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "error": {"message": "Rate limit exceeded"}
            })
            
            with pytest.raises(Exception, match="Rate limit"):
                await anthropic_client.generate_response("test prompt")

    async def test_token_counting(self, anthropic_client):
        """Test accurate token counting from API response."""
        mock_response = {
            "content": [{"text": "Response"}],
            "model": "claude-3-sonnet-20240229",
            "usage": {"input_tokens": 15, "output_tokens": 25}
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await anthropic_client.generate_response("test")
            
            assert result["tokens"] == 40  # 15 + 25


class TestGoogleClient:
    """Test cases for Google (Gemini) client."""

    @pytest_asyncio.fixture
    async def google_client(self, mock_settings):
        """Create a Google client instance."""
        from app.clients.google_client import GoogleClient
        mock_settings["google_api_key"] = "test-google-key"
        return GoogleClient(mock_settings)

    async def test_successful_request(self, google_client):
        """Test successful API request to Google Gemini."""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "This is Gemini's response."}]
                },
                "finishReason": "STOP"
            }],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 18,
                "totalTokenCount": 30
            }
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            result = await google_client.generate_response(
                "What are the challenges in AI development?",
                conversation_history=[]
            )
            
            assert result["content"] == "This is Gemini's response."
            assert result["model"] == "gemini-pro"
            assert result["tokens"] == 30
            assert "latency_ms" in result

    async def test_conversation_history_formatting(self, google_client):
        """Test that conversation history is properly formatted for Gemini."""
        conversation_history = [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Hi there"}
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "candidates": [{"content": {"parts": [{"text": "Response"}]}}],
                "usageMetadata": {"totalTokenCount": 10}
            })
            mock_post.return_value.__aenter__.return_value.status = 200
            
            await google_client.generate_response(
                "New message",
                conversation_history=conversation_history
            )
            
            call_args = mock_post.call_args
            request_data = call_args[1]["json"]
            
            assert "contents" in request_data
            # Google uses different role names
            assert request_data["contents"][0]["role"] == "model"  # assistant -> model
            assert request_data["contents"][1]["role"] == "user"

    async def test_safety_filtering_response(self, google_client):
        """Test handling of safety-filtered responses from Gemini."""
        mock_response = {
            "candidates": [{
                "finishReason": "SAFETY",
                "safetyRatings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "probability": "HIGH"}
                ]
            }]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aenter__.return_value.status = 200
            
            with pytest.raises(Exception, match="safety"):
                await google_client.generate_response("inappropriate prompt")

    async def test_quota_exceeded_handling(self, google_client):
        """Test handling of quota exceeded errors."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 429
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={
                "error": {
                    "code": 429,
                    "message": "Quota exceeded"
                }
            })
            
            with pytest.raises(Exception, match="Quota"):
                await google_client.generate_response("test prompt")


class TestLLMClientFactory:
    """Test cases for LLM client factory pattern."""

    @pytest_asyncio.fixture
    async def client_factory(self, mock_settings):
        """Create a client factory instance."""
        from app.clients.base_llm_client import LLMClientFactory
        return LLMClientFactory(mock_settings)

    async def test_create_anthropic_client(self, client_factory):
        """Test creation of Anthropic client."""
        client = await client_factory.create_client("anthropic")
        assert client.__class__.__name__ == "AnthropicClient"

    async def test_create_google_client(self, client_factory):
        """Test creation of Google client."""
        client = await client_factory.create_client("google")
        assert client.__class__.__name__ == "GoogleClient"

    async def test_invalid_client_type(self, client_factory):
        """Test error handling for invalid client types."""
        with pytest.raises(ValueError, match="Unknown client type"):
            await client_factory.create_client("invalid_client")

    async def test_client_caching(self, client_factory):
        """Test that clients are cached and reused."""
        client1 = await client_factory.create_client("anthropic")
        client2 = await client_factory.create_client("anthropic")
        
        # Should return the same instance
        assert client1 is client2

    async def test_health_check(self, client_factory):
        """Test health check functionality for all clients."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={})
            
            health_status = await client_factory.health_check_all()
            
            assert "anthropic" in health_status
            assert "google" in health_status
            assert all(status["healthy"] for status in health_status.values())