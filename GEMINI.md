# Project Chimera: Gemini Context

This document provides a comprehensive overview of the Project Chimera repository for the Gemini CLI.

## Project Overview

Project Chimera is a multi-faceted project focused on market validation and investment analysis. It includes a documentation suite and a backend data ingestion service. The primary goal of the project appears to be gathering and analyzing data to support business decisions.

### Key Components

*   **Documentation:** The `/docs` directory contains market validation and investment memos.
*   **Data Ingestion Service:** The `/src/backend/services/data-ingestion-service` directory contains a sophisticated data ingestion service built with Python, FastAPI, Scrapy, and Docker. This service is designed to scrape news and other data from the web in a distributed and scalable manner.

## Data Ingestion Service

The data ingestion service is the core technical component of this repository. It is a containerized application that uses Scrapy for web scraping and FastAPI to provide an API for controlling the scraping jobs.

### Architecture

The service uses a distributed architecture with the following components:

*   **FastAPI:** Provides a web interface for scheduling and managing scraping jobs.
*   **Scrapy:** The core web scraping engine.
*   **Redis:** Used as a message broker for `scrapy-redis` to enable distributed scraping. It manages the queue of URLs to be scraped and tracks duplicate requests.
*   **Docker:** The entire service is containerized using Docker and orchestrated with `docker-compose.yml`.

### Building and Running

To build and run the data ingestion service, use the following commands from the `/src/backend/services/data-ingestion-service` directory:

1.  **Build the Docker image:**
    ```sh
    docker build -t data-ingestion-service .
    ```

2.  **Run the service with Docker Compose:**
    ```sh
    docker-compose up -d
    ```

This will start the `data-ingestion-service` and the `redis` container. The service will be available at `http://localhost:8000`.

### API Endpoints

The data ingestion service exposes the following API endpoints:

*   `GET /api/v1/scrape/news`: Schedules a scraping job for news articles.
    *   **Query Parameters:**
        *   `start_urls` (optional): A comma-separated list of URLs to scrape. If not provided, it defaults to `https://news.ycombinator.com`.
*   `GET /api/v1/clear_scrape_queue`: Clears the Redis queue for news scraping and the duplicate filter.

### Development Conventions

*   **Dependencies:** Python dependencies are managed in `requirements.txt`.
*   **Configuration:** Environment variables are used for configuration and are managed with a `.env` file.
*   **Scraping:** Web scraping is performed by Scrapy spiders located in `src/backend/services/data-ingestion-service/app/services/scraper/spiders`. The current implementation includes a spider for scraping Hacker News.
*   **Distributed Scraping:** The project uses `scrapy-redis` to enable distributed scraping. The `ScrapyIngestionService` pushes start URLs to a Redis list, and the Scrapy spiders consume from this list.
