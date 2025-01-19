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

[License information to be added]# Il Manifesto Copertine Archive

A web application to archive and search through the front pages ("copertine") of Il Manifesto newspaper.

## Architecture

The project consists of three main components:

1. **Frontend** (Next.js 14)
   - Web interface for browsing and searching copertine
   - Built with Next.js 14 and TypeScript
   - Uses pnpm for package management
   - Containerized with Docker
   - Features server-side rendering and image caching

2. **Backend** (Python FastAPI)
   - REST API for searching copertine
   - Interfaces with Weaviate vector database
   - Handles image processing and metadata extraction
   - Containerized with Docker

3. **Database** (Weaviate)
   - Vector database storing copertine metadata and search indices
   - Connected via Docker network

## Setup

### Prerequisites
- Docker and Docker Compose
- Nginx server
- Crontab access
- Weaviate instance

### Installation

1. Clone the repository
2. Configure environment variables
3. Build and start services:
```bash
docker-compose up -d
```

### Nginx Configuration

Add these locations to your Nginx configuration:

```nginx
location /images {
    alias /path/to/images;
}

location /copertine {
    proxy_pass http://localhost:3737;
}
```

### Automated Scraping

Add this to your crontab (runs daily at 5:00 AM, Tuesday through Sunday):
```bash
0 5 * * 2-7 /path/to/your/scraping-script.sh
```

The scraping script should:
1. Fetch the latest copertina
2. Save the image to the /images directory
3. Extract metadata and store in Weaviate
4. Restart the frontend container to clear caches

## Development

### Frontend
- Located in `/frontend`
- Built with Next.js 14
- Uses Tailwind CSS for styling
- TypeScript for type safety
- Features client-side caching for performance

### Backend
- Located in `/backend`
- FastAPI application
- Poetry for dependency management
- Implements search endpoints
- Handles Weaviate integration

## Docker Setup

The application runs in Docker containers:
- Frontend container (port 3737)
- Backend container (port 8383)
- Shared network with Weaviate
- Mounted volumes for image storage

## Data Flow

1. Daily scraper collects new copertine
2. Images stored in filesystem
3. Metadata stored in Weaviate
4. Frontend serves browsing interface
5. Backend handles search requests
6. Nginx routes requests appropriately

## License

[Your license here]
