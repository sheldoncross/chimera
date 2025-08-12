# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Chimera is a synthetic data generation platform for training Large Language Models (LLMs). The system creates high-fidelity conversational data by orchestrating discussions between multiple AI models and grounding them with real-time human data. This addresses the AI industry's data scarcity problem by providing premium training data for instruction tuning, safety & alignment, reward model training, and domain-specific fine-tuning.

## Architecture

The project follows a microservices architecture with the main component being the **Data Ingestion Service**:

- **Backend Services**: Located in `src/backend/services/`
- **Data Ingestion Service**: FastAPI-based service that handles news scraping and data collection
- **Container Architecture**: Each service is containerized using Docker with docker-compose orchestration
- **Data Flow**: Redis-based queue system for managing scraping jobs and deduplication

## Development Commands

### Data Ingestion Service

Navigate to the service directory:
```bash
cd src/backend/services/data-ingestion-service
```

**Local Development:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI service locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Docker Development:**
```bash
# Build the service
docker build -t data-ingestion-service .

# Run with docker-compose (includes Redis)
docker-compose up -d

# View logs
docker-compose logs -f data-ingestion-service

# Stop services
docker-compose down
```

**Testing the Service:**
```bash
# Schedule a news scrape
curl "http://localhost:8000/api/v1/scrape/news"

# Clear the scrape queue
curl "http://localhost:8000/api/v1/clear_scrape_queue"

# Health check
curl "http://localhost:8000/"
```

## Key Components

### Data Ingestion Service (`src/backend/services/data-ingestion-service/`)

- **FastAPI Application** (`app/main.py`): Main application entry point
- **API Endpoints** (`app/api/endpoints.py`): REST endpoints for triggering scrapes
- **Ingestion Service** (`app/services/ingestion.py`): Core logic for managing Redis queues
- **News Spider** (`app/services/scraper/spiders/news_spider.py`): Scrapy spider for Hacker News
- **Docker Configuration**: Uses Python 3.10-slim with uvicorn server on port 8000

### Environment Configuration

The service requires a `.env` file with Redis configuration:
- `REDIS_HOST`: Redis server hostname (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379) 
- `REDIS_PASSWORD`: Redis password (optional)

### Dependencies

**Python Stack:**
- FastAPI for REST API framework
- Scrapy + scrapy-redis for distributed web scraping
- Redis for queue management and deduplication
- Pydantic for data validation
- Python-dotenv for environment configuration

## Business Context

This codebase supports a B2B synthetic data platform targeting:
- AI model developers and startups
- AI safety & alignment research labs  
- Enterprise AI teams building domain-specific models

The current implementation focuses on data ingestion from news sources as a foundation for the broader synthetic data generation ecosystem.