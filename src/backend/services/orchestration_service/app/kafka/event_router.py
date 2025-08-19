"""Kafka event router for handling message routing and processing."""

import json
import asyncio
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class KafkaEventRouter:
    """Routes Kafka messages to appropriate handlers."""
    
    def __init__(self, consumer, producer):
        """Initialize event router with consumer and producer."""
        self.consumer = consumer
        self.producer = producer
        self._handlers: Dict[str, Callable] = {}
        
    def register_handler(self, topic: str, handler: Callable) -> None:
        """Register a message handler for a specific topic."""
        self._handlers[topic] = handler
        
    async def route_message(self, message) -> Any:
        """Route a message to the appropriate handler."""
        try:
            if message.topic in self._handlers:
                handler = self._handlers[message.topic]
                
                # Validate schema if needed
                if not await self._validate_schema(message):
                    return False
                    
                # Parse message data
                data = json.loads(message.value) if isinstance(message.value, bytes) else message.value
                
                # Call handler
                result = await handler(data)
                return result
            else:
                logger.warning(f"No handler registered for topic: {message.topic}")
                return False
                
        except Exception as e:
            logger.error(f"Error routing message from topic {message.topic}: {e}")
            await self._send_to_dlq(message, str(e))
            return False
            
    async def _validate_schema(self, message) -> bool:
        """Validate message schema (placeholder implementation)."""
        # This would contain actual schema validation logic
        return True
        
    async def _send_to_dlq(self, message, error: str) -> None:
        """Send failed message to dead letter queue."""
        dlq_topic = f"{message.topic}.dlq"
        dlq_data = {
            "original_topic": message.topic,
            "original_message": message.value.decode() if isinstance(message.value, bytes) else message.value,
            "error": error,
            "timestamp": message.timestamp
        }
        
        try:
            await self.producer.send_event(dlq_topic, dlq_data)
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")