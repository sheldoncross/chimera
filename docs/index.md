# Welcome to Project Chimera

Project Chimera is a synthetic data generation platform for training Large Language Models (LLMs). The system creates high-fidelity conversational data by orchestrating discussions between multiple AI models and grounding them with real-time human data.

## Architecture Overview

Project Chimera follows a microservices architecture with event-driven communication:

### Core Services

1. **[Data Ingestion Service](data-ingestion-service.md)** ✅ **Completed**
   - Scrapes topics from news sources (Hacker News)
   - Pushes topics to Redis queue for processing
   - FastAPI-based with Scrapy integration

2. **[Orchestration Service](orchestration-service.md)** 🚧 **In Development**
   - Orchestrates conversations between multiple LLMs
   - Event-driven architecture using Kafka
   - Manages conversation state with Redis
   - **Status**: Core architecture and tests completed, implementation in progress

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
- Data ingestion service with Redis integration
- Orchestration service architecture and test suite
- Docker containerization for ingestion service
- Comprehensive test coverage

### In Progress 🚧
- Orchestration service implementation
- Kafka infrastructure setup
- End-to-end integration testing

### Planned 📋
- Analytics and monitoring service
- Data storage and retrieval service
- Production deployment automation
- Performance optimization and scaling
