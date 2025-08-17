# Data Ingestion Service

The data ingestion service is the core technical component of this repository. It is a containerized application that uses FastAPI to provide an API for controlling the scraping jobs.

## Architecture

The service uses a distributed architecture with the following components:

*   **FastAPI:** Provides a web interface for scheduling and managing scraping jobs.
*   **Beautiful Soup:** Used for parsing HTML and XML documents.
*   **Redis:** Used as a message broker for distributed scraping. It manages the queue of URLs to be scraped and tracks duplicate requests.
*   **Docker:** The entire service is containerized using Docker and orchestrated with `docker-compose.yml`.

## Building and Running

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

## API Endpoints

The data ingestion service exposes the following API endpoints:

*   `GET /api/v1/scrape/news`: Schedules a scraping job for news articles.
    *   **Query Parameters:**
        *   `start_urls` (optional): A comma-separated list of URLs to scrape.
*   `GET /api/v1/clear_scrape_queue`: Clears the Redis queue for news scraping and the duplicate filter.

## Development Conventions

*   **Dependencies:** Python dependencies are managed in `requirements.txt`.
*   **Configuration:** Environment variables are used for configuration and are managed with a `.env` file.