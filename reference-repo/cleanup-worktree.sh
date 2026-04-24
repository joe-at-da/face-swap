#!/bin/bash
# =============================================================================
# Cleanup Docker resources for git worktree
# Usage: ./cleanup-worktree.sh [options]
# =============================================================================
# This script complements setup-worktree.sh by cleaning up Docker resources
# (containers and volumes) after a worktree branch has been merged.
#
# Options:
#   -f, --force        Skip confirmation prompt
#   --keep-volumes     Stop containers but keep volumes (for potential reuse)
#   --clean-env        Also remove the .env file
#   -h, --help         Show this help message
# =============================================================================

set -e

# Parse command-line arguments
# Force is always true — cleanup should never prompt interactively.
# This is critical for CI pipelines and automated workflows where stdin is unavailable.
FORCE=true
KEEP_VOLUMES=false
CLEAN_ENV=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        --keep-volumes)
            KEEP_VOLUMES=true
            shift
            ;;
        --clean-env)
            CLEAN_ENV=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./cleanup-worktree.sh [options]"
            echo ""
            echo "Options:"
            echo "  -f, --force        Skip confirmation prompt"
            echo "  --keep-volumes     Stop containers but keep volumes (for potential reuse)"
            echo "  --clean-env        Also remove the .env file"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get the full path for unique port calculation
FULL_PATH=$(pwd)
# Get directory name for display and project naming
DIR_NAME=$(basename "$FULL_PATH")

# Hash the full path to get a unique offset (must match setup-worktree.sh)
OFFSET=$(echo "$FULL_PATH" | cksum | awk '{print $1 % 999}')

