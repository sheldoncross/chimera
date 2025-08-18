"""Kafka-specific configuration and utilities."""

from typing import Dict, Any, List
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.helpers import create_ssl_context
import ssl
import logging

from .settings import Settings

logger = logging.getLogger(__name__)


class KafkaConfig:
    """Kafka configuration utility class."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def get_producer_config(self) -> Dict[str, Any]:
        """Get configuration for Kafka producer."""
        config = {
            "bootstrap_servers": self.settings.kafka_bootstrap_servers_list,
            "value_serializer": lambda x: x.encode('utf-8') if isinstance(x, str) else x,
            "key_serializer": lambda x: x.encode('utf-8') if isinstance(x, str) else x,
            "acks": "all",  # Wait for all replicas to acknowledge
            "retries": 5,
            "max_in_flight_requests_per_connection": 1,  # Ensure ordering
            "enable_idempotence": True,  # Prevent duplicate messages
            "compression_type": "gzip",
            "batch_size": 16384,
            "linger_ms": 10,  # Small delay to allow batching
            "buffer_memory": 33554432,  # 32MB
        }
        
        # Add SSL configuration if needed
        ssl_config = self._get_ssl_config()
        if ssl_config:
            config.update(ssl_config)
        
        return config
    
    def get_consumer_config(self, group_id: str = None) -> Dict[str, Any]:
        """Get configuration for Kafka consumer."""
        config = {
            "bootstrap_servers": self.settings.kafka_bootstrap_servers_list,
            "group_id": group_id or self.settings.kafka_consumer_group_id,
            "value_deserializer": lambda x: x.decode('utf-8') if x else None,
            "key_deserializer": lambda x: x.decode('utf-8') if x else None,
            "auto_offset_reset": self.settings.kafka_auto_offset_reset,
            "enable_auto_commit": self.settings.kafka_enable_auto_commit,
            "max_poll_records": 500,
            "session_timeout_ms": 30000,
            "heartbeat_interval_ms": 10000,
            "fetch_max_wait_ms": 500,
            "fetch_min_bytes": 1,
            "fetch_max_bytes": 52428800,  # 50MB
        }
        
        # Add SSL configuration if needed
        ssl_config = self._get_ssl_config()
        if ssl_config:
            config.update(ssl_config)
        
        return config
    
    def _get_ssl_config(self) -> Dict[str, Any]:
        """Get SSL configuration if enabled."""
        # This would be expanded based on your specific SSL requirements
        ssl_config = {}
        
        # Example SSL configuration (uncomment and modify as needed)
        # if self.settings.kafka_ssl_enabled:
        #     ssl_context = create_ssl_context(
        #         cafile=self.settings.kafka_ssl_cafile,
        #         certfile=self.settings.kafka_ssl_certfile,
        #         keyfile=self.settings.kafka_ssl_keyfile,
        #         password=self.settings.kafka_ssl_password,
        #         cadata=self.settings.kafka_ssl_cadata
        #     )
        #     ssl_config = {
        #         "security_protocol": "SSL",
        #         "ssl_context": ssl_context
        #     }
        
        return ssl_config
    
    def get_topic_list(self) -> List[str]:
        """Get list of all topics used by the application."""
        return [
            self.settings.topic_conversation_new,
            self.settings.topic_conversation_turn,
            self.settings.topic_conversation_response,
            self.settings.topic_conversation_completed
        ]
    
    def get_topic_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get topic-specific configurations."""
        return {
            self.settings.topic_conversation_new: {
                "num_partitions": 3,
                "replication_factor": 2,
                "config": {
                    "retention.ms": "86400000",  # 24 hours
                    "cleanup.policy": "delete"
                }
            },
            self.settings.topic_conversation_turn: {
                "num_partitions": 6,  # Higher partitions for better parallelism
                "replication_factor": 2,
                "config": {
                    "retention.ms": "86400000",
                    "cleanup.policy": "delete"
                }
            },
            self.settings.topic_conversation_response: {
                "num_partitions": 6,
                "replication_factor": 2,
                "config": {
                    "retention.ms": "86400000",
                    "cleanup.policy": "delete"
                }
            },
            self.settings.topic_conversation_completed: {
                "num_partitions": 2,
                "replication_factor": 3,  # Higher replication for completed conversations
                "config": {
                    "retention.ms": "604800000",  # 7 days
                    "cleanup.policy": "delete"
                }
            }
        }
    
    async def create_producer(self) -> AIOKafkaProducer:
        """Create and return a configured Kafka producer."""
        config = self.get_producer_config()
        producer = AIOKafkaProducer(**config)
        return producer
    
    async def create_consumer(self, 
                            topics: List[str] = None, 
                            group_id: str = None) -> AIOKafkaConsumer:
        """Create and return a configured Kafka consumer."""
        config = self.get_consumer_config(group_id)
        
        if topics:
            consumer = AIOKafkaConsumer(*topics, **config)
        else:
            consumer = AIOKafkaConsumer(**config)
        
        return consumer
    
    def validate_topics(self, topics: List[str]) -> List[str]:
        """Validate that topics are properly configured."""
        valid_topics = self.get_topic_list()
        invalid_topics = [topic for topic in topics if topic not in valid_topics]
        
        if invalid_topics:
            logger.warning(f"Invalid topics detected: {invalid_topics}")
        
        return [topic for topic in topics if topic in valid_topics]
    
    def get_partition_key(self, conversation_id: str) -> str:
        """Generate partition key for conversation-related messages."""
        # Use conversation_id as partition key to ensure message ordering
        # within a conversation
        return conversation_id
    
    def get_headers(self, event_type: str = None, source: str = None) -> Dict[str, bytes]:
        """Generate standard headers for Kafka messages."""
        headers = {
            "service": b"orchestration-service",
            "version": self.settings.app_version.encode(),
        }
        
        if event_type:
            headers["event_type"] = event_type.encode()
        
        if source:
            headers["source"] = source.encode()
        
        return headers