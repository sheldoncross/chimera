"""Kafka producer for sending events."""

import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
import logging

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Async Kafka producer for publishing events."""
    
    def __init__(self, settings: Dict[str, Any]):
        """Initialize Kafka producer with settings."""
        self.bootstrap_servers = settings.get("kafka_bootstrap_servers", "localhost:9092")
        self.max_retries = settings.get("kafka_max_retries", 3)
        self.retry_delay = settings.get("kafka_retry_delay_seconds", 1)
        self._producer: Optional[AIOKafkaProducer] = None
        
    async def start(self) -> None:
        """Start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self._producer.start()
        
    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            
    async def send_event(self, topic: str, event_data: Dict[str, Any], key: Optional[str] = None) -> bool:
        """Send a single event to Kafka topic with retry logic."""
        if not self._producer:
            raise RuntimeError("Producer not started")
            
        for attempt in range(self.max_retries):
            try:
                kwargs = {"topic": topic, "value": event_data}
                if key:
                    kwargs["key"] = key.encode('utf-8')
                    
                await self._producer.send(**kwargs)
                return True
                
            except KafkaError as e:
                logger.warning(f"Kafka send attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to send event after {self.max_retries} attempts")
                    return False
                    
        return False
        
    async def send_batch(self, events: List[Tuple[str, Dict[str, Any]]]) -> List[bool]:
        """Send multiple events in batch."""
        results = []
        for topic, event_data in events:
            result = await self.send_event(topic, event_data)
            results.append(result)
        return results