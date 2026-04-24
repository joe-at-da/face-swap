#!/bin/bash

# Coolify Supabase Database Backup Configuration Script with Hetzner S3 Upload
# This script provides the proper pg_dump configuration to avoid circular foreign key constraint issues
# and uploads backups to Hetzner S3-compatible storage

# Database connection parameters
# Support both DATABASE_URL and individual parameters
parse_database_url() {
    _parse_url="$1"
    _parse_masked_url=""
    
    # Mask password in URL for logging
    if echo "$_parse_url" | grep -q "@"; then
        _parse_masked_url=$(echo "$_parse_url" | sed 's/\(:[^:@]*\)@/:***@/')
    else
        _parse_masked_url="$_parse_url"
    fi
    
    echo "Parsing DATABASE_URL: $_parse_masked_url"
    
    # Remove the postgresql:// or postgres:// prefix
    _parse_db_url="${_parse_url#postgresql://}"
    _parse_db_url="${_parse_db_url#postgres://}"
    
    if [ "$_parse_db_url" = "$_parse_url" ]; then
        echo "Warning: DATABASE_URL does not start with postgresql:// or postgres://"
        return 1
    fi
    
    # Extract user and password (everything before @)
    if ! echo "$_parse_db_url" | grep -q "@"; then
        echo "Error: DATABASE_URL missing @ separator"
        return 1
    fi
    
    _parse_user_pass="${_parse_db_url%%@*}"
    _parse_host_port_db="${_parse_db_url#*@}"
    
    # Extract user and password
    if ! echo "$_parse_user_pass" | grep -q ":"; then
        echo "Error: DATABASE_URL missing : separator in user:password"
        return 1
    fi
    
    DB_USER="${_parse_user_pass%%:*}"
    DB_PASSWORD="${_parse_user_pass#*:}"
    
    # Extract host, port, and database
    if ! echo "$_parse_host_port_db" | grep -q "/"; then
        echo "Error: DATABASE_URL missing / separator before database name"
        return 1
    fi
    
    _parse_host_port="${_parse_host_port_db%%/*}"
    DB_NAME="${_parse_host_port_db#*/}"
    
    # Remove any query parameters from DB_NAME
    DB_NAME="${DB_NAME%%\?*}"
    
    # Extract host and port
    if echo "$_parse_host_port" | grep -q ":"; then
        DB_HOST="${_parse_host_port%%:*}"
        DB_PORT="${_parse_host_port#*:}"
    else
        # No port specified, use default
        DB_HOST="$_parse_host_port"
        DB_PORT="5432"
    fi
    
    # Clean up temporary variables
    unset _parse_url _parse_masked_url _parse_db_url _parse_user_pass _parse_host_port_db _parse_host_port
    
    # Validate all components are non-empty
    if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ]; then
        echo "Error: Failed to parse all required components from DATABASE_URL"
        echo "  DB_USER: ${DB_USER:-[empty]}"
        echo "  DB_PASSWORD: ${DB_PASSWORD:+[set]}${DB_PASSWORD:-[empty]}"
        echo "  DB_HOST: ${DB_HOST:-[empty]}"
        echo "  DB_PORT: ${DB_PORT:-[empty]}"
        echo "  DB_NAME: ${DB_NAME:-[empty]}"
        return 1
    fi
    
    return 0
}

# Parse DATABASE_URL if provided, otherwise use individual parameters
if [ -n "$DATABASE_URL" ]; then
    if ! parse_database_url "$DATABASE_URL"; then
        echo "Failed to parse DATABASE_URL, falling back to individual parameters..."
        # Fall through to individual parameters
        DB_HOST="${DB_HOST:-localhost}"
        DB_PORT="${DB_PORT:-5432}"
        DB_NAME="${DB_NAME:-postgres}"
        DB_USER="${DB_USER:-postgres}"
        DB_PASSWORD="${DB_PASSWORD:-postgres}"
    fi
else
    # Use individual parameters
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-postgres}"
    DB_USER="${DB_USER:-postgres}"
    DB_PASSWORD="${DB_PASSWORD:-postgres}"
fi

# Validate all database parameters are set
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo "Error: Missing required database connection parameters!"
    echo "  DB_HOST: ${DB_HOST:-[not set]}"
    echo "  DB_PORT: ${DB_PORT:-[not set]}"
    echo "  DB_NAME: ${DB_NAME:-[not set]}"
    echo "  DB_USER: ${DB_USER:-[not set]}"
    echo "  DB_PASSWORD: ${DB_PASSWORD:+[set]}${DB_PASSWORD:-[not set]}"
    exit 1
fi

# Debug output (mask password)
echo "==============================================="
echo "Database Connection Configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: [hidden]"
echo "==============================================="

# S3 Configuration for Hetzner Object Storage
S3_ENDPOINT="${S3_ENDPOINT:-https://fsn1.your-objectstorage.com}"
S3_BUCKET="${S3_BUCKET:-veedoo-coolify}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-MP8VSZZ3VVCXYZIGXE1M}"
S3_SECRET_KEY="${S3_SECRET_KEY:-zJ2Bw32vDvsjlpvYBdBnUkllFIlR8zRPfSheAWUm}"
S3_FOLDER="${S3_FOLDER:-mp-ai-supabase-backup}"
S3_REGION="${S3_REGION:-fsn1}"

# Backup configuration
BACKUP_DIR="${BACKUP_DIR:-/tmp/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="supabase_backup_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Configure AWS CLI for Hetzner S3 (if not already configured)
configure_aws_cli() {
    echo "Configuring AWS CLI for Hetzner S3..."
    export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
    export AWS_DEFAULT_REGION="$S3_REGION"
}

# Configure AWS CLI
configure_aws_cli

echo "==============================================="
echo "Starting Supabase database backup..."
echo "Timestamp: $TIMESTAMP"
echo "Backup file: $BACKUP_DIR/$BACKUP_FILENAME"
echo "==============================================="

# Recommended pg_dump options to avoid circular foreign key constraint issues:
# --disable-triggers: Disables trigger firing during data restore (prevents constraint issues)
# --if-exists: Adds IF EXISTS to DROP statements for safer restores
# --clean: Adds DROP statements for a clean restore
# --no-owner: Don't output commands to set ownership (useful for different environments)
# --no-privileges: Don't output commands to set privileges (useful for different environments)
# --verbose: Show detailed progress

echo "Step 1: Creating database dump..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --disable-triggers \
    --if-exists \
    --clean \
    --no-owner \
    --no-privileges \
    --verbose \
    -f "$BACKUP_DIR/$BACKUP_FILENAME"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "✓ Database dump completed successfully!"
    echo "File saved to: $BACKUP_DIR/$BACKUP_FILENAME"

    # Compress the backup file
    echo "Step 2: Compressing backup..."
    gzip "$BACKUP_DIR/$BACKUP_FILENAME"
    COMPRESSED_FILENAME="${BACKUP_FILENAME}.gz"
    echo "✓ Backup compressed: $BACKUP_DIR/$COMPRESSED_FILENAME"

    # Upload to Hetzner S3
    echo "Step 3: Uploading to Hetzner S3..."
    echo "Target: s3://${S3_BUCKET}/${S3_FOLDER}/${COMPRESSED_FILENAME}"

    # Using AWS CLI with Hetzner endpoint
    aws s3 cp "$BACKUP_DIR/$COMPRESSED_FILENAME" \
        "s3://${S3_BUCKET}/${S3_FOLDER}/${COMPRESSED_FILENAME}" \
        --endpoint-url="$S3_ENDPOINT" \
        --no-verify-ssl 2>/dev/null || \
    aws s3 cp "$BACKUP_DIR/$COMPRESSED_FILENAME" \
        "s3://${S3_BUCKET}/${S3_FOLDER}/${COMPRESSED_FILENAME}" \
        --endpoint-url="$S3_ENDPOINT"

    if [ $? -eq 0 ]; then
        echo "✓ Backup uploaded successfully to S3!"

        # Construct full download URL
        # Remove trailing slash from endpoint if present
        S3_ENDPOINT_CLEAN="${S3_ENDPOINT%/}"
        # Construct the full download URL
        DOWNLOAD_URL="${S3_ENDPOINT_CLEAN}/${S3_BUCKET}/${S3_FOLDER}/${COMPRESSED_FILENAME}"
        
        echo "Download URL: ${DOWNLOAD_URL}"

        # List recent backups in S3
        echo "Step 4: Recent backups in S3:"
        aws s3 ls "s3://${S3_BUCKET}/${S3_FOLDER}/" \
            --endpoint-url="$S3_ENDPOINT" \
            --no-verify-ssl 2>/dev/null | tail -5 || \
        aws s3 ls "s3://${S3_BUCKET}/${S3_FOLDER}/" \
            --endpoint-url="$S3_ENDPOINT" | tail -5

        # Clean up old local backups (keep last 7 days)
        echo "Step 5: Cleaning up old local backups..."
        find "$BACKUP_DIR" -name "supabase_backup_*.sql.gz" -mtime +7 -delete
        echo "✓ Old local backups cleaned up (kept last 7 days)"

        # Clean up old S3 backups (keep last 30 days)
        echo "Step 6: Cleaning up old S3 backups..."
        CUTOFF_DATE=$(date -d "30 days ago" +%Y%m%d 2>/dev/null || date -v-30d +%Y%m%d)

        # List and delete old S3 backups
        aws s3 ls "s3://${S3_BUCKET}/${S3_FOLDER}/" --endpoint-url="$S3_ENDPOINT" | \
        while read -r line; do
            FILENAME=$(echo "$line" | awk '{print $4}')
            # Extract date from filename using sed (POSIX-compliant)
            FILE_DATE=$(echo "$FILENAME" | sed -n 's/.*supabase_backup_\([0-9]\{8\}\)_.*\.sql\.gz/\1/p')
            if [ -n "$FILE_DATE" ] && [ -n "$CUTOFF_DATE" ]; then
                # Compare dates (YYYYMMDD format allows numeric comparison)
                if [ "$FILE_DATE" -lt "$CUTOFF_DATE" ] 2>/dev/null; then
                    echo "  Deleting old backup: $FILENAME"
                    aws s3 rm "s3://${S3_BUCKET}/${S3_FOLDER}/${FILENAME}" \
                        --endpoint-url="$S3_ENDPOINT" --quiet
                fi
            fi
        done
        echo "✓ Old S3 backups cleaned up (kept last 30 days)"

        # Clean up local compressed file after successful S3 upload
        rm -f "$BACKUP_DIR/$COMPRESSED_FILENAME"
        echo "✓ Local backup file cleaned up to save storage space"

        echo "==============================================="
        echo "✓ BACKUP COMPLETED SUCCESSFULLY!"
        echo "  File: ${COMPRESSED_FILENAME}"
        echo "  Location: s3://${S3_BUCKET}/${S3_FOLDER}/"
        echo "  Download URL: ${DOWNLOAD_URL}"
        echo "==============================================="
    else
        echo "✗ Failed to upload backup to S3!"
        echo "Local backup is still available at: $BACKUP_DIR/$COMPRESSED_FILENAME"
        exit 1
    fi
else
    echo "✗ Database dump failed!"
    exit 1
fi

# For Coolify integration, set these environment variables in your scheduled task:
# DATABASE_URL (preferred) or individual DB parameters (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
# S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_FOLDER, S3_REGION

# Example usage:
# ./coolify-backup-config.sh
# or with DATABASE_URL:
# DATABASE_URL="postgresql://postgres:wsI7ppKHHBzEuf6ywbYw0O2XD1OaFLQo@176.9.78.50:5440/postgres" ./coolify-backup-config.sh
# or with individual parameters:
# DB_HOST=176.9.78.50 DB_PORT=5440 DB_PASSWORD=wsI7ppKHHBzEuf6ywbYw0O2XD1OaFLQo ./coolify-backup-config.sh