"""Test configuration and fixtures for orchestration service tests."""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any
import uuid
from datetime import datetime


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.exists.return_value = False
    redis_mock.lpop.return_value = None
    return redis_mock


@pytest_asyncio.fixture
async def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    producer_mock = AsyncMock()
    producer_mock.send.return_value = asyncio.Future()
    producer_mock.send.return_value.set_result(MagicMock())
    producer_mock.start.return_value = None
    producer_mock.stop.return_value = None
    return producer_mock


@pytest_asyncio.fixture
async def mock_kafka_consumer():
    """Mock Kafka consumer for testing."""
    consumer_mock = AsyncMock()
    consumer_mock.start.return_value = None
    consumer_mock.stop.return_value = None
    consumer_mock.subscribe.return_value = None
    consumer_mock.__aiter__ = AsyncMock(return_value=iter([]))
    return consumer_mock


@pytest_asyncio.fixture
async def mock_anthropic_client():
    """Mock Anthropic LLM client for testing."""
    client_mock = AsyncMock()
    client_mock.generate_response.return_value = {
        "content": "This is a mock response from Claude.",
        "model": "claude-3-sonnet",
        "tokens": 50,
        "latency_ms": 450
    }
    return client_mock


@pytest_asyncio.fixture
async def mock_google_client():
    """Mock Google LLM client for testing."""
    client_mock = AsyncMock()
    client_mock.generate_response.return_value = {
        "content": "This is a mock response from Gemini.",
        "model": "gemini-pro",
        "tokens": 45,
        "latency_ms": 380
    }
    return client_mock


@pytest.fixture
def sample_conversation_topic():
    """Sample conversation topic for testing."""
    return {
        "id": str(uuid.uuid4()),
        "title": "Impact of AI on education",
        "source": "hackernews",
        "url": "https://news.ycombinator.com/item?id=123456",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_conversation_event():
    """Sample conversation event for testing."""
    conversation_id = str(uuid.uuid4())
    return {
        "conversation_id": conversation_id,
        "topic": "Impact of AI on education",
        "source": "hackernews",
        "turns": [
            {
                "turn_number": 1,
                "model": "claude-3-sonnet",
                "role": "assistant_1",
                "content": "AI is revolutionizing education by personalizing learning experiences.",
                "timestamp": "2024-01-01T00:00:00Z",
                "latency_ms": 450,
                "tokens": 50
            },
            {
                "turn_number": 2,
                "model": "gemini-pro",
                "role": "assistant_2",
                "content": "I agree, but we must also consider the challenges of AI bias in educational content.",
                "timestamp": "2024-01-01T00:00:01Z",
                "latency_ms": 380,
                "tokens": 45
            }
        ],
        "metadata": {
            "total_turns": 2,
            "total_tokens": 95,
            "duration_seconds": 1.5,
            "models_used": ["claude-3-sonnet", "gemini-pro"],
            "status": "in_progress"
        }
    }


@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    return {
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_password": None,
        "kafka_bootstrap_servers": "localhost:9092",
        "anthropic_api_key": "test-anthropic-key",
        "google_api_key": "test-google-key",
        "max_conversation_turns": 10,
        "conversation_timeout_seconds": 300,
        "rate_limit_requests_per_minute": 60
    }


@pytest.fixture
def mock_kafka_message():
    """Mock Kafka message for testing."""
    message_mock = MagicMock()
    message_mock.value = b'{"conversation_id": "test-id", "topic": "test topic"}'
    message_mock.topic = "conversation.new"
    message_mock.partition = 0
    message_mock.offset = 1
    message_mock.timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC
    return message_mock