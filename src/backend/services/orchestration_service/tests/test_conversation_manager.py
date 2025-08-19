"""Tests for the conversation manager."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
import uuid
from datetime import datetime, timedelta


class TestConversationManager:
    """Test cases for ConversationManager class."""

    @pytest_asyncio.fixture
    async def conversation_manager(self, mock_redis, mock_kafka_producer, mock_anthropic_client, mock_google_client, mock_settings):
        """Create a ConversationManager instance with mocked dependencies."""
        from app.workers.conversation_manager import ConversationManager
        
        manager = ConversationManager(
            redis_client=mock_redis,
            kafka_producer=mock_kafka_producer,
            llm_clients={
                "anthropic": mock_anthropic_client,
                "google": mock_google_client
            },
            settings=mock_settings
        )
        return manager

    @pytest_asyncio.fixture
    async def sample_topic(self):
        """Sample topic data from Redis."""
        return {
            "id": str(uuid.uuid4()),
            "title": "The future of renewable energy technology",
            "source": "hackernews",
            "url": "https://news.ycombinator.com/item?id=123456"
        }

    async def test_start_new_conversation(self, conversation_manager, sample_topic, mock_kafka_producer):
        """Test starting a new conversation from a topic."""
        # Act
        conversation_id = await conversation_manager.start_new_conversation(sample_topic)
        
        # Assert
        assert conversation_id is not None
        assert isinstance(conversation_id, str)
        # Should send conversation.new event to Kafka
        mock_kafka_producer.send.assert_called_once()
        call_args = mock_kafka_producer.send.call_args
        assert call_args[1]["topic"] == "conversation.new"
        
        # Check the event structure
        event_data = json.loads(call_args[1]["value"])
        assert event_data["conversation_id"] == conversation_id
        assert event_data["topic"] == sample_topic["title"]
        assert event_data["source"] == sample_topic["source"]

    async def test_process_conversation_turn(self, conversation_manager, sample_conversation_event, mock_redis, mock_anthropic_client):
        """Test processing a single conversation turn."""
        # Arrange
        conversation_id = sample_conversation_event["conversation_id"]
        mock_redis.get.return_value = json.dumps(sample_conversation_event).encode()
        
        # Act
        result = await conversation_manager.process_conversation_turn(conversation_id, "anthropic")
        
        # Assert
        assert result is not None
        assert result["success"] is True
        mock_anthropic_client.generate_response.assert_called_once()
        
        # Should update conversation state in Redis
        mock_redis.set.assert_called()
        
        # Should send turn event to Kafka
        conversation_manager.kafka_producer.send.assert_called()

    async def test_conversation_alternates_between_models(self, conversation_manager, sample_topic):
        """Test that conversation alternates between different LLM models."""
        # Arrange
        conversation_id = await conversation_manager.start_new_conversation(sample_topic)
        
        # Act - Process multiple turns
        turn1_result = await conversation_manager.process_conversation_turn(conversation_id, "anthropic")
        turn2_result = await conversation_manager.process_conversation_turn(conversation_id, "google")
        
        # Assert
        assert turn1_result["model"] == "anthropic"
        assert turn2_result["model"] == "google"

    async def test_conversation_reaches_max_turns(self, conversation_manager, sample_conversation_event, mock_redis, mock_kafka_producer):
        """Test that conversation completes when reaching maximum turns."""
        # Arrange
        # Create a conversation with near-max turns
        sample_conversation_event["metadata"]["total_turns"] = 9  # Max is 10
        sample_conversation_event["turns"] = [{"turn_number": i} for i in range(1, 10)]
        mock_redis.get.return_value = json.dumps(sample_conversation_event).encode()
        
        conversation_id = sample_conversation_event["conversation_id"]
        
        # Act
        result = await conversation_manager.process_conversation_turn(conversation_id, "anthropic")
        
        # Assert
        assert result["completed"] is True
        
        # Should send conversation.completed event
        completed_call = None
        for call in mock_kafka_producer.send.call_args_list:
            if call[1]["topic"] == "conversation.completed":
                completed_call = call
                break
        
        assert completed_call is not None
        completed_event = json.loads(completed_call[1]["value"])
        assert completed_event["conversation_id"] == conversation_id
        assert completed_event["metadata"]["total_turns"] == 10

    async def test_conversation_timeout_handling(self, conversation_manager, sample_conversation_event, mock_redis):
        """Test handling of conversation timeouts."""
        # Arrange
        # Set conversation timestamp to be older than timeout
        old_timestamp = datetime.utcnow() - timedelta(seconds=400)  # 400 seconds ago
        sample_conversation_event["turns"][0]["timestamp"] = old_timestamp.isoformat()
        mock_redis.get.return_value = json.dumps(sample_conversation_event).encode()
        
        conversation_id = sample_conversation_event["conversation_id"]
        
        # Act
        result = await conversation_manager.process_conversation_turn(conversation_id, "anthropic")
        
        # Assert
        assert result["completed"] is True
        assert result["reason"] == "timeout"

    async def test_llm_client_error_handling(self, conversation_manager, sample_conversation_event, mock_redis, mock_anthropic_client):
        """Test handling of LLM client errors with retries."""
        # Arrange
        mock_redis.get.return_value = json.dumps(sample_conversation_event).encode()
        mock_anthropic_client.generate_response.side_effect = Exception("API Error")
        
        conversation_id = sample_conversation_event["conversation_id"]
        
        # Act
        result = await conversation_manager.process_conversation_turn(conversation_id, "anthropic")
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        # Should have attempted retries
        assert mock_anthropic_client.generate_response.call_count > 1

    async def test_conversation_state_persistence(self, conversation_manager, sample_topic, mock_redis):
        """Test that conversation state is properly persisted to Redis."""
        # Act
        conversation_id = await conversation_manager.start_new_conversation(sample_topic)
        
        # Assert
        # Should save initial conversation state
        mock_redis.set.assert_called()
        
        # Check that TTL is set (24 hours)
        set_calls = [call for call in mock_redis.set.call_args_list if call[0][0].endswith(conversation_id)]
        assert len(set_calls) > 0
        
        # Should include TTL parameter
        ttl_call = None
        for call in mock_redis.set.call_args_list:
            if "ex" in call[1]:  # TTL parameter
                ttl_call = call
                break
        assert ttl_call is not None
        assert ttl_call[1]["ex"] == 86400  # 24 hours

    async def test_get_conversation_state(self, conversation_manager, sample_conversation_event, mock_redis):
        """Test retrieving conversation state from Redis."""
        # Arrange
        conversation_id = sample_conversation_event["conversation_id"]
        mock_redis.get.return_value = json.dumps(sample_conversation_event).encode()
        
        # Act
        state = await conversation_manager.get_conversation_state(conversation_id)
        
        # Assert
        assert state is not None
        assert state["conversation_id"] == conversation_id
        assert state["topic"] == sample_conversation_event["topic"]
        assert len(state["turns"]) == len(sample_conversation_event["turns"])

    async def test_natural_conversation_ending_detection(self, conversation_manager, mock_redis, mock_anthropic_client):
        """Test detection of natural conversation endings."""
        # Arrange
        conversation_with_ending = {
            "conversation_id": str(uuid.uuid4()),
            "topic": "Test topic",
            "turns": [
                {
                    "turn_number": 3,
                    "content": "Thank you for this insightful discussion. I think we've covered the key points comprehensively.",
                    "model": "claude-3-sonnet"
                }
            ],
            "metadata": {"total_turns": 3}
        }
        mock_redis.get.return_value = json.dumps(conversation_with_ending).encode()
        mock_anthropic_client.generate_response.return_value = {
            "content": "Indeed, this has been a great conversation. I believe we've reached a natural conclusion.",
            "model": "claude-3-sonnet",
            "tokens": 20,
            "latency_ms": 300
        }
        
        # Act
        result = await conversation_manager.process_conversation_turn(
            conversation_with_ending["conversation_id"], 
            "anthropic"
        )
        
        # Assert
        assert result.get("natural_ending_detected") is True

    async def test_repetition_detection(self, conversation_manager, mock_redis):
        """Test detection of repetitive responses that should end conversation."""
        # Arrange
        repetitive_conversation = {
            "conversation_id": str(uuid.uuid4()),
            "topic": "Test topic",
            "turns": [
                {"content": "I think AI will transform education.", "model": "claude-3-sonnet"},
                {"content": "Yes, AI will definitely change education.", "model": "gemini-pro"},
                {"content": "Absolutely, AI transformation in education is inevitable.", "model": "claude-3-sonnet"},
            ],
            "metadata": {"total_turns": 3}
        }
        mock_redis.get.return_value = json.dumps(repetitive_conversation).encode()
        
        # Act
        result = await conversation_manager.detect_repetition(repetitive_conversation["conversation_id"])
        
        # Assert
        assert result["repetition_detected"] is True

    async def test_concurrent_conversation_processing(self, conversation_manager, sample_topic):
        """Test that multiple conversations can be processed concurrently."""
        # Act
        conversation_ids = await asyncio.gather(*[
            conversation_manager.start_new_conversation(sample_topic)
            for _ in range(5)
        ])
        
        # Assert
        assert len(conversation_ids) == 5
        assert len(set(conversation_ids)) == 5  # All unique

    async def test_conversation_metrics_collection(self, conversation_manager, sample_conversation_event, mock_redis):
        """Test that conversation metrics are properly collected."""
        # Arrange
        mock_redis.get.return_value = json.dumps(sample_conversation_event).encode()
        conversation_id = sample_conversation_event["conversation_id"]
        
        # Act
        result = await conversation_manager.process_conversation_turn(conversation_id, "anthropic")
        
        # Assert
        # Should collect latency, token count, and other metrics
        assert "latency_ms" in result
        assert "tokens" in result
        
        # Metrics should be included in the updated conversation state
        updated_conversation = json.loads(mock_redis.set.call_args[0][1])
        last_turn = updated_conversation["turns"][-1]
        assert "latency_ms" in last_turn
        assert "tokens" in last_turn