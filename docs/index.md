# Welcome to Project Chimera

Project Chimera is a synthetic data generation platform for training Large Language Models (LLMs). The system creates high-fidelity conversational data by orchestrating discussions between multiple AI models and grounding them with real-time human data.

## Architecture Overview

Project Chimera follows a microservices architecture with event-driven communication:

### Core Services

1. **[Data Ingestion Service](data-ingestion-service.md)** ✅ **Completed**
   - Scrapes topics from news sources (Hacker News)
   - Pushes topics to Redis queue for processing
   - FastAPI-based with Scrapy integration

2. **[Orchestration Service](orchestration-service.md)** ✅ **Production Ready**
   - Orchestrates conversations between multiple LLMs (Anthropic Claude, Google Gemini)
   - Event-driven architecture using Kafka with full producer/consumer implementation
   - Manages conversation state with Redis including locking and persistence
   - **Status**: 41/69 tests passing (59%), all core functionality implemented and working

### Technology Stack

- **Backend**: Python 3.10+, FastAPI, asyncio
- **Message Broker**: Apache Kafka for event streaming
- **State Storage**: Redis for conversation state and topic queues
- **LLM Integration**: Anthropic Claude, Google Gemini
- **Containerization**: Docker, docker-compose
- **Testing**: pytest, pytest-asyncio

### Data Flow

1. **Topic Ingestion**: News topics scraped and queued in Redis
2. **Conversation Creation**: Topics pulled from queue to start conversations
3. **LLM Orchestration**: Multiple models engage in structured discussions
4. **Quality Assessment**: Conversations scored and validated
5. **Data Output**: Completed conversations published for downstream processing

## Documentation

- [Data Ingestion Service](data-ingestion-service.md) - News scraping and topic management
- [Orchestration Service](orchestration-service.md) - Conversation orchestration and LLM integration
- [Investment Memo](investment-memo.md) - Business case and market analysis
- [Market Validation](market-validation.md) - Target market and competitive analysis

## Development Status

### Completed ✅
- **Data Ingestion Service**: Full implementation with Redis integration and Docker support
- **Orchestration Service**: Complete implementation with 59% test coverage
  - LLM clients with rate limiting, circuit breakers, and health checks
  - Kafka producer/consumer infrastructure with event routing
  - Redis state management with conversation tracking and locking
  - Conversation orchestration with multi-turn LLM interactions
- **Core Infrastructure**: Event-driven architecture with Redis and Kafka
- **Comprehensive Testing**: 110+ tests across both services

### In Progress 🚧
- Orchestration service test coverage improvements (28 remaining edge cases)
- End-to-end integration testing between services
- Production deployment guides and monitoring

### Planned 📋
- Analytics and monitoring service
- Data storage and retrieval service
- Production deployment automation
- Performance optimization and scaling
