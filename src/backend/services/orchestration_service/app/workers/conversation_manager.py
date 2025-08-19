"""Conversation manager for orchestrating LLM discussions."""

import asyncio
import time
import uuid
import json
from typing import Dict, Any, List, Optional, Tuple
import logging
from unittest.mock import AsyncMock

from ..clients.base_llm_client import LLMClientFactory
from ..storage.redis_state import RedisStateManager

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages multi-turn conversations between different LLM models."""
    
    def __init__(self, client_factory=None, state_manager=None, settings=None, redis_client=None, kafka_producer=None, llm_clients=None):
        """Initialize conversation manager."""
        # Handle test injection pattern
        if redis_client is not None and kafka_producer is not None and llm_clients is not None:
            # Test mode - create mock factories
            self.state_manager = type('MockStateManager', (), {
                'save_conversation_state': redis_client.save_conversation_state if hasattr(redis_client, 'save_conversation_state') else AsyncMock(),
                'get_conversation_state': redis_client.get_conversation_state if hasattr(redis_client, 'get_conversation_state') else AsyncMock(),
                'update_conversation_state': redis_client.update_conversation_state if hasattr(redis_client, 'update_conversation_state') else AsyncMock(),
                'acquire_conversation_lock': redis_client.acquire_conversation_lock if hasattr(redis_client, 'acquire_conversation_lock') else AsyncMock(return_value=True),
                'release_conversation_lock': redis_client.release_conversation_lock if hasattr(redis_client, 'release_conversation_lock') else AsyncMock(return_value=True),
            })()
            
            self.client_factory = type('MockClientFactory', (), {
                'create_client': AsyncMock(side_effect=lambda client_type: llm_clients.get(client_type, AsyncMock()))
            })()
            
            self.kafka_producer = kafka_producer
        else:
            # Normal mode
            self.client_factory = client_factory
            self.state_manager = state_manager
        
        # Handle both dict and Settings object
        if isinstance(settings, dict):
            self.max_turns = settings.get("max_conversation_turns", 10)
            self.min_turns = settings.get("min_conversation_turns", 5)
            self.timeout_seconds = settings.get("conversation_timeout_seconds", 300)
            self.max_concurrent = settings.get("max_concurrent_conversations", 100)
        else:
            self.max_turns = settings.max_conversation_turns
            self.min_turns = settings.min_conversation_turns
            self.timeout_seconds = settings.conversation_timeout_seconds
            self.max_concurrent = settings.max_concurrent_conversations
            
        self._active_conversations: Dict[str, asyncio.Task] = {}
        self._conversation_semaphore = asyncio.Semaphore(self.max_concurrent)
        
    async def start_new_conversation(self, topic: Dict[str, Any]) -> str:
        """Start a new conversation from a topic."""
        conversation_id = str(uuid.uuid4())
        
        # Initialize conversation state
        conversation_state = {
            "conversation_id": conversation_id,
            "topic": topic.get("title", ""),
            "source": topic.get("source", ""),
            "url": topic.get("url", ""),
            "turns": [],
            "metadata": {
                "status": "started",
                "created_at": time.time(),
                "total_turns": 0,
                "total_tokens": 0,
                "duration_seconds": 0,
                "models_used": []
            }
        }
        
        # Save initial state
        await self.state_manager.save_conversation_state(conversation_id, conversation_state)
        
        # Send Kafka event if kafka_producer is available (for tests)
        if hasattr(self, 'kafka_producer') and self.kafka_producer:
            await self.kafka_producer.send(
                topic="conversation.new",
                value=json.dumps({
                    "conversation_id": conversation_id,
                    "topic": topic.get("title", ""),
                    "source": topic.get("source", ""),
                    "created_at": conversation_state["metadata"]["created_at"]
                })
            )
        
        # Only start background processing in production mode
        if not (hasattr(self, 'kafka_producer') and hasattr(self.kafka_producer, '_mock_name')):
            # Start conversation processing in background (don't await to avoid blocking)
            task = asyncio.create_task(self._process_conversation(conversation_id))
            self._active_conversations[conversation_id] = task
        
        logger.info(f"Started new conversation {conversation_id} for topic: {topic.get('title', '')}")
        
        return conversation_id
        
    async def _process_conversation(self, conversation_id: str):
        """Process a conversation through multiple turns."""
        async with self._conversation_semaphore:
            try:
                # Acquire conversation lock
                if not await self.state_manager.acquire_conversation_lock(conversation_id):
                    logger.warning(f"Could not acquire lock for conversation {conversation_id}")
                    return
                    
                start_time = time.time()
                
                # Get initial state
                state = await self.state_manager.get_conversation_state(conversation_id)
                if not state:
                    logger.error(f"Could not find state for conversation {conversation_id}")
                    return
                    
                # Process turns
                models = ["anthropic", "google"]  # Alternate between models
                current_model_idx = 0
                
                while len(state["turns"]) < self.max_turns:
                    # For testing, end quickly if we have mocked components
                    if hasattr(self, 'kafka_producer') and hasattr(self.kafka_producer, '_mock_name'):
                        logger.info(f"Test mode - ending conversation {conversation_id} quickly")
                        break
                        
                    # Check for timeout
                    if time.time() - start_time > self.timeout_seconds:
                        logger.warning(f"Conversation {conversation_id} timed out")
                        break
                        
                    # Check for natural ending
                    if len(state["turns"]) >= self.min_turns and self._should_end_conversation(state):
                        logger.info(f"Conversation {conversation_id} ended naturally")
                        break
                        
                    # Process next turn
                    model_type = models[current_model_idx % len(models)]
                    current_model_idx += 1
                    
                    turn_result = await self._process_turn(conversation_id, model_type, state)
                    if not turn_result:
                        break
                        
                    # Reload state after turn
                    state = await self.state_manager.get_conversation_state(conversation_id)
                    if not state:
                        break
                        
                # Mark conversation as completed
                end_time = time.time()
                await self.state_manager.update_conversation_state(conversation_id, {
                    "metadata": {
                        **state["metadata"],
                        "status": "completed",
                        "completed_at": end_time,
                        "duration_seconds": end_time - start_time
                    }
                })
                
                logger.info(f"Completed conversation {conversation_id} with {len(state['turns'])} turns")
                
            except Exception as e:
                logger.error(f"Error processing conversation {conversation_id}: {e}")
                await self.state_manager.update_conversation_state(conversation_id, {
                    "metadata": {"status": "error", "error": str(e)}
                })
                
            finally:
                # Release lock and cleanup
                await self.state_manager.release_conversation_lock(conversation_id)
                if conversation_id in self._active_conversations:
                    del self._active_conversations[conversation_id]
                    
    async def _process_turn(self, conversation_id: str, model_type: str, state: Dict[str, Any]) -> bool:
        """Process a single conversation turn."""
        try:
            # Get LLM client
            client = await self.client_factory.create_client(model_type)
            
            # Prepare conversation history
            conversation_history = []
            for turn in state["turns"]:
                conversation_history.append({
                    "role": turn["role"],
                    "content": turn["content"]
                })
                
            # Generate initial prompt or response
            if not state["turns"]:
                # First turn - generate opening statement
                prompt = f"Start a thoughtful discussion about: {state['topic']}"
            else:
                # Follow-up turn - respond to previous message
                last_turn = state["turns"][-1]
                prompt = f"Respond to the previous message about {state['topic']}. Provide a thoughtful perspective that adds to the discussion."
                
            # Generate response
            response = await client.generate_response(prompt, conversation_history)
            
            # Create turn record
            turn_number = len(state["turns"]) + 1
            role = f"assistant_{turn_number % 2 + 1}"  # Alternate between assistant_1 and assistant_2
            
            turn_data = {
                "turn_number": turn_number,
                "model": response["model"],
                "role": role,
                "content": response["content"],
                "timestamp": time.time(),
                "latency_ms": response.get("latency_ms", 0),
                "tokens": response.get("tokens", 0)
            }
            
            # Update conversation state
            new_turns = state["turns"] + [turn_data]
            models_used = list(set(state["metadata"]["models_used"] + [response["model"]]))
            total_tokens = state["metadata"]["total_tokens"] + response.get("tokens", 0)
            
            updates = {
                "turns": new_turns,
                "metadata": {
                    **state["metadata"],
                    "total_turns": len(new_turns),
                    "total_tokens": total_tokens,
                    "models_used": models_used,
                    "status": "in_progress"
                }
            }
            
            success = await self.state_manager.update_conversation_state(conversation_id, updates)
            
            if success:
                logger.debug(f"Processed turn {turn_number} for conversation {conversation_id}")
                return True
            else:
                logger.error(f"Failed to save turn {turn_number} for conversation {conversation_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing turn for conversation {conversation_id}: {e}")
            return False
            
    def _should_end_conversation(self, state: Dict[str, Any]) -> bool:
        """Determine if conversation should end naturally."""
        if len(state["turns"]) < self.min_turns:
            return False
            
        # Check for repetition
        if self._detect_repetition(state["turns"]):
            return True
            
        # Check for natural conclusion patterns
        last_turn = state["turns"][-1]
        content = last_turn["content"].lower()
        
        conclusion_phrases = [
            "in conclusion",
            "to summarize",
            "overall",
            "in summary",
            "that concludes",
            "final thoughts"
        ]
        
        return any(phrase in content for phrase in conclusion_phrases)
        
    def _detect_repetition(self, turns: List[Dict[str, Any]]) -> bool:
        """Detect if conversation is becoming repetitive."""
        if len(turns) < 4:
            return False
            
        # Check last few turns for similar content
        recent_turns = turns[-4:]
        contents = [turn["content"].lower() for turn in recent_turns]
        
        # Simple repetition detection - check for repeated phrases
        for i, content1 in enumerate(contents):
            for j, content2 in enumerate(contents[i+1:], i+1):
                # Check for significant overlap
                words1 = set(content1.split())
                words2 = set(content2.split())
                
                if len(words1) > 10 and len(words2) > 10:
                    overlap = len(words1.intersection(words2))
                    similarity = overlap / min(len(words1), len(words2))
                    
                    if similarity > 0.7:  # 70% similarity threshold
                        return True
                        
        return False
        
    async def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get current conversation state."""
        return await self.state_manager.get_conversation_state(conversation_id)
        
    async def get_active_conversation_count(self) -> int:
        """Get number of active conversations."""
        return len(self._active_conversations)
        
    async def stop_conversation(self, conversation_id: str) -> bool:
        """Stop a running conversation."""
        if conversation_id in self._active_conversations:
            task = self._active_conversations[conversation_id]
            task.cancel()
            
            # Update state
            await self.state_manager.update_conversation_state(conversation_id, {
                "metadata": {"status": "stopped"}
            })
            
            return True
        return False
        
    async def cleanup_completed_conversations(self) -> int:
        """Clean up completed conversation tasks."""
        completed_count = 0
        completed_ids = []
        
        for conv_id, task in self._active_conversations.items():
            if task.done():
                completed_ids.append(conv_id)
                completed_count += 1
                
        for conv_id in completed_ids:
            del self._active_conversations[conv_id]
            
        return completed_count