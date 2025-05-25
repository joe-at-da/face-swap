#!/bin/bash
# Script to dump the database structure and data

set -e  # Exit on any error

# Default values
DUMP_DIR="$(dirname "$0")/dumps"
STRUCTURE_ONLY=false
INCLUDE_DATA=true
OUTPUT_FILE="db_dump_$(date +%Y%m%d_%H%M%S)"

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

# Print usage information
print_usage() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  -s, --structure-only    Dump only the database structure (no data)"
  echo "  -d, --with-data         Include data in the dump (default)"
  echo "  -o, --output FILE       Specify output filename (without extension)"
  echo "  -h, --help              Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 --structure-only -o db_structure"
  echo "  $0 --with-data -o full_db_backup"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--structure-only)
      STRUCTURE_ONLY=true
      INCLUDE_DATA=false
      shift
      ;;
    -d|--with-data)
      INCLUDE_DATA=true
      STRUCTURE_ONLY=false
      shift
      ;;
    -o|--output)
      if [[ -z "$2" || "$2" == -* ]]; then
        print_error "Error: Output filename is required after -o/--output option"
        print_usage
        exit 1
      fi
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      print_usage
      exit 1
      ;;
  esac
done

# Create dumps directory if it doesn't exist
mkdir -p "$DUMP_DIR"

# Get database credentials from .env file
if [ -f ../.env ]; then
  source ../.env
else
  print_error "Error: .env file not found"
  exit 1
fi

# Set default values if not found in .env
DB_HOST=${POSTGRES_HOST:-db}
DB_PORT=${POSTGRES_PORT:-5432}
DB_NAME=${POSTGRES_DB:-parliament_db}
DB_USER=${POSTGRES_USER:-postgres}
DB_PASSWORD=${POSTGRES_PASSWORD:-postgres}

# Dump the database
print_header "Dumping database"

if [ "$STRUCTURE_ONLY" = true ]; then
  print_info "Dumping database structure only (no data)..."
  docker exec the-mp-db-1 pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --schema-only --no-owner --no-acl > "$DUMP_DIR/${OUTPUT_FILE}_structure.sql"
  
  echo "Database structure dumped to: $DUMP_DIR/${OUTPUT_FILE}_structure.sql"
else
  print_info "Dumping database structure and data..."
  
  # Dump structure
  docker exec the-mp-db-1 pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --schema-only --no-owner --no-acl > "$DUMP_DIR/${OUTPUT_FILE}_structure.sql"
  
  # Dump data
  docker exec the-mp-db-1 pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --data-only --no-owner --no-acl > "$DUMP_DIR/${OUTPUT_FILE}_data.sql"
  
  # Create a full dump as well
  docker exec the-mp-db-1 pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-acl > "$DUMP_DIR/${OUTPUT_FILE}_full.sql"
  
  echo "Database structure dumped to: $DUMP_DIR/${OUTPUT_FILE}_structure.sql"
  echo "Database data dumped to: $DUMP_DIR/${OUTPUT_FILE}_data.sql"
  echo "Full database dump saved to: $DUMP_DIR/${OUTPUT_FILE}_full.sql"
  
  # Create a symlink to the latest dump
  ln -sf "${OUTPUT_FILE}_structure.sql" "$DUMP_DIR/latest_structure.sql"
  ln -sf "${OUTPUT_FILE}_data.sql" "$DUMP_DIR/latest_data.sql"
  ln -sf "${OUTPUT_FILE}_full.sql" "$DUMP_DIR/latest_full.sql"
  
  echo "Symlinks to latest dumps created."
fi

print_header "Database dump completed successfully!"
