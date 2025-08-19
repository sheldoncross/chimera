"""Redis state management for conversations and topics."""

import json
import asyncio
import time
from typing import Dict, Any, List, Optional, Set
import redis.asyncio as redis
from redis.asyncio.client import Redis
import logging

logger = logging.getLogger(__name__)


class RedisStateManager:
    """Manages conversation state and topic queue in Redis."""
    
    def __init__(self, settings, redis_client=None):
        """Initialize Redis state manager."""
        # Handle test injection of redis_client
        if redis_client is not None:
            self.redis_client = redis_client
            self.conversation_ttl = 86400  # Default for testing
            self._locks: Dict[str, asyncio.Lock] = {}
            return
            
        # Normal initialization
        if isinstance(settings, dict):
            self.redis_host = settings.get("redis_host", "localhost")
            self.redis_port = settings.get("redis_port", 6379)
            self.redis_password = settings.get("redis_password")
            self.redis_db = settings.get("redis_db", 0)
            self.conversation_ttl = settings.get("conversation_ttl_seconds", 86400)
        else:
            self.redis_host = settings.redis_host
            self.redis_port = settings.redis_port
            self.redis_password = settings.redis_password
            self.redis_db = settings.redis_db
            self.conversation_ttl = settings.conversation_ttl_seconds
            
        self.redis_client: Optional[Redis] = None
        self._locks: Dict[str, asyncio.Lock] = {}
        
    async def start(self):
        """Start Redis connection."""
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            db=self.redis_db,
            decode_responses=True
        )
        
    async def stop(self):
        """Stop Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            
    async def save_conversation_state(self, conversation_id: str, state: Dict[str, Any]) -> bool:
        """Save conversation state to Redis."""
        try:
            if not self.redis_client:
                await self.start()
                
            # Validate conversation state
            if not self._validate_conversation_state(state):
                return False
                
            key = f"conversation:{conversation_id}"
            state_json = json.dumps(state)
            
            # Simple operations for test compatibility  
            await self.redis_client.set(key, state_json, ex=self.conversation_ttl)
            await self.redis_client.sadd("active_conversations", conversation_id)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation state: {e}")
            return False
            
    async def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation state from Redis."""
        try:
            if not self.redis_client:
                await self.start()
                
            key = f"conversation:{conversation_id}"
            state_json = await self.redis_client.get(key)
            
            if state_json:
                return json.loads(state_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get conversation state: {e}")
            return None
            
    async def update_conversation_state(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing conversation state."""
        try:
            # Get current state
            current_state = await self.get_conversation_state(conversation_id)
            if not current_state:
                return False
                
            # Merge updates
            current_state.update(updates)
            
            # Save updated state
            return await self.save_conversation_state(conversation_id, current_state)
            
        except Exception as e:
            logger.error(f"Failed to update conversation state: {e}")
            return False
            
    async def delete_conversation_state(self, conversation_id: str) -> bool:
        """Delete conversation state from Redis."""
        try:
            if not self.redis_client:
                await self.start()
                
            key = f"conversation:{conversation_id}"
            
            await self.redis_client.delete(key)
            await self.redis_client.srem("active_conversations", conversation_id)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete conversation state: {e}")
            return False
            
    async def list_active_conversations(self) -> Set[str]:
        """List all active conversation IDs."""
        try:
            if not self.redis_client:
                await self.start()
                
            return await self.redis_client.smembers("active_conversations")
            
        except Exception as e:
            logger.error(f"Failed to list active conversations: {e}")
            return set()
            
    async def get_conversation_metrics(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation metrics."""
        try:
            state = await self.get_conversation_state(conversation_id)
            if not state:
                return None
                
            return state.get("metrics", {})
            
        except Exception as e:
            logger.error(f"Failed to get conversation metrics: {e}")
            return None
            
    async def acquire_conversation_lock(self, conversation_id: str, timeout: int = 30) -> bool:
        """Acquire a lock for conversation processing."""
        try:
            if not self.redis_client:
                await self.start()
                
            lock_key = f"lock:conversation:{conversation_id}"
            acquired = await self.redis_client.set(
                lock_key, 
                "locked", 
                nx=True, 
                ex=timeout
            )
            
            return acquired is not None
            
        except Exception as e:
            logger.error(f"Failed to acquire conversation lock: {e}")
            return False
            
    async def release_conversation_lock(self, conversation_id: str) -> bool:
        """Release conversation lock."""
        try:
            if not self.redis_client:
                await self.start()
                
            lock_key = f"lock:conversation:{conversation_id}"
            deleted = await self.redis_client.delete(lock_key)
            
            return deleted > 0
            
        except Exception as e:
            logger.error(f"Failed to release conversation lock: {e}")
            return False
            
    async def get_topic_from_queue(self) -> Optional[Dict[str, Any]]:
        """Get next topic from the topic queue."""
        try:
            if not self.redis_client:
                await self.start()
                
            topic_json = await self.redis_client.lpop("topic_queue")
            if topic_json:
                return json.loads(topic_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get topic from queue: {e}")
            return None
            
    async def get_topic_queue_length(self) -> int:
        """Get the length of the topic queue."""
        try:
            if not self.redis_client:
                await self.start()
                
            return await self.redis_client.llen("topic_queue")
            
        except Exception as e:
            logger.error(f"Failed to get topic queue length: {e}")
            return 0
            
    async def search_conversations(self, 
                                  topic: Optional[str] = None, 
                                  status: Optional[str] = None) -> List[str]:
        """Search conversations by topic or metadata."""
        try:
            conversation_ids = await self.list_active_conversations()
            matching_ids = []
            
            for conv_id in conversation_ids:
                state = await self.get_conversation_state(conv_id)
                if not state:
                    continue
                    
                # Filter by topic
                if topic and topic.lower() not in state.get("topic", "").lower():
                    continue
                    
                # Filter by status
                if status and state.get("metadata", {}).get("status") != status:
                    continue
                    
                matching_ids.append(conv_id)
                
            return matching_ids
            
        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []
            
    async def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversation states."""
        try:
            if not self.redis_client:
                await self.start()
                
            cleaned_count = 0
            conversation_ids = await self.list_active_conversations()
            
            for conv_id in conversation_ids:
                key = f"conversation:{conv_id}"
                exists = await self.redis_client.exists(key)
                
                if not exists:
                    # Remove from active set if key doesn't exist
                    await self.redis_client.srem("active_conversations", conv_id)
                    cleaned_count += 1
                    
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired conversations: {e}")
            return 0
            
    def _validate_conversation_state(self, state: Dict[str, Any]) -> bool:
        """Validate conversation state structure."""
        required_fields = ["conversation_id", "topic", "turns"]
        
        for field in required_fields:
            if field not in state:
                logger.warning(f"Missing required field in conversation state: {field}")
                return False
                
        # Validate turns structure
        turns = state.get("turns", [])
        if not isinstance(turns, list):
            logger.warning("Turns must be a list")
            return False
            
        return True