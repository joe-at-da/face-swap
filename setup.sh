#!/bin/bash
# Parliament Video Clip Manager - Complete Setup Script
# This script sets up the entire project environment, including Docker containers,
# database initialization, and facial recognition components.

set -e  # Exit on any error

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m" # No Color

# Print section header
print_header() {
  echo -e "\n${BOLD}${GREEN}=== $1 ===${NC}\n"
}

# Print info message
print_info() {
  echo -e "${YELLOW}$1${NC}"
}

# Print error message
print_error() {
  echo -e "${RED}$1${NC}"
}

# Check if Docker is installed
check_docker() {
  print_header "Checking Docker installation"
  
  if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
  fi
  
  if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
  fi
  
  echo "Docker and Docker Compose are installed."
}

# Create necessary directories
create_directories() {
  print_header "Creating necessary directories"
  
  mkdir -p data/media/clips
  mkdir -p data/media/captures
  mkdir -p data/media/thumbnails
  mkdir -p data/mp_photos
  mkdir -p data/face_profiles
  mkdir -p data/audio_extracts
  mkdir -p data/temp
  
  echo "Directories created successfully."
}

# Check if .env file exists, create if not
setup_env_file() {
  print_header "Setting up environment file"
  
  if [ ! -f .env ]; then
    print_info "Creating .env file from template..."
    cp .env.example .env
    echo ".env file created. You may want to edit it with your specific settings."
  else
    echo ".env file already exists."
  fi
}

# Build and start Docker containers
start_docker_containers() {
  print_header "Building and starting Docker containers"
  
  print_info "Building containers (this may take a few minutes)..."
  docker-compose -f docker-compose.dev.yml build
  
  print_info "Starting containers..."
  docker-compose -f docker-compose.dev.yml up -d
  
  echo "Docker containers started successfully."
}

# Fix NumPy compatibility issues
fix_numpy_compatibility() {
  print_header "Fixing NumPy compatibility for facial recognition"
  
  print_info "Applying NumPy fix in the app container..."
  docker exec the-mp-app-1 bash /app/backend/fix_numpy.sh
  
  echo "NumPy compatibility fix applied successfully."
}

# Initialize database
initialize_database() {
  print_header "Initializing database"
  
  print_info "Running database migrations..."
  docker exec the-mp-app-1 alembic upgrade head
  
  echo "Database initialized successfully."
}

# Setup facial recognition
setup_facial_recognition() {
  print_header "Setting up facial recognition"
  
  print_info "Running facial recognition setup script..."
  docker exec the-mp-app-1 python /app/scripts/setup_facial_recognition.py
  
  echo "Facial recognition setup completed successfully."
}

# Generate sample MP encodings
generate_mp_encodings() {
  print_header "Generating sample MP encodings"
  
  print_info "Running MP encodings generation script..."
  docker exec the-mp-app-1 python /app/scripts/generate_mp_encodings.py
  
  echo "Sample MP encodings generated successfully."
}

# Print setup completion message
print_completion() {
  print_header "Setup completed successfully!"
  
  echo -e "${GREEN}The Parliament Video Clip Manager has been set up successfully.${NC}"
  echo ""
  echo "You can access the following services:"
  echo "- Backend API: http://localhost:8000"
  echo "- Frontend: http://localhost:3000"
  echo "- Prometheus: http://localhost:9090"
  echo "- Grafana: http://localhost:3001"
  echo ""
  echo "To stop the services, run:"
  echo "  docker-compose -f docker-compose.dev.yml down"
  echo ""
  echo "To start the services again, run:"
  echo "  docker-compose -f docker-compose.dev.yml up -d"
  echo ""
  echo "For more information, see the documentation in the docs/ directory."
}

# Main function
main() {
  print_header "Parliament Video Clip Manager - Setup"
  
  # Check if script is run with sudo/root
  if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root or with sudo."
    exit 1
  fi
  
  # Run setup steps
  check_docker
  create_directories
  setup_env_file
  start_docker_containers
  fix_numpy_compatibility
  initialize_database
  setup_facial_recognition
  generate_mp_encodings
  print_completion
}

# Run main function
main
