# Data Ingestion Service

## Responsibilities
- Fetch daily news, trending topics, and relevant articles from various APIs (e.g., news APIs, social media trends).
- Ingest small, targeted samples of real human conversational data from licensed or partnered sources.
- Standardize and pre-process incoming data into a consistent format.

## Tech Stack
- **FastAPI**: For building the API endpoints and service orchestration.
- **Scrapy**: For web scraping and data extraction from various sources.
- **Playwright**: For browser automation and scraping dynamic content.
- **Docker**: For containerized deployment and environment consistency.

## Deployment
This service is designed to be deployed using Docker. Ensure all dependencies are specified in the Dockerfile and use environment variables for configuration.

## Usage
1. Build the Docker image:
	```sh
	docker build -t data-ingestion-service .
	```
2. Run the service:
	```sh
	docker run -d -p 8000:8000 --env-file .env data-ingestion-service
	```