# Sanitize directory name for COMPOSE_PROJECT_NAME (alphanumeric + dash only)
# This must match the logic in setup-worktree.sh
# Include OFFSET to ensure unique container names per worktree (even if folder name is the same)
PROJECT_NAME=$(echo "${DIR_NAME}-${OFFSET}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')

# Check if docker-compose.development.yml exists
if [ ! -f "docker-compose.development.yml" ]; then
    echo "Error: docker-compose.development.yml not found in current directory"
    echo "Please run this script from the worktree root directory"
    exit 1
fi

# Define container names (based on docker-compose.development.yml)
CONTAINERS=(
    "${PROJECT_NAME}-nextjs-app"
    "${PROJECT_NAME}-supabase-kong"
    "${PROJECT_NAME}-supabase-studio"
    "${PROJECT_NAME}-supabase-db"
    "${PROJECT_NAME}-supabase-analytics"
    "${PROJECT_NAME}-supabase-vector"
    "${PROJECT_NAME}-supabase-rest"
    "${PROJECT_NAME}-supabase-auth"
    "${PROJECT_NAME}-realtime-dev"
    "${PROJECT_NAME}-supabase-minio"
    "${PROJECT_NAME}-minio-createbucket"
    "${PROJECT_NAME}-supabase-storage"
    "${PROJECT_NAME}-imgproxy"
    "${PROJECT_NAME}-supabase-meta"
    "${PROJECT_NAME}-supabase-supavisor"
)

# Define volume names
VOLUMES=(
    "${PROJECT_NAME}_supabase-db-data"
    "${PROJECT_NAME}_supabase-storage-data"
)

# Function to check if containers exist
check_containers() {
    local found=0
    for container in "${CONTAINERS[@]}"; do
        if docker ps -a --format '{{.Names}}' | grep -q "^${container}$" 2>/dev/null; then
            found=$((found + 1))
        fi
    done
    echo $found
}

# Function to check if volumes exist
check_volumes() {
    local found=0
    for volume in "${VOLUMES[@]}"; do
        if docker volume ls --format '{{.Name}}' | grep -q "^${volume}$" 2>/dev/null; then
            found=$((found + 1))
        fi
    done
    echo $found
}

# Count existing resources
EXISTING_CONTAINERS=$(check_containers)
EXISTING_VOLUMES=$(check_volumes)

# Show what will be cleaned
echo "=========================================="
echo "Cleanup Worktree: $DIR_NAME"
echo "=========================================="
echo "Project Name: $PROJECT_NAME"
echo ""
echo "Resources to clean:"
echo "  Containers: ${EXISTING_CONTAINERS}/${#CONTAINERS[@]} found"
echo "  Volumes:    ${EXISTING_VOLUMES}/${#VOLUMES[@]} found"
if [ "$CLEAN_ENV" = true ] && [ -f ".env" ]; then
    echo "  .env file:  Will be removed"
fi
echo ""

# Check if there's anything to clean
if [ "$EXISTING_CONTAINERS" -eq 0 ] && [ "$EXISTING_VOLUMES" -eq 0 ]; then
    echo "No Docker resources found for this project."
    if [ "$CLEAN_ENV" = true ] && [ -f ".env" ]; then
        if [ "$FORCE" = false ]; then
            echo ""
            read -p "Remove .env file? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -f .env
                echo "Removed .env file"
            fi
        else
            rm -f .env
            echo "Removed .env file"
        fi
    fi
    exit 0
fi

# Confirmation prompt (unless --force)
if [ "$FORCE" = false ]; then
    echo "WARNING: This will permanently delete the above resources."
    if [ "$KEEP_VOLUMES" = true ]; then
        echo "         (Volumes will be kept due to --keep-volumes flag)"
    fi
    echo ""
    read -p "Are you sure you want to continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi
fi

echo ""
echo "Cleaning up Docker resources..."
echo ""

# Export COMPOSE_PROJECT_NAME for docker compose
export COMPOSE_PROJECT_NAME="$PROJECT_NAME"

# Stop and remove containers (with or without volumes)
if [ "$KEEP_VOLUMES" = true ]; then
    echo "Stopping and removing containers (keeping volumes)..."
    docker compose -f docker-compose.development.yml down --remove-orphans 2>/dev/null || true
else
    echo "Stopping and removing containers and volumes..."
    docker compose -f docker-compose.development.yml down -v --remove-orphans 2>/dev/null || true

    # Double-check and remove any remaining volumes manually
    for volume in "${VOLUMES[@]}"; do
        if docker volume ls --format '{{.Name}}' | grep -q "^${volume}$" 2>/dev/null; then
            echo "  Removing volume: $volume"
            docker volume rm "$volume" 2>/dev/null || true
        fi
    done
fi

# Remove any orphaned containers that might have been missed
for container in "${CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$" 2>/dev/null; then
        echo "  Removing container: $container"
        docker rm -f "$container" 2>/dev/null || true
    fi
done

# Clean up Docker-created node dependencies
# These contain hardlinks with container paths (/app) that break host pnpm
echo "Removing Docker-created node dependencies..."
rm -rf .pnpm-store node_modules

# Clean up .env file if requested
if [ "$CLEAN_ENV" = true ] && [ -f ".env" ]; then
    echo "Removing .env file..."
    rm -f .env
fi

# Final summary
echo ""
echo "=========================================="
echo "Cleanup Complete"
echo "=========================================="

# Check what's left
REMAINING_CONTAINERS=$(check_containers)
REMAINING_VOLUMES=$(check_volumes)

echo "Containers removed: $((EXISTING_CONTAINERS - REMAINING_CONTAINERS))"
if [ "$KEEP_VOLUMES" = false ]; then
    echo "Volumes removed:    $((EXISTING_VOLUMES - REMAINING_VOLUMES))"
else
    echo "Volumes kept:       $EXISTING_VOLUMES (--keep-volumes)"
fi
if [ "$CLEAN_ENV" = true ]; then
    echo ".env file removed:  Yes"
fi

if [ "$REMAINING_CONTAINERS" -gt 0 ] || ([ "$KEEP_VOLUMES" = false ] && [ "$REMAINING_VOLUMES" -gt 0 ]); then
    echo ""
    echo "WARNING: Some resources could not be removed."
    echo "You may need to remove them manually."
fi

echo "=========================================="

echo ""
echo "Success!"
exit 0
