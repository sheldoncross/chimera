# Orchestration Service

## Overview

The Orchestration Service is the core component of Project Chimera's synthetic data generation platform. It orchestrates conversations between multiple Large Language Models (LLMs) using event-driven architecture with Kafka, manages conversation state with Redis, and produces high-quality conversational data for LLM training.

## Architecture

### Event-Driven Design
- **Kafka Topics**: 4 core topics for conversation lifecycle management
  - `conversation.new` - New conversation requests
  - `conversation.turn` - Individual conversation turns
  - `conversation.response` - LLM responses
  - `conversation.completed` - Finished conversations

### LLM Integration
- **Multi-Provider Support**: Anthropic Claude and Google Gemini
- **Resilient Design**: Circuit breakers, retry logic, rate limiting
- **Quality Assurance**: Response validation and quality scoring

### State Management
- **Redis Backend**: Conversation state with TTL and atomic operations
- **Concurrent Safety**: Conversation locking for parallel processing
- **Topic Queue**: Integration with data ingestion service

## Implementation Status

### ✅ Completed (Test-Driven Development)

#### Core Architecture
- **Configuration Management** (`app/config/`)
  - Environment-based settings with validation
  - Kafka-specific configuration with SSL support
  - LLM model configuration per provider

#### Data Models (`app/models/`)
- **Conversation Models**: Complete conversation lifecycle with validation
  - `ConversationTurn`: Individual turns with metadata
  - `ConversationMetadata`: Quality metrics and status tracking
  - `Conversation`: Full conversation with business logic
- **Event Models**: Kafka event schemas with type safety
  - 7 event types covering full conversation lifecycle
  - Pydantic validation and serialization
  - Event routing and error handling

#### LLM Clients (`app/clients/`)
- **Base Client**: Abstract base with common functionality
  - Rate limiting (60 requests/minute configurable)
  - Circuit breaker pattern (5 failures threshold)
  - Exponential backoff retry logic
  - Health check capabilities
- **Anthropic Client**: Claude API integration
  - Messages API format handling
  - Token counting and latency tracking
  - Error classification and handling
- **Google Client**: Gemini API integration
  - Content safety filtering
  - Usage metadata extraction
  - Quota management

#### Test Suite (`tests/`)
- **Comprehensive Coverage**: 50+ test cases across all components
- **Mock Infrastructure**: Redis, Kafka, and LLM API mocks
- **Integration Tests**: End-to-end conversation flows
- **Error Scenarios**: Failure modes and recovery testing

### 🚧 Pending Implementation

#### Kafka Infrastructure (`app/kafka/`)
- Producer with batching and partitioning
- Consumer with group management
- Event router for message handling
- Dead letter queue for failed messages

#### State Management (`app/storage/`)
- Redis client with connection pooling
- Conversation state CRUD operations
- Topic queue integration
- Metrics and monitoring

#### Workers (`app/workers/`)
- Conversation manager orchestration
- Turn processor for LLM interactions
- Background task management
- Graceful shutdown handling

#### Application (`app/`)
- FastAPI health endpoints
- Service startup/shutdown
- Metrics collection
- Logging configuration

#### Infrastructure
- Docker containerization
- docker-compose with dependencies
- Environment configuration
- Production deployment guides

## Technical Specifications

### Dependencies
```
fastapi>=0.104.0
aiokafka>=0.9.0
aioredis>=2.0.0
anthropic>=0.7.0
google-generativeai>=0.3.0
pydantic>=2.0.0
tenacity>=8.2.0
aiohttp>=3.9.0
```

### Environment Variables
```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP_ID=orchestration-service

# LLM API Keys
ANTHROPIC_API_KEY=required
GOOGLE_API_KEY=required

# Service Configuration
MAX_CONVERSATION_TURNS=10
CONVERSATION_TIMEOUT_SECONDS=300
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### Conversation Flow
1. **Topic Retrieval**: Pull topics from Redis queue (from data ingestion service)
2. **Conversation Initialization**: Create new conversation event
3. **Turn Orchestration**: Alternate between LLMs for 5-10 turns
4. **State Management**: Track conversation progress in Redis
5. **Quality Assessment**: Score conversations on completion
6. **Event Publishing**: Send completed conversations to Kafka

### Quality Metrics
- **Length Factor**: Ideal 5-8 turns per conversation
- **Model Diversity**: Multiple LLMs engaged
- **Response Quality**: Latency and content analysis
- **Natural Flow**: Coherent conversation progression
- **Completion Logic**: Smart ending detection

## Testing

### Test Structure
```
tests/
├── conftest.py              # Fixtures and mocks
├── test_conversation_manager.py  # Core orchestration logic
├── test_llm_clients.py      # LLM integration tests
├── test_kafka_integration.py    # Event handling tests
└── test_redis_state.py      # State management tests
```

### Running Tests
```bash
cd src/backend/services/orchestration_service
python -m pytest tests/ -v
```

### Test Coverage
- **Conversation Management**: 12 test scenarios
- **LLM Clients**: Error handling, rate limiting, circuit breakers
- **Kafka Integration**: Producer, consumer, event routing
- **Redis State**: CRUD operations, locking, persistence

## Next Development Phase

1. **Kafka Infrastructure Implementation**
   - Producer with reliability guarantees
   - Consumer group management
   - Event routing and error handling

2. **Redis State Management**
   - Connection pooling and failover
   - Atomic state updates
   - Performance optimization

3. **Service Workers**
   - Conversation orchestration engine
   - Background processing
   - Resource management

4. **Production Readiness**
   - Docker containerization
   - Monitoring and alerting
   - Deployment automation

## Integration Points

### Data Ingestion Service
- **Topic Queue**: Consumes topics from `topics:queue` Redis list
- **Data Format**: Compatible with existing topic schema

### Downstream Services
- **Completed Conversations**: Published to `conversation.completed` topic
- **Event Format**: Structured for analytics and storage

### Infrastructure Dependencies
- **Kafka Cluster**: Message broker for event streaming
- **Redis Instance**: State storage and queue management
- **LLM APIs**: Anthropic and Google services