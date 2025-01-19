# Il Manifesto Copertine Archive

A web application to archive and search through the front pages ("copertine") of Il Manifesto newspaper.

## Overview

This project provides a searchable archive of Il Manifesto's front pages, with automated daily updates and a modern web interface.

## Architecture

The system consists of three main components:

1. **Frontend** (Next.js 14)
   - Web interface for browsing and searching copertine
   - Built with Next.js 14 and TypeScript
   - Uses pnpm for package management
   - Features server-side rendering and image caching
   - Runs in Docker container on port 3737

2. **Backend** (Python FastAPI)
   - REST API for searching copertine
   - Interfaces with Weaviate vector database
   - Handles image processing and metadata extraction
   - Runs in Docker container on port 8383

3. **Database** (Weaviate)
   - Vector database storing copertine metadata and search indices
   - Connected via Docker network
   - Provides semantic search capabilities

## Setup

### Prerequisites
- Docker and Docker Compose
- Nginx server
- Crontab access
- Weaviate instance

### Environment Configuration

Backend environment variables (.env):
```
COP_WEAVIATE_URL=127.0.0.1
COP_WEAVIATE_API_KEY=your_weaviate_api_key
COP_COPERTINE_COLLNAME=Copertine
COP_VISION_MODELNAME=gpt-4-vision-preview
COP_OLDEST_DATE=2013-03-27
```

### Installation

1. Clone the repository
2. Configure environment variables
3. Start services:
```bash
docker-compose up -d
```

### Nginx Configuration

Add to your Nginx configuration:
```nginx
location /images {
    alias /path/to/images;
}

location /copertine {
    proxy_pass http://localhost:3737;
}
```

### Automated Updates

Add to crontab (runs at 5:00 AM, Tuesday through Sunday):
```bash
0 5 * * 2-7 /path/to/project/scripts/update_copertine.sh
```

The update process:
1. Scrapes the latest copertina
2. Saves image to /images directory
3. Extracts metadata to Weaviate
4. Restarts frontend container to clear caches

## Development

### Frontend
- Located in `/frontend`
- Next.js 14 with TypeScript
- Tailwind CSS for styling
- Client-side caching for performance
- Docker container with mounted volumes

### Backend
- Located in `/backend`
- FastAPI application
- Poetry for dependency management
- Weaviate integration
- Docker container with mounted volumes

## Data Flow

1. Daily scraper collects new copertine
2. Images stored in filesystem
3. Metadata stored in Weaviate
4. Frontend serves browsing interface
5. Backend handles search requests
6. Nginx routes requests appropriately

## Docker Setup

Services run in containers:
- Frontend: port 3737
- Backend: port 8383
- Shared Docker network with Weaviate
- Mounted volumes for image storage

## Features

- Full-text and semantic search
- Image preview on hover
- Detailed image modal view
- Sort by date or relevance
- Responsive design
- Fast search response times

## License

[License information to be added]
