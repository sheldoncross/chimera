"""Application settings and configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application configuration settings."""
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_consumer_group_id: str = Field(default="orchestration-service", env="KAFKA_CONSUMER_GROUP_ID")
    kafka_auto_offset_reset: str = Field(default="latest", env="KAFKA_AUTO_OFFSET_RESET")
    kafka_enable_auto_commit: bool = Field(default=False, env="KAFKA_ENABLE_AUTO_COMMIT")
    
    # Kafka Topics
    topic_conversation_new: str = Field(default="conversation.new", env="TOPIC_CONVERSATION_NEW")
    topic_conversation_turn: str = Field(default="conversation.turn", env="TOPIC_CONVERSATION_TURN")
    topic_conversation_response: str = Field(default="conversation.response", env="TOPIC_CONVERSATION_RESPONSE")
    topic_conversation_completed: str = Field(default="conversation.completed", env="TOPIC_CONVERSATION_COMPLETED")
    
    # LLM API Configuration
    anthropic_api_key: str = Field(env="ANTHROPIC_API_KEY")
    google_api_key: str = Field(env="GOOGLE_API_KEY")
    
    # LLM Model Configuration
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    google_model: str = Field(default="gemini-pro", env="GOOGLE_MODEL")
    
    # Conversation Settings
    max_conversation_turns: int = Field(default=10, env="MAX_CONVERSATION_TURNS")
    min_conversation_turns: int = Field(default=5, env="MIN_CONVERSATION_TURNS")
    conversation_timeout_seconds: int = Field(default=300, env="CONVERSATION_TIMEOUT_SECONDS")
    conversation_ttl_seconds: int = Field(default=86400, env="CONVERSATION_TTL_SECONDS")  # 24 hours
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_window_seconds: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")
    
    # Retry Configuration
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay_seconds: float = Field(default=1.0, env="RETRY_DELAY_SECONDS")
    retry_exponential_base: float = Field(default=2.0, env="RETRY_EXPONENTIAL_BASE")
    
    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(default=5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_timeout_seconds: int = Field(default=60, env="CIRCUIT_BREAKER_TIMEOUT_SECONDS")
    
    # Application Settings
    app_name: str = Field(default="Orchestration Service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # FastAPI Settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    
    # Health Check Settings
    health_check_interval_seconds: int = Field(default=30, env="HEALTH_CHECK_INTERVAL_SECONDS")
    
    # Performance Settings
    max_concurrent_conversations: int = Field(default=100, env="MAX_CONCURRENT_CONVERSATIONS")
    worker_pool_size: int = Field(default=10, env="WORKER_POOL_SIZE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def kafka_bootstrap_servers_list(self) -> List[str]:
        """Get Kafka bootstrap servers as a list."""
        return [server.strip() for server in self.kafka_bootstrap_servers.split(",")]
    
    def get_llm_model_config(self, provider: str) -> dict:
        """Get LLM model configuration for a specific provider."""
        if provider == "anthropic":
            return {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
                "max_tokens": 2048,
                "temperature": 0.7
            }
        elif provider == "google":
            return {
                "api_key": self.google_api_key,
                "model": self.google_model,
                "max_output_tokens": 2048,
                "temperature": 0.7
            }
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def validate_required_settings(self) -> None:
        """Validate that all required settings are present."""
        required_fields = [
            "anthropic_api_key",
            "google_api_key"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")


# Global settings instance
def get_settings():
    """Get settings instance."""
    return Settings()

# Only create global instance if not in testing mode
if not os.getenv("TESTING", "false").lower() == "true":
    try:
        settings = Settings()
        settings.validate_required_settings()
    except ValueError:
        # In development, create settings with warnings but don't fail
        settings = None
else:
    settings = None