#!/bin/bash

# Script to check for conflicts between local PostgreSQL and Docker PostgreSQL
# and help resolve them

echo "Checking for PostgreSQL conflicts..."

# Check if local PostgreSQL is running
# Look for PostgreSQL processes that are NOT related to Docker
LOCAL_PG=$(ps aux | grep -v grep | grep postgres | grep -v docker | grep -v "com.docke" | grep -v "com.docker")
LOCAL_PG_COUNT=$(echo "$LOCAL_PG" | grep -v "^$" | wc -l | tr -d ' ')

# Check if Docker PostgreSQL is running
DOCKER_PG_RUNNING=0
if docker-compose -f docker-compose.dev.yml ps db | grep -q "Up"; then
    DOCKER_PG_RUNNING=1
fi

# Report findings
echo "----------------------------------------"
if [ $LOCAL_PG_COUNT -gt 0 ]; then
    echo "⚠️  Local PostgreSQL is running ($LOCAL_PG_COUNT processes)"
    echo "   This may conflict with Docker PostgreSQL on port 5432"
else
    echo "✅ No local PostgreSQL instances detected"
fi

if [ $DOCKER_PG_RUNNING -eq 1 ]; then
    echo "✅ Docker PostgreSQL is running"
else
    echo "❌ Docker PostgreSQL is not running"
fi

# Check for port conflicts
PORT_5432_USAGE=$(lsof -i :5432 | grep LISTEN)
if [ -n "$PORT_5432_USAGE" ]; then
    echo "⚠️  Port 5432 is in use:"
    echo "$PORT_5432_USAGE"
fi

echo "----------------------------------------"

# Provide resolution options
if [ $LOCAL_PG_COUNT -gt 0 ] && [ $DOCKER_PG_RUNNING -eq 1 ]; then
    echo "CONFLICT DETECTED: Both local and Docker PostgreSQL are running"
    echo ""
    echo "Options to resolve:"
    echo "1. Stop local PostgreSQL:  brew services stop postgresql@14"
    echo "2. Stop Docker PostgreSQL: docker-compose -f docker-compose.dev.yml stop db"
    echo ""
    echo "For development with Docker, option 1 is recommended."
    
    # Offer to automatically stop local PostgreSQL
    read -p "Would you like to stop local PostgreSQL now? (y/n): " STOP_LOCAL
    if [ "$STOP_LOCAL" = "y" ] || [ "$STOP_LOCAL" = "Y" ]; then
        echo "Stopping local PostgreSQL..."
        brew services stop postgresql@14
        echo "Done. You should now be able to connect to Docker PostgreSQL on port 5432."
    fi
elif [ $LOCAL_PG_COUNT -eq 0 ] && [ $DOCKER_PG_RUNNING -eq 0 ]; then
    echo "No PostgreSQL instances are running."
    echo "Start Docker PostgreSQL with: docker-compose -f docker-compose.dev.yml up -d db"
elif [ $LOCAL_PG_COUNT -gt 0 ] && [ $DOCKER_PG_RUNNING -eq 0 ]; then
    echo "Only local PostgreSQL is running."
    echo "If you want to use Docker PostgreSQL instead, first stop local PostgreSQL:"
    echo "brew services stop postgresql@14"
    echo "Then start Docker PostgreSQL: docker-compose -f docker-compose.dev.yml up -d db"
elif [ $LOCAL_PG_COUNT -eq 0 ] && [ $DOCKER_PG_RUNNING -eq 1 ]; then
    echo "Only Docker PostgreSQL is running. This is the recommended setup."
    echo "You can connect to it with TablePlus using:"
    echo "- Host: localhost"
    echo "- Port: 5432"
    echo "- Database: parliament_clips"
    echo "- Username: postgres"
    echo "- Password: postgres"
fi

echo ""
echo "For more information, see the updated setup guide: docs/setup_guide.md"
