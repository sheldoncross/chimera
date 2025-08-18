"""Pydantic models for Kafka events."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime
import uuid

from .conversation import ConversationTurn, ConversationMetadata


class BaseEvent(BaseModel):
    """Base class for all Kafka events."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    event_type: str = Field(..., description="Type of the event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    source_service: str = Field(default="orchestration-service", description="Service that generated the event")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationNewEvent(BaseEvent):
    """Event for starting a new conversation."""
    
    event_type: Literal["conversation.new"] = "conversation.new"
    conversation_id: str = Field(..., description="Unique conversation ID")
    topic: str = Field(..., min_length=1, description="Conversation topic")
    source: str = Field(..., description="Source of the topic")
    source_url: Optional[str] = Field(None, description="Source URL")
    initial_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Initial context for the conversation")
    priority: Literal["high", "normal", "low"] = Field(default="normal", description="Processing priority")
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("conversation_id must be a valid UUID")
        return v


class ConversationTurnEvent(BaseEvent):
    """Event for processing a conversation turn."""
    
    event_type: Literal["conversation.turn"] = "conversation.turn"
    conversation_id: str = Field(..., description="Conversation ID")
    turn_number: int = Field(..., ge=1, description="Turn number to process")
    target_model: str = Field(..., description="Target LLM model for this turn")
    previous_turns: List[ConversationTurn] = Field(default_factory=list, description="Previous conversation turns")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context for the turn")
    
    @validator('target_model')
    def validate_target_model(cls, v):
        valid_models = ["anthropic", "google", "claude-3-sonnet", "gemini-pro"]
        if v not in valid_models:
            raise ValueError(f"Invalid target model: {v}")
        return v


class ConversationResponseEvent(BaseEvent):
    """Event for LLM response to a conversation turn."""
    
    event_type: Literal["conversation.response"] = "conversation.response"
    conversation_id: str = Field(..., description="Conversation ID")
    turn: ConversationTurn = Field(..., description="The generated turn")
    success: bool = Field(..., description="Whether the response was successful")
    error_message: Optional[str] = Field(None, description="Error message if response failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    
    @validator('turn')
    def validate_turn_content(cls, v, values):
        if values.get('success', False) and not v.content.strip():
            raise ValueError("Successful response must have non-empty content")
        return v


class ConversationCompletedEvent(BaseEvent):
    """Event for completed conversations."""
    
    event_type: Literal["conversation.completed"] = "conversation.completed"
    conversation_id: str = Field(..., description="Conversation ID")
    topic: str = Field(..., description="Conversation topic")
    source: str = Field(..., description="Source of the topic")
    turns: List[ConversationTurn] = Field(..., description="All conversation turns")
    metadata: ConversationMetadata = Field(..., description="Conversation metadata")
    completion_reason: Literal["max_turns", "timeout", "natural_ending", "repetition", "error"] = Field(
        ..., 
        description="Reason for completion"
    )
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Quality score of the conversation")
    created_at: datetime = Field(..., description="Conversation creation time")
    completed_at: datetime = Field(default_factory=datetime.utcnow, description="Conversation completion time")
    
    @validator('turns')
    def validate_turns_not_empty(cls, v):
        if not v:
            raise ValueError("Completed conversation must have at least one turn")
        return v
    
    @validator('metadata')
    def validate_metadata_consistency(cls, v, values):
        if 'turns' in values:
            expected_turns = len(values['turns'])
            if v.total_turns != expected_turns:
                raise ValueError(f"Metadata total_turns ({v.total_turns}) doesn't match actual turns ({expected_turns})")
        return v


class ConversationErrorEvent(BaseEvent):
    """Event for conversation processing errors."""
    
    event_type: Literal["conversation.error"] = "conversation.error"
    conversation_id: str = Field(..., description="Conversation ID")
    error_type: Literal["llm_api_error", "timeout", "validation_error", "system_error"] = Field(
        ..., 
        description="Type of error"
    )
    error_message: str = Field(..., description="Error message")
    error_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional error details")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    is_recoverable: bool = Field(default=True, description="Whether the error is recoverable")
    turn_number: Optional[int] = Field(None, description="Turn number where error occurred")


class ConversationHealthEvent(BaseEvent):
    """Event for conversation service health monitoring."""
    
    event_type: Literal["conversation.health"] = "conversation.health"
    service_status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Service health status")
    active_conversations: int = Field(..., ge=0, description="Number of active conversations")
    pending_topics: int = Field(..., ge=0, description="Number of pending topics in queue")
    llm_client_status: Dict[str, bool] = Field(..., description="Status of LLM clients")
    error_rate: float = Field(..., ge=0, le=1, description="Error rate in last monitoring window")
    avg_response_time_ms: float = Field(..., ge=0, description="Average response time")
    
    @validator('llm_client_status')
    def validate_client_status(cls, v):
        required_clients = ["anthropic", "google"]
        missing_clients = [client for client in required_clients if client not in v]
        if missing_clients:
            raise ValueError(f"Missing status for clients: {missing_clients}")
        return v


class ConversationMetricsEvent(BaseEvent):
    """Event for conversation metrics and analytics."""
    
    event_type: Literal["conversation.metrics"] = "conversation.metrics"
    time_window_minutes: int = Field(..., gt=0, description="Time window for metrics in minutes")
    conversations_started: int = Field(..., ge=0, description="Conversations started in window")
    conversations_completed: int = Field(..., ge=0, description="Conversations completed in window")
    conversations_failed: int = Field(..., ge=0, description="Conversations failed in window")
    avg_turns_per_conversation: float = Field(..., ge=0, description="Average turns per conversation")
    avg_conversation_duration_seconds: float = Field(..., ge=0, description="Average conversation duration")
    avg_quality_score: Optional[float] = Field(None, ge=0, le=1, description="Average quality score")
    model_usage: Dict[str, int] = Field(..., description="Usage count per model")
    completion_reasons: Dict[str, int] = Field(..., description="Count of completion reasons")
    
    @validator('model_usage')
    def validate_model_usage(cls, v):
        if not v:
            raise ValueError("Model usage cannot be empty")
        return v


# Event type mapping for deserialization
EVENT_TYPE_MAPPING = {
    "conversation.new": ConversationNewEvent,
    "conversation.turn": ConversationTurnEvent,
    "conversation.response": ConversationResponseEvent,
    "conversation.completed": ConversationCompletedEvent,
    "conversation.error": ConversationErrorEvent,
    "conversation.health": ConversationHealthEvent,
    "conversation.metrics": ConversationMetricsEvent,
}


def parse_event(event_data: Dict[str, Any]) -> BaseEvent:
    """Parse event data into appropriate event model."""
    event_type = event_data.get("event_type")
    
    if event_type not in EVENT_TYPE_MAPPING:
        raise ValueError(f"Unknown event type: {event_type}")
    
    event_class = EVENT_TYPE_MAPPING[event_type]
    return event_class(**event_data)


def serialize_event(event: BaseEvent) -> Dict[str, Any]:
    """Serialize event model to dictionary."""
    return event.dict()


class EventEnvelope(BaseModel):
    """Envelope for wrapping events with metadata."""
    
    event: BaseEvent = Field(..., description="The actual event")
    partition_key: Optional[str] = Field(None, description="Kafka partition key")
    headers: Dict[str, str] = Field(default_factory=dict, description="Kafka headers")
    topic: str = Field(..., description="Target Kafka topic")
    
    class Config:
        arbitrary_types_allowed = True