# Docker Setup Guide for Parliament Video Clip Manager

This guide provides detailed instructions for setting up the Parliament Video Clip Manager using Docker, with special focus on the facial recognition components.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git for cloning the repository
- At least 4GB of RAM available for Docker
- At least 10GB of free disk space

## Quick Setup

For a quick and complete setup, you can use the provided setup script:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/yourusername/the-mp.git
cd the-mp

# Make the setup script executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

The setup script will:
1. Check if Docker and Docker Compose are installed
2. Create necessary directories
3. Set up environment files
4. Build and start Docker containers
5. Fix NumPy compatibility issues for facial recognition
6. Initialize the database
7. Set up facial recognition components
8. Generate sample MP encodings

## Manual Setup

If you prefer to set up the system manually, follow these steps:

### 1. Create Required Directories

```bash
mkdir -p data/media/clips
mkdir -p data/media/captures
mkdir -p data/media/thumbnails
mkdir -p data/mp_photos
mkdir -p data/face_profiles
mkdir -p data/audio_extracts
mkdir -p data/temp
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your specific settings
nano .env
```

### 3. Build and Start Docker Containers

```bash
# Build the containers
docker-compose -f docker-compose.dev.yml build

# Start the containers
docker-compose -f docker-compose.dev.yml up -d
```

### 4. Fix NumPy Compatibility Issues

The facial recognition system requires a specific version of NumPy to work with OpenCV:

```bash
# Apply the NumPy fix in the app container
docker exec the-mp-app-1 bash /app/backend/fix_numpy.sh
```

### 5. Initialize Database

```bash
# Run database migrations
docker exec the-mp-app-1 alembic upgrade head
```

### 6. Set Up Facial Recognition

```bash
# Run facial recognition setup script
docker exec the-mp-app-1 python /app/scripts/setup_facial_recognition.py

# Generate sample MP encodings
docker exec the-mp-app-1 python /app/scripts/generate_mp_encodings.py
```

## Container Structure

The Docker setup includes the following containers:

1. **app**: FastAPI backend server
   - Handles API requests
   - Processes video capture requests
   - Manages facial recognition

2. **frontend**: Next.js frontend application
   - Provides the user interface
   - Communicates with the backend API

3. **db**: PostgreSQL database
   - Stores application data
   - Manages user accounts, video metadata, and recognition results

4. **redis**: Redis server
   - Handles caching
   - Manages message queues for background tasks

5. **celery**: Celery worker
   - Processes background tasks
   - Handles long-running operations like video processing

6. **prometheus**: Prometheus monitoring
   - Collects metrics from the application

7. **grafana**: Grafana dashboard
   - Visualizes application metrics

## Facial Recognition Components

The facial recognition system consists of several components:

1. **MP Encodings**: Face encodings of Members of Parliament stored in `/app/data/mp_encodings.json`

2. **Face Detection Scripts**:
   - `identify_speakers.py`: Identifies speakers in videos using facial recognition
   - `detect_unique_faces.py`: Detects unique faces in videos
   - `process_video_faces.py`: Processes videos to detect and identify faces

3. **Facial Recognition Service**: Backend service that manages facial recognition operations

## Common Issues and Troubleshooting

### NumPy Compatibility Issues

If you encounter errors related to NumPy and OpenCV compatibility, run the NumPy fix script:

```bash
docker exec the-mp-app-1 bash /app/backend/fix_numpy.sh
```

### Missing MP Encodings

If facial recognition is not working due to missing MP encodings, generate sample encodings:

```bash
docker exec the-mp-app-1 python /app/scripts/generate_mp_encodings.py
```

### Container Access Issues

If you need to access a container for debugging:

```bash
# Access the app container
docker exec -it the-mp-app-1 bash

# Access the frontend container
docker exec -it the-mp-frontend-1 bash
```

### Viewing Logs

To view logs for troubleshooting:

```bash
# View logs for all containers
docker-compose -f docker-compose.dev.yml logs

# View logs for a specific container
docker-compose -f docker-compose.dev.yml logs app

# Follow logs in real-time
docker-compose -f docker-compose.dev.yml logs -f app
```

## Maintenance

### Updating the Application

To update the application after pulling changes from the repository:

```bash
# Rebuild and restart containers
docker-compose -f docker-compose.dev.yml up -d --build
```

### Backing Up Data

To back up the application data:

```bash
# Back up the database
docker exec the-mp-db-1 pg_dump -U postgres parliament_clips > backup_$(date +%Y%m%d).sql

# Back up media files
tar -czf media_backup_$(date +%Y%m%d).tar.gz data/media
```

### Cleaning Up

To clean up unused Docker resources:

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune
```

## Sharing the Project

When sharing the project with others, provide them with:

1. The repository URL
2. This Docker setup guide
3. Any specific environment variables they need to set

They can then use the setup script or follow the manual setup instructions to get the system running.

## Next Steps

After setting up the Docker environment:

1. Access the frontend at http://localhost:3000
2. Log in with the default credentials (admin@parliament.uk / admin123)
3. Explore the application features
4. Try capturing video from Parliament TV and using facial recognition

For more information, refer to the other documentation files in the `docs/` directory.
