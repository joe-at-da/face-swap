#!/bin/bash
# Script to restore the database from a dump file

set -e  # Exit on any error

# Default values
DUMP_DIR="$(dirname "$0")/dumps"
STRUCTURE_FILE="latest_structure.sql"
DATA_FILE="latest_data.sql"
FULL_FILE="latest_full.sql"
RESTORE_MODE="full"  # Options: structure, data, full
INCLUDE_SAMPLE_DATA=false

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
  echo "  -m, --mode MODE         Restore mode: structure, data, or full (default: full)"
  echo "  -s, --structure FILE    Specify structure dump file (default: latest_structure.sql)"
  echo "  -d, --data FILE         Specify data dump file (default: latest_data.sql)"
  echo "  -f, --full FILE         Specify full dump file (default: latest_full.sql)"
  echo "  --sample-data           Include sample data after structure restore"
  echo "  -h, --help              Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 --mode structure"
  echo "  $0 --mode data --data custom_data_dump.sql"
  echo "  $0 --mode full --full full_backup.sql"
  echo "  $0 --mode structure --sample-data"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mode)
      if [[ -z "$2" || "$2" == -* ]]; then
        print_error "Error: Mode is required after -m/--mode option"
        print_usage
        exit 1
      fi
      if [[ "$2" != "structure" && "$2" != "data" && "$2" != "full" ]]; then
        print_error "Error: Mode must be 'structure', 'data', or 'full'"
        print_usage
        exit 1
      fi
      RESTORE_MODE="$2"
      shift 2
      ;;
    -s|--structure)
      if [[ -z "$2" || "$2" == -* ]]; then
        print_error "Error: Structure file is required after -s/--structure option"
        print_usage
        exit 1
      fi
      STRUCTURE_FILE="$2"
      shift 2
      ;;
    -d|--data)
      if [[ -z "$2" || "$2" == -* ]]; then
        print_error "Error: Data file is required after -d/--data option"
        print_usage
        exit 1
      fi
      DATA_FILE="$2"
      shift 2
      ;;
    -f|--full)
      if [[ -z "$2" || "$2" == -* ]]; then
        print_error "Error: Full dump file is required after -f/--full option"
        print_usage
        exit 1
      fi
      FULL_FILE="$2"
      shift 2
      ;;
    --sample-data)
      INCLUDE_SAMPLE_DATA=true
      shift
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

# Check if dump files exist
if [[ "$RESTORE_MODE" == "structure" || "$RESTORE_MODE" == "full" ]]; then
  if [[ ! -f "$DUMP_DIR/$STRUCTURE_FILE" ]]; then
    print_error "Error: Structure dump file not found: $DUMP_DIR/$STRUCTURE_FILE"
    exit 1
  fi
fi

if [[ "$RESTORE_MODE" == "data" || "$RESTORE_MODE" == "full" ]]; then
  if [[ "$RESTORE_MODE" == "data" && ! -f "$DUMP_DIR/$DATA_FILE" ]]; then
    print_error "Error: Data dump file not found: $DUMP_DIR/$DATA_FILE"
    exit 1
  fi
  
  if [[ "$RESTORE_MODE" == "full" && ! -f "$DUMP_DIR/$FULL_FILE" ]]; then
    print_error "Error: Full dump file not found: $DUMP_DIR/$FULL_FILE"
    exit 1
  fi
fi

# Restore the database
print_header "Restoring database"

# Drop and recreate the database
print_info "Dropping and recreating the database..."
docker exec the-mp-db-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';
  DROP DATABASE IF EXISTS $DB_NAME;
  CREATE DATABASE $DB_NAME;
"

case "$RESTORE_MODE" in
  structure)
    print_info "Restoring database structure..."
    docker exec -i the-mp-db-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$DUMP_DIR/$STRUCTURE_FILE"
    
    if [ "$INCLUDE_SAMPLE_DATA" = true ]; then
      print_info "Including sample data..."
      if [ -f "$DUMP_DIR/sample_data.sql" ]; then
        docker exec -i the-mp-db-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$DUMP_DIR/sample_data.sql"
      else
        print_error "Warning: Sample data file not found: $DUMP_DIR/sample_data.sql"
        print_info "Falling back to latest data dump..."
        if [ -f "$DUMP_DIR/$DATA_FILE" ]; then
          docker exec -i the-mp-db-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$DUMP_DIR/$DATA_FILE"
        else
          print_error "Error: Latest data dump not found: $DUMP_DIR/$DATA_FILE"
        fi
      fi
    fi
    ;;
    
  data)
    print_info "Restoring database data only..."
    docker exec -i the-mp-db-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$DUMP_DIR/$DATA_FILE"
    ;;
    
  full)
    print_info "Restoring full database (structure and data)..."
    docker exec -i the-mp-db-1 psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" < "$DUMP_DIR/$FULL_FILE"
    ;;
esac

# Run migrations to ensure everything is up to date
print_info "Running database migrations to ensure schema is up to date..."
docker exec the-mp-app-1 alembic upgrade head

print_header "Database restore completed successfully!"
