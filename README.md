# Copertine Search Application

A full-stack application for searching and displaying "Copertine - Il Manifesto" images with associated metadata.

## Overview

This application consists of three main components:

1. Data Ingestion Pipeline
   - Python batch processes for data processing
   - Weaviate vector database integration for storing metadata
   - File system storage for image files

2. Backend Service
   - FastAPI server implementing search endpoints
   - Integration with Weaviate for semantic search capabilities
   - Image file serving functionality

3. Frontend Application
   - Interactive search interface
   - Results display with sorting capabilities
   - Image preview and popup functionality

## Deployment

The application is containerized using Docker and can be launched using Docker Compose:

```bash
docker-compose up -d
```

This will start:
- Backend container (FastAPI server)
- Frontend container (Web application)

The data ingestion pipeline should be scheduled to run nightly at 4 AM via cron:

```bash
# /etc/cron.d/copertine-ingestion
0 4 * * * /path/to/project/scripts/run_ingestion.sh
```

# System Architecture

### Data Pipeline
- Batch processing scripts for data ingestion
- Data stored in Weaviate "Copertine" collection
- Images stored as JPG files in `/images` filesystem

### Backend
- FastAPI server exposing RESTful endpoints
- Search functionality leveraging Weaviate's semantic capabilities
- Image serving endpoints

### Frontend
- Search input interface
- Sortable results list (by date and caption)
- Image preview with hover descriptions
- Modal image viewer

## Features

- Full-text search capabilities
- Image preview on hover
- Detailed image view in popup
- Sort results by:
  - Date
  - Caption
- Responsive design
- Fast search response times

## Prerequisites

- A running instance of Weaviate
- Docker and Docker Compose installed
- Configuration through `.env` file with the following variables:
  ```
  COP_WEAVIATE_URL=localhost
  COP_WEAVIATE_API_KEY=your_weaviate_api_key
  ```

## Project Structure

The project includes an `images/` directory that is excluded from Git tracking (via `.gitignore`). This directory stores all the Copertine JPG files that are referenced by the application.

## Getting Started

1. Ensure all prerequisites are met
2. Configure your `.env` file with appropriate Weaviate connection details
3. Start the application using Docker Compose

## API Documentation

[API endpoint documentation to be added]

## Development

[Development setup and guidelines to be added]

## Contributing

[Contribution guidelines to be added]

## License

[License information to be added]