"""Pydantic models for conversation data structures."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import uuid


class ConversationTurn(BaseModel):
    """Model for a single conversation turn."""
    
    turn_number: int = Field(..., ge=1, description="Turn number in the conversation")
    model: str = Field(..., description="LLM model that generated this turn")
    role: Literal["assistant_1", "assistant_2"] = Field(..., description="Role of the assistant in conversation")
    content: str = Field(..., min_length=1, description="Content of the turn")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the turn")
    latency_ms: Optional[int] = Field(None, ge=0, description="API latency in milliseconds")
    tokens: Optional[int] = Field(None, ge=0, description="Number of tokens in the response")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationMetadata(BaseModel):
    """Metadata for a conversation."""
    
    total_turns: int = Field(default=0, ge=0, description="Total number of turns")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens used")
    duration_seconds: float = Field(default=0.0, ge=0, description="Total conversation duration")
    models_used: List[str] = Field(default_factory=list, description="List of models used")
    status: Literal["initializing", "in_progress", "completed", "failed", "timeout"] = Field(
        default="initializing", 
        description="Current status of the conversation"
    )
    completion_reason: Optional[Literal["max_turns", "timeout", "natural_ending", "repetition", "error"]] = Field(
        None, 
        description="Reason for conversation completion"
    )
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Quality score of the conversation")
    
    @validator('models_used')
    def validate_models_used(cls, v):
        valid_models = ["claude-3-sonnet", "claude-3-haiku", "gemini-pro", "gemini-pro-vision"]
        invalid_models = [model for model in v if model not in valid_models]
        if invalid_models:
            raise ValueError(f"Invalid models: {invalid_models}")
        return v


class ConversationTopic(BaseModel):
    """Model for conversation topic from data ingestion service."""
    
    id: str = Field(..., description="Unique topic identifier")
    title: str = Field(..., min_length=1, description="Topic title")
    source: str = Field(..., description="Source of the topic (e.g., hackernews)")
    url: Optional[str] = Field(None, description="Source URL if available")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Topic creation timestamp")
    additional_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Conversation(BaseModel):
    """Complete conversation model."""
    
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique conversation ID")
    topic: str = Field(..., min_length=1, description="Conversation topic")
    source: str = Field(..., description="Source of the topic")
    source_url: Optional[str] = Field(None, description="Source URL")
    turns: List[ConversationTurn] = Field(default_factory=list, description="List of conversation turns")
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata, description="Conversation metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Conversation creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('turns')
    def validate_turns_order(cls, v):
        """Validate that turns are in correct order."""
        if not v:
            return v
        
        expected_turn = 1
        for turn in v:
            if turn.turn_number != expected_turn:
                raise ValueError(f"Invalid turn order: expected {expected_turn}, got {turn.turn_number}")
            expected_turn += 1
        
        return v
    
    @validator('metadata')
    def update_metadata_from_turns(cls, v, values):
        """Update metadata based on turns."""
        if 'turns' in values and values['turns']:
            turns = values['turns']
            v.total_turns = len(turns)
            v.total_tokens = sum(turn.tokens or 0 for turn in turns)
            v.models_used = list(set(turn.model for turn in turns))
            
            if len(turns) >= 2:
                start_time = turns[0].timestamp
                end_time = turns[-1].timestamp
                v.duration_seconds = (end_time - start_time).total_seconds()
        
        return v
    
    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a new turn to the conversation."""
        turn.turn_number = len(self.turns) + 1
        self.turns.append(turn)
        self.updated_at = datetime.utcnow()
        
        # Update metadata
        self.metadata.total_turns = len(self.turns)
        self.metadata.total_tokens += turn.tokens or 0
        if turn.model not in self.metadata.models_used:
            self.metadata.models_used.append(turn.model)
        
        if len(self.turns) >= 2:
            duration = (self.turns[-1].timestamp - self.turns[0].timestamp).total_seconds()
            self.metadata.duration_seconds = duration
    
    def is_complete(self, max_turns: int = 10, timeout_seconds: int = 300) -> tuple[bool, Optional[str]]:
        """Check if conversation should be completed and return reason."""
        # Check max turns
        if len(self.turns) >= max_turns:
            return True, "max_turns"
        
        # Check timeout
        if self.turns:
            last_turn_time = self.turns[-1].timestamp
            if (datetime.utcnow() - last_turn_time).total_seconds() > timeout_seconds:
                return True, "timeout"
        
        # Check for natural ending phrases
        if self.turns:
            last_content = self.turns[-1].content.lower()
            ending_phrases = [
                "thank you for this discussion",
                "this has been a great conversation",
                "i think we've covered",
                "let's conclude",
                "to summarize our discussion",
                "in conclusion"
            ]
            
            if any(phrase in last_content for phrase in ending_phrases):
                return True, "natural_ending"
        
        return False, None
    
    def detect_repetition(self, similarity_threshold: float = 0.8) -> bool:
        """Detect if the conversation is becoming repetitive."""
        if len(self.turns) < 3:
            return False
        
        # Simple repetition detection based on content similarity
        # In a real implementation, you might use more sophisticated NLP techniques
        recent_turns = self.turns[-3:]
        contents = [turn.content.lower() for turn in recent_turns]
        
        # Check for exact repetitions
        if len(set(contents)) < len(contents):
            return True
        
        # Check for similar content (simplified)
        for i, content1 in enumerate(contents):
            for j, content2 in enumerate(contents[i+1:], start=i+1):
                words1 = set(content1.split())
                words2 = set(content2.split())
                
                if not words1 or not words2:
                    continue
                
                similarity = len(words1 & words2) / len(words1 | words2)
                if similarity > similarity_threshold:
                    return True
        
        return False
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history in a format suitable for LLM APIs."""
        history = []
        
        for turn in self.turns:
            # Map our roles to standard chat roles
            role = "assistant" if turn.role.startswith("assistant") else "user"
            history.append({
                "role": role,
                "content": turn.content
            })
        
        return history
    
    def calculate_quality_score(self) -> float:
        """Calculate a quality score for the conversation."""
        if not self.turns:
            return 0.0
        
        score = 0.0
        
        # Length factor (conversations with 5-8 turns are ideal)
        ideal_turns = 6.5
        length_factor = 1.0 - abs(len(self.turns) - ideal_turns) / ideal_turns
        score += max(0, length_factor) * 0.3
        
        # Diversity factor (different models used)
        diversity_factor = len(set(turn.model for turn in self.turns)) / 2.0  # Assuming 2 models max
        score += diversity_factor * 0.2
        
        # Response time factor (faster responses are better, up to a point)
        if all(turn.latency_ms for turn in self.turns):
            avg_latency = sum(turn.latency_ms for turn in self.turns) / len(self.turns)
            # Ideal latency is around 500ms
            latency_factor = 1.0 - abs(avg_latency - 500) / 1000
            score += max(0, latency_factor) * 0.2
        
        # Content quality (very simplified - length and no repetition)
        avg_length = sum(len(turn.content) for turn in self.turns) / len(self.turns)
        length_quality = min(1.0, avg_length / 200)  # 200 chars is good
        score += length_quality * 0.2
        
        # No repetition bonus
        if not self.detect_repetition():
            score += 0.1
        
        return min(1.0, score)