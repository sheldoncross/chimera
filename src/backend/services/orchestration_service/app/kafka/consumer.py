"""Kafka consumer for receiving events."""

import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, AsyncIterator
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
import logging

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """Async Kafka consumer for consuming events."""
    
    def __init__(self, settings: Dict[str, Any], group_id: str):
        """Initialize Kafka consumer with settings."""
        self.bootstrap_servers = settings.get("kafka_bootstrap_servers", "localhost:9092")
        self.group_id = group_id
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._handlers: Dict[str, Callable] = {}
        self.on_rebalance: Optional[Callable] = None
        
    async def start(self) -> None:
        """Start the Kafka consumer."""
        self._consumer = AIOKafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None
        )
        await self._consumer.start()
        
    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        if self._consumer:
            await self._consumer.stop()
            
    async def subscribe(self, topics: List[str]) -> None:
        """Subscribe to Kafka topics."""
        if not self._consumer:
            raise RuntimeError("Consumer not started")
        self._consumer.subscribe(topics)
        
    def register_handler(self, topic: str, handler: Callable) -> None:
        """Register a message handler for a specific topic."""
        self._handlers[topic] = handler
        
    async def _process_message(self, message) -> bool:
        """Process a single message using registered handlers."""
        if message.topic in self._handlers:
            handler = self._handlers[message.topic]
            try:
                result = await handler(message)
                return result if result is not None else True
            except Exception as e:
                logger.error(f"Handler error for topic {message.topic}: {e}")
                return False
        return True
        
    async def _handle_error(self, error: Exception) -> None:
        """Handle consumer errors."""
        logger.error(f"Consumer error: {error}")
        
    async def _handle_rebalance(self, event_type: str, partitions: List[str]) -> None:
        """Handle consumer group rebalancing."""
        if self.on_rebalance:
            self.on_rebalance(event_type, partitions)
            
    async def commit_offset(self, message) -> None:
        """Commit message offset."""
        if self._consumer:
            await self._consumer.commit()
            
    def __aiter__(self) -> AsyncIterator:
        """Make consumer async iterable."""
        return self
        
    async def __anext__(self):
        """Get next message from consumer."""
        if not self._consumer:
            raise RuntimeError("Consumer not started")
            
        try:
            async for message in self._consumer:
                return message
        except KafkaError as e:
            await self._handle_error(e)
            raise StopAsyncIteration