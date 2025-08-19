"""Tests for Redis state management."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
import uuid
from datetime import datetime, timedelta


class TestRedisStateManager:
    """Test cases for Redis state management."""

    @pytest_asyncio.fixture
    async def redis_state_manager(self, mock_redis, mock_settings):
        """Create a Redis state manager instance."""
        from app.storage.redis_state import RedisStateManager
        return RedisStateManager(mock_settings, redis_client=mock_redis)

    @pytest_asyncio.fixture
    async def sample_conversation_state(self):
        """Sample conversation state for testing."""
        return {
            "conversation_id": str(uuid.uuid4()),
            "topic": "Climate change and renewable energy",
            "source": "hackernews",
            "status": "in_progress",
            "created_at": datetime.utcnow().isoformat(),
            "turns": [
                {
                    "turn_number": 1,
                    "model": "claude-3-sonnet",
                    "role": "assistant_1",
                    "content": "Climate change is one of the most pressing issues of our time.",
                    "timestamp": datetime.utcnow().isoformat(),
                    "latency_ms": 450,
                    "tokens": 50
                }
            ],
            "metadata": {
                "total_turns": 1,
                "total_tokens": 50,
                "duration_seconds": 0.45,
                "models_used": ["claude-3-sonnet"]
            }
        }

    async def test_save_conversation_state(self, redis_state_manager, sample_conversation_state, mock_redis):
        """Test saving conversation state to Redis."""
        conversation_id = sample_conversation_state["conversation_id"]
        
        result = await redis_state_manager.save_conversation_state(conversation_id, sample_conversation_state)
        
        assert result is True
        mock_redis.set.assert_called_once()
        
        # Check the Redis key format
        call_args = mock_redis.set.call_args
        expected_key = f"conversation:{conversation_id}"
        assert call_args[0][0] == expected_key
        
        # Check that data is JSON serialized
        saved_data = json.loads(call_args[0][1])
        assert saved_data["conversation_id"] == conversation_id
        
        # Check that TTL is set (24 hours)
        assert call_args[1]["ex"] == 86400

    async def test_get_conversation_state(self, redis_state_manager, sample_conversation_state, mock_redis):
        """Test retrieving conversation state from Redis."""
        conversation_id = sample_conversation_state["conversation_id"]
        mock_redis.get.return_value = json.dumps(sample_conversation_state).encode()
        
        result = await redis_state_manager.get_conversation_state(conversation_id)
        
        assert result is not None
        assert result["conversation_id"] == conversation_id
        assert result["topic"] == sample_conversation_state["topic"]
        
        # Check the Redis key format
        expected_key = f"conversation:{conversation_id}"
        mock_redis.get.assert_called_once_with(expected_key)

    async def test_get_nonexistent_conversation(self, redis_state_manager, mock_redis):
        """Test retrieving non-existent conversation state."""
        mock_redis.get.return_value = None
        
        result = await redis_state_manager.get_conversation_state("nonexistent-id")
        
        assert result is None

    async def test_update_conversation_state(self, redis_state_manager, sample_conversation_state, mock_redis):
        """Test updating existing conversation state."""
        conversation_id = sample_conversation_state["conversation_id"]
        mock_redis.get.return_value = json.dumps(sample_conversation_state).encode()
        
        # Add a new turn
        new_turn = {
            "turn_number": 2,
            "model": "gemini-pro",
            "role": "assistant_2",
            "content": "I agree, and renewable energy solutions are becoming more viable.",
            "timestamp": datetime.utcnow().isoformat(),
            "latency_ms": 380,
            "tokens": 45
        }
        
        result = await redis_state_manager.add_turn(conversation_id, new_turn)
        
        assert result is True
        
        # Should have called get to retrieve current state
        mock_redis.get.assert_called_once()
        
        # Should have called set to save updated state
        mock_redis.set.assert_called()
        
        # Check that the updated state includes the new turn
        updated_data = json.loads(mock_redis.set.call_args[0][1])
        assert len(updated_data["turns"]) == 2
        assert updated_data["turns"][1]["turn_number"] == 2
        assert updated_data["metadata"]["total_turns"] == 2

    async def test_delete_conversation_state(self, redis_state_manager, mock_redis):
        """Test deleting conversation state from Redis."""
        conversation_id = "test-conversation-123"
        
        result = await redis_state_manager.delete_conversation_state(conversation_id)
        
        assert result is True
        expected_key = f"conversation:{conversation_id}"
        mock_redis.delete.assert_called_once_with(expected_key)

    async def test_list_active_conversations(self, redis_state_manager, mock_redis):
        """Test listing all active conversations."""
        # Mock Redis keys response
        mock_redis.keys.return_value = [
            b"conversation:id1",
            b"conversation:id2",
            b"conversation:id3"
        ]
        
        result = await redis_state_manager.list_active_conversations()
        
        assert len(result) == 3
        assert "id1" in result
        assert "id2" in result
        assert "id3" in result
        
        mock_redis.keys.assert_called_once_with("conversation:*")

    async def test_conversation_state_expiry(self, redis_state_manager, sample_conversation_state, mock_redis):
        """Test that conversation states expire after TTL."""
        conversation_id = sample_conversation_state["conversation_id"]
        
        # Set TTL to 1 hour instead of default 24 hours
        await redis_state_manager.save_conversation_state(
            conversation_id, 
            sample_conversation_state, 
            ttl_seconds=3600
        )
        
        call_args = mock_redis.set.call_args
        assert call_args[1]["ex"] == 3600

    async def test_conversation_metrics_tracking(self, redis_state_manager, mock_redis):
        """Test tracking of conversation metrics."""
        metrics = {
            "total_conversations": 150,
            "active_conversations": 25,
            "completed_conversations": 125,
            "avg_turns_per_conversation": 7.5,
            "avg_duration_seconds": 45.2
        }
        
        await redis_state_manager.update_metrics(metrics)
        
        mock_redis.hset.assert_called_once_with("conversation:metrics", mapping=metrics)

    async def test_get_conversation_metrics(self, redis_state_manager, mock_redis):
        """Test retrieving conversation metrics."""
        mock_metrics = {
            b"total_conversations": b"150",
            b"active_conversations": b"25",
            b"avg_turns_per_conversation": b"7.5"
        }
        mock_redis.hgetall.return_value = mock_metrics
        
        result = await redis_state_manager.get_metrics()
        
        assert result["total_conversations"] == 150
        assert result["active_conversations"] == 25
        assert result["avg_turns_per_conversation"] == 7.5

    async def test_conversation_locking(self, redis_state_manager, mock_redis):
        """Test conversation locking for concurrent access."""
        conversation_id = "test-conversation-123"
        
        # Test acquiring lock
        mock_redis.set.return_value = True  # Lock acquired
        
        lock_acquired = await redis_state_manager.acquire_conversation_lock(conversation_id)
        
        assert lock_acquired is True
        
        # Check lock key format and expiry
        expected_lock_key = f"conversation:lock:{conversation_id}"
        mock_redis.set.assert_called_with(
            expected_lock_key, 
            "locked", 
            nx=True,  # Only set if not exists
            ex=30     # 30 second expiry
        )

    async def test_conversation_lock_timeout(self, redis_state_manager, mock_redis):
        """Test conversation lock timeout."""
        conversation_id = "test-conversation-123"
        
        # Lock already exists
        mock_redis.set.return_value = False
        
        lock_acquired = await redis_state_manager.acquire_conversation_lock(conversation_id)
        
        assert lock_acquired is False

    async def test_release_conversation_lock(self, redis_state_manager, mock_redis):
        """Test releasing conversation lock."""
        conversation_id = "test-conversation-123"
        
        result = await redis_state_manager.release_conversation_lock(conversation_id)
        
        assert result is True
        expected_lock_key = f"conversation:lock:{conversation_id}"
        mock_redis.delete.assert_called_once_with(expected_lock_key)

    async def test_topic_queue_operations(self, redis_state_manager, mock_redis):
        """Test operations on the topic queue from data ingestion service."""
        # Test getting topic from queue
        mock_topic = {
            "id": str(uuid.uuid4()),
            "title": "AI Ethics and Governance",
            "source": "hackernews",
            "url": "https://news.ycombinator.com/item?id=123456"
        }
        mock_redis.lpop.return_value = json.dumps(mock_topic).encode()
        
        result = await redis_state_manager.get_next_topic()
        
        assert result is not None
        assert result["title"] == "AI Ethics and Governance"
        mock_redis.lpop.assert_called_once_with("topics:queue")

    async def test_empty_topic_queue(self, redis_state_manager, mock_redis):
        """Test handling empty topic queue."""
        mock_redis.lpop.return_value = None
        
        result = await redis_state_manager.get_next_topic()
        
        assert result is None

    async def test_topic_queue_length(self, redis_state_manager, mock_redis):
        """Test checking topic queue length."""
        mock_redis.llen.return_value = 15
        
        length = await redis_state_manager.get_topic_queue_length()
        
        assert length == 15
        mock_redis.llen.assert_called_once_with("topics:queue")

    async def test_conversation_search(self, redis_state_manager, mock_redis):
        """Test searching conversations by topic or metadata."""
        # Mock search results
        mock_conversations = [
            {"conversation_id": "1", "topic": "AI in healthcare"},
            {"conversation_id": "2", "topic": "AI in education"}
        ]
        
        with patch.object(redis_state_manager, '_scan_conversations', return_value=mock_conversations):
            results = await redis_state_manager.search_conversations("AI")
            
            assert len(results) == 2
            assert all("AI" in conv["topic"] for conv in results)

    async def test_cleanup_expired_conversations(self, redis_state_manager, mock_redis):
        """Test cleanup of expired conversation states."""
        # Mock expired conversation keys
        expired_keys = [b"conversation:expired1", b"conversation:expired2"]
        mock_redis.keys.return_value = expired_keys
        mock_redis.ttl.return_value = -1  # Expired
        
        cleaned_count = await redis_state_manager.cleanup_expired_conversations()
        
        assert cleaned_count == 2
        assert mock_redis.delete.call_count == 2

    async def test_redis_connection_error_handling(self, redis_state_manager):
        """Test handling of Redis connection errors."""
        # Mock Redis connection error
        mock_redis_error = AsyncMock()
        mock_redis_error.get.side_effect = ConnectionError("Redis connection failed")
        
        redis_state_manager.redis_client = mock_redis_error
        
        result = await redis_state_manager.get_conversation_state("test-id")
        
        # Should handle error gracefully and return None
        assert result is None

    async def test_conversation_state_validation(self, redis_state_manager, mock_redis):
        """Test validation of conversation state before saving."""
        # Invalid conversation state (missing required fields)
        invalid_state = {
            "topic": "Test topic"
            # Missing conversation_id, turns, metadata
        }
        
        with pytest.raises(ValueError, match="Invalid conversation state"):
            await redis_state_manager.save_conversation_state("test-id", invalid_state)

    async def test_atomic_state_updates(self, redis_state_manager, sample_conversation_state, mock_redis):
        """Test atomic updates to conversation state."""
        conversation_id = sample_conversation_state["conversation_id"]
        mock_redis.get.return_value = json.dumps(sample_conversation_state).encode()
        
        # Simulate concurrent update using Redis transaction
        with patch.object(redis_state_manager, '_atomic_update') as mock_atomic:
            mock_atomic.return_value = True
            
            new_turn = {"turn_number": 2, "content": "New turn"}
            result = await redis_state_manager.add_turn_atomic(conversation_id, new_turn)
            
            assert result is True
            mock_atomic.assert_called_once()