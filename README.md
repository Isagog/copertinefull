# Il Manifesto Copertine Archive

A web application to archive and search through the front pages ("copertine") of Il Manifesto newspaper.

## Overview

This project provides a searchable archive of Il Manifesto's opening stories, with automated daily updates and a modern web interface.

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
   - Provides strong BM25F text search capabilities

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
docker-compose up -d copback
docker-compose up -d copfront
```

### Nginx Configuration

Add to your Nginx configuration:
```nginx
    location /images/ {
        alias /home/mema/code/copertinefull/images/;
        http2_push_preload on;
        autoindex off;
   
        # Aggressive caching for images since they never change
        expires max;
        add_header Cache-Control "public, max-age=31536000, immutable";

        # Performance optimizations
        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
        aio threads;
        directio 512;  # For files larger than 512 bytes

        # Security headers
        add_header X-Content-Type-Options "nosniff";

        # Only allow GET and HEAD
        limit_except GET HEAD {
            deny all;
        }

        # Optional: Enable compression for JPEG if not already compressed
        # gzip on;
        # gzip_types image/jpeg;
        # gzip_min_length 1024;

        # Optional but recommended: Cross-Origin settings
        add_header Access-Control-Allow-Origin "https://dev.isagog.com";
        add_header Access-Control-Allow-Methods "GET, HEAD, OPTIONS";
        add_header Timing-Allow-Origin "https://dev.isagog.com";
    }

    location /copertine {
        proxy_pass http://127.0.0.1:3737;
        # Basic proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Updated Permissions-Policy with only widely supported features
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()";
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
```

### Automated Updates

Add to crontab (runs at 5:00 AM, Tuesday through Sunday):
```bash
# scrape the new Il Manifesto edition article (copertine) and save the image on filesystem and the data in weaviate
0 5 * * 2-7 /home/mema/code/copertinefull/refreshbind.sh  >> /home/mema/code/copertinefull/backend/scrape2.log 2>&1
```
where refreshbind.sh is:
```bash
#!/bin/bash

# Run the scraping process
/home/mema/code/copertinefull/backend/.venv/bin/python /home/mema/code/copertinefull/backend/src/scrape2.py

# Restart the container
/usr/bin/docker compose --project-directory /home/mema/mema_docker_compose/ stop copfront
/usr/bin/docker compose --project-directory /home/mema/mema_docker_compose/ start copfront
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

- Full-text BM25F search
- Image preview on hover
- Detailed image modal view
- Sort by date or relevance
- Responsive design
- Fast search response times

## License

[License information to be added]
