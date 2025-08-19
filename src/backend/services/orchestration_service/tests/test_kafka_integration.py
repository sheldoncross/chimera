"""Tests for Kafka integration components."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio
from aiokafka.errors import KafkaError


class TestKafkaProducer:
    """Test cases for Kafka producer."""

    @pytest_asyncio.fixture
    async def kafka_producer(self, mock_settings):
        """Create a Kafka producer instance."""
        from app.kafka.producer import KafkaProducer
        return KafkaProducer(mock_settings)

    async def test_producer_initialization(self, kafka_producer):
        """Test that producer initializes correctly."""
        assert kafka_producer.bootstrap_servers == "localhost:9092"
        assert kafka_producer._producer is None  # Not started yet

    async def test_producer_start_stop(self, kafka_producer):
        """Test producer start and stop lifecycle."""
        # TODO: FAILING - KafkaConnectionError when trying to connect to localhost:9092
        # TODO: Fix by properly mocking AIOKafkaProducer in the producer module import
        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            # Test start
            await kafka_producer.start()
            mock_producer.start.assert_called_once()
            assert kafka_producer._producer is not None
            
            # Test stop
            await kafka_producer.stop()
            mock_producer.stop.assert_called_once()

    async def test_send_event_success(self, kafka_producer):
        """Test successful event publishing."""
        # TODO: FAILING - Patch needs to target the correct import path: 'app.kafka.producer.AIOKafkaProducer'
        # TODO: Fix by using patch('app.kafka.producer.AIOKafkaProducer') instead
        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_producer.start()
            
            event_data = {"conversation_id": "test-123", "topic": "AI in education"}
            
            # Test sending event
            result = await kafka_producer.send_event("conversation.new", event_data)
            
            assert result is True
            mock_producer.send.assert_called_once()
            
            # Check the call arguments
            call_args = mock_producer.send.call_args
            assert call_args[0][0] == "conversation.new"  # topic
            assert json.loads(call_args[0][1]) == event_data  # serialized data

    async def test_send_event_with_key(self, kafka_producer):
        """Test sending event with partition key."""
        # TODO: FAILING - Same issue as test_send_event_success
        # TODO: Fix by properly mocking AIOKafkaProducer import path
        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_producer.start()
            
            event_data = {"conversation_id": "test-123"}
            partition_key = "test-123"
            
            await kafka_producer.send_event("conversation.turn", event_data, key=partition_key)
            
            call_args = mock_producer.send.call_args
            assert call_args[1]["key"] == partition_key.encode()

    async def test_send_event_failure_retry(self, kafka_producer):
        """Test retry logic on send failures."""
        # TODO: FAILING - Mock path issue + need to properly mock producer.send side_effect
        # TODO: Fix by mocking correct path and ensuring KafkaError is properly raised
        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            # First attempt fails, second succeeds
            mock_producer.send.side_effect = [
                KafkaError("Network error"),
                AsyncMock()
            ]
            
            await kafka_producer.start()
            
            result = await kafka_producer.send_event("test.topic", {"data": "test"})
            
            assert result is True
            assert mock_producer.send.call_count == 2

    async def test_send_event_max_retries_exceeded(self, kafka_producer):
        """Test behavior when max retries are exceeded."""
        # TODO: FAILING - Same mock path issue as other send tests
        # TODO: Fix by mocking correct import path and side_effect
        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            mock_producer.send.side_effect = KafkaError("Persistent error")
            
            await kafka_producer.start()
            
            result = await kafka_producer.send_event("test.topic", {"data": "test"})
            
            assert result is False
            assert mock_producer.send.call_count >= 3  # Default max retries

    async def test_batch_send_events(self, kafka_producer):
        """Test sending multiple events in batch."""
        # TODO: FAILING - Same mock path issue affecting all producer tests
        # TODO: Fix by correctly mocking AIOKafkaProducer import
        with patch('app.kafka.producer.AIOKafkaProducer') as mock_producer_class:
            mock_producer = AsyncMock()
            mock_producer_class.return_value = mock_producer
            
            await kafka_producer.start()
            
            events = [
                ("conversation.new", {"id": "1"}),
                ("conversation.turn", {"id": "2"}),
                ("conversation.response", {"id": "3"})
            ]
            
            results = await kafka_producer.send_batch(events)
            
            assert len(results) == 3
            assert all(results)
            assert mock_producer.send.call_count == 3


class TestKafkaConsumer:
    """Test cases for Kafka consumer."""

    @pytest_asyncio.fixture
    async def kafka_consumer(self, mock_settings):
        """Create a Kafka consumer instance."""
        from app.kafka.consumer import KafkaConsumer
        return KafkaConsumer(mock_settings, group_id="test-group")

    async def test_consumer_initialization(self, kafka_consumer):
        """Test that consumer initializes correctly."""
        assert kafka_consumer.group_id == "test-group"
        assert kafka_consumer.bootstrap_servers == "localhost:9092"

    async def test_consumer_start_stop(self, kafka_consumer):
        """Test consumer start and stop lifecycle."""
        # TODO: FAILING - Same issue as producer - mock path needs to be 'app.kafka.consumer.AIOKafkaConsumer'
        # TODO: Fix by patching the correct import path in consumer module
        with patch('app.kafka.consumer.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_consumer.start()
            mock_consumer.start.assert_called_once()
            
            await kafka_consumer.stop()
            mock_consumer.stop.assert_called_once()

    async def test_subscribe_to_topics(self, kafka_consumer):
        """Test subscribing to multiple topics."""
        # TODO: FAILING - Mock path issue - AIOKafkaConsumer not being mocked correctly
        # TODO: Fix by patching 'app.kafka.consumer.AIOKafkaConsumer'
        with patch('app.kafka.consumer.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_consumer.start()
            
            topics = ["conversation.new", "conversation.turn"]
            await kafka_consumer.subscribe(topics)
            
            mock_consumer.subscribe.assert_called_once_with(topics)

    async def test_consume_messages(self, kafka_consumer):
        """Test consuming messages from topics."""
        # TODO: FAILING - Mock path + async iteration setup issues
        # TODO: Fix mocking path and properly setup __aiter__ for async iteration
        with patch('app.kafka.consumer.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            # Mock messages
            mock_message1 = MagicMock()
            mock_message1.topic = "conversation.new"
            mock_message1.value = b'{"conversation_id": "123", "topic": "AI"}'
            mock_message1.key = b"123"
            mock_message1.offset = 1
            
            mock_message2 = MagicMock()
            mock_message2.topic = "conversation.turn"
            mock_message2.value = b'{"turn": 1}'
            mock_message2.key = None
            mock_message2.offset = 2
            
            # Configure async iteration
            async def mock_iter():
                yield mock_message1
                yield mock_message2
            
            mock_consumer.__aiter__ = lambda self: mock_iter()
            
            await kafka_consumer.start()
            await kafka_consumer.subscribe(["conversation.new", "conversation.turn"])
            
            # Consume messages
            messages = []
            async for message in kafka_consumer:
                messages.append(message)
                if len(messages) >= 2:
                    break
            
            assert len(messages) == 2
            assert messages[0].topic == "conversation.new"
            assert json.loads(messages[0].value) == {"conversation_id": "123", "topic": "AI"}

    async def test_message_handler_registration(self, kafka_consumer):
        """Test registering message handlers for specific topics."""
        handler_called = False
        processed_message = None
        
        async def test_handler(message):
            nonlocal handler_called, processed_message
            handler_called = True
            processed_message = message
            return True
        
        kafka_consumer.register_handler("conversation.new", test_handler)
        
        # Simulate processing a message
        mock_message = MagicMock()
        mock_message.topic = "conversation.new"
        mock_message.value = b'{"test": "data"}'
        
        result = await kafka_consumer._process_message(mock_message)
        
        assert result is True
        assert handler_called is True
        assert processed_message == mock_message

    async def test_consumer_error_handling(self, kafka_consumer):
        """Test error handling in message consumption."""
        # TODO: FAILING - Mock path issue + _handle_error method not implemented
        # TODO: Fix by mocking correctly and implementing _handle_error in consumer
        with patch('app.kafka.consumer.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            # Simulate error during consumption
            async def error_iter():
                raise KafkaError("Connection lost")
            
            mock_consumer.__aiter__ = lambda self: error_iter()
            
            await kafka_consumer.start()
            
            # Should handle error gracefully and attempt reconnection
            with patch.object(kafka_consumer, '_handle_error') as mock_error_handler:
                try:
                    async for message in kafka_consumer:
                        pass
                except KafkaError:
                    pass
                
                mock_error_handler.assert_called()

    async def test_offset_management(self, kafka_consumer):
        """Test manual offset management."""
        # TODO: FAILING - Mock path issue affecting consumer tests
        # TODO: Fix by properly mocking AIOKafkaConsumer in consumer module
        with patch('app.kafka.consumer.AIOKafkaConsumer') as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            await kafka_consumer.start()
            
            mock_message = MagicMock()
            mock_message.topic = "test.topic"
            mock_message.partition = 0
            mock_message.offset = 100
            
            # Test committing offset
            await kafka_consumer.commit_offset(mock_message)
            mock_consumer.commit.assert_called_once()

    async def test_consumer_group_rebalancing(self, kafka_consumer):
        """Test handling of consumer group rebalancing."""
        rebalance_events = []
        
        def on_rebalance(event_type, partitions):
            rebalance_events.append((event_type, partitions))
        
        kafka_consumer.on_rebalance = on_rebalance
        
        # Simulate rebalance events
        await kafka_consumer._handle_rebalance("assigned", ["topic-0", "topic-1"])
        await kafka_consumer._handle_rebalance("revoked", ["topic-0"])
        
        assert len(rebalance_events) == 2
        assert rebalance_events[0][0] == "assigned"
        assert rebalance_events[1][0] == "revoked"


class TestKafkaEventRouter:
    """Test cases for Kafka event routing."""

    @pytest_asyncio.fixture
    async def event_router(self, mock_kafka_consumer, mock_kafka_producer):
        """Create a Kafka event router instance."""
        from app.kafka.event_router import KafkaEventRouter
        return KafkaEventRouter(mock_kafka_consumer, mock_kafka_producer)

    async def test_route_conversation_new_event(self, event_router):
        """Test routing of new conversation events."""
        handler_called = False
        received_data = None
        
        async def conversation_handler(data):
            nonlocal handler_called, received_data
            handler_called = True
            received_data = data
            return True
        
        event_router.register_handler("conversation.new", conversation_handler)
        
        mock_message = MagicMock()
        mock_message.topic = "conversation.new"
        mock_message.value = b'{"conversation_id": "123", "topic": "AI"}'
        
        await event_router.route_message(mock_message)
        
        assert handler_called is True
        assert received_data["conversation_id"] == "123"

    async def test_route_conversation_turn_event(self, event_router):
        """Test routing of conversation turn events."""
        turn_processed = False
        
        async def turn_handler(data):
            nonlocal turn_processed
            turn_processed = True
            # Simulate processing turn and generating response
            return {"status": "processed", "next_model": "google"}
        
        event_router.register_handler("conversation.turn", turn_handler)
        
        mock_message = MagicMock()
        mock_message.topic = "conversation.turn"
        mock_message.value = b'{"conversation_id": "123", "turn": 1}'
        
        result = await event_router.route_message(mock_message)
        
        assert turn_processed is True
        assert result["status"] == "processed"

    async def test_dead_letter_queue_handling(self, event_router):
        """Test handling of messages that fail processing."""
        async def failing_handler(data):
            raise ValueError("Processing failed")
        
        event_router.register_handler("conversation.new", failing_handler)
        
        mock_message = MagicMock()
        mock_message.topic = "conversation.new"
        mock_message.value = b'{"conversation_id": "123"}'
        
        with patch.object(event_router, '_send_to_dlq') as mock_dlq:
            result = await event_router.route_message(mock_message)
            
            assert result is False
            mock_dlq.assert_called_once()

    async def test_message_ordering_within_partition(self, event_router):
        """Test that messages within the same partition are processed in order."""
        processed_order = []
        
        async def ordered_handler(data):
            processed_order.append(data["sequence"])
            # Simulate variable processing time
            await asyncio.sleep(0.01 if data["sequence"] % 2 == 0 else 0.005)
            return True
        
        event_router.register_handler("test.ordered", ordered_handler)
        
        # Send messages with same partition key (should maintain order)
        messages = []
        for i in range(5):
            mock_message = MagicMock()
            mock_message.topic = "test.ordered"
            mock_message.value = json.dumps({"sequence": i}).encode()
            mock_message.partition = 0  # Same partition
            messages.append(mock_message)
        
        # Process messages
        for message in messages:
            await event_router.route_message(message)
        
        assert processed_order == [0, 1, 2, 3, 4]

    async def test_event_schema_validation(self, event_router):
        """Test validation of event schemas."""
        async def validating_handler(data):
            return True
        
        event_router.register_handler("conversation.new", validating_handler)
        
        # Valid message
        valid_message = MagicMock()
        valid_message.topic = "conversation.new"
        valid_message.value = b'{"conversation_id": "123", "topic": "Valid topic"}'
        
        result = await event_router.route_message(valid_message)
        assert result is True
        
        # Invalid message (missing required fields)
        invalid_message = MagicMock()
        invalid_message.topic = "conversation.new"
        invalid_message.value = b'{"incomplete": "data"}'
        
        with patch.object(event_router, '_validate_schema', return_value=False):
            result = await event_router.route_message(invalid_message)
            assert result is False