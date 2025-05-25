# Database Management Guide

This guide covers comprehensive database management for the Parliament Video Clip Manager, including setup, rebuilding, and connecting with external SQL IDEs.

## Table of Contents
- [Database Setup](#database-setup)
- [Database Rebuild](#database-rebuild)
- [Sample Data](#sample-data)
- [Connecting with SQL IDEs](#connecting-with-sql-ides)
- [Common Database Operations](#common-database-operations)
- [Troubleshooting](#troubleshooting)

## Database Setup

The application uses PostgreSQL as its database. The database is automatically set up when you run the setup script:

```bash
./setup.sh
```

This will:
1. Create necessary database containers
2. Run migrations to set up the schema
3. Initialize the database with required tables

## Database Rebuild

If you need to completely rebuild the database (for example, after schema changes or to start with a clean slate), you can use the database rebuild functionality:

```bash
# Rebuild with clean structure (no data)
./setup.sh --rebuild-db

# Rebuild with sample data
./setup.sh --rebuild-db --with-sample-data

# Rebuild database only (skip Docker and recognition setup)
./setup.sh --rebuild-db --with-sample-data --skip-docker --skip-recognition
```

### Manual Database Operations

For more fine-grained control, you can use the dedicated database scripts:

#### Dumping the Database

```bash
# Dump structure only
./database/dump_db.sh --structure-only -o my_structure

# Dump structure and data
./database/dump_db.sh --with-data -o my_backup

# See all options
./database/dump_db.sh --help
```

#### Restoring the Database

```bash
# Restore structure only
./database/restore_db.sh --mode structure

# Restore structure with sample data
./database/restore_db.sh --mode structure --sample-data

# Restore full database from a specific dump
./database/restore_db.sh --mode full --full my_backup_full.sql

# See all options
./database/restore_db.sh --help
```

## Sample Data

The system includes a sample data script that populates the database with test data for development and testing purposes. This includes:

- Users with different roles (admin, regular user, editor)
- MPs with party and constituency information
- Capture sessions
- Video clips
- MP appearances in clips
- Transcriptions
- Social posts
- Tags

To use the sample data:

```bash
# When rebuilding the database
./setup.sh --rebuild-db --with-sample-data

# Or manually
docker exec -i the-mp-db-1 psql -h db -U postgres -d parliament_db < database/create_sample_data.sql
```

## Connecting with SQL IDEs

You can connect to the database using SQL IDEs like TablePlus, DBeaver, pgAdmin, or any other PostgreSQL-compatible client.

### Connection Details

When running in Docker (default setup):

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 5432 |
| Database | parliament_db |
| Username | postgres |
| Password | postgres |

> **Note**: The actual values may differ based on your `.env` configuration.

### TablePlus Setup

1. **Download and Install TablePlus**:
   - Download from [TablePlus website](https://tableplus.com/)
   - Install following the instructions for your OS

2. **Create a New Connection**:
   - Open TablePlus
   - Click "Create a new connection"
   - Select PostgreSQL

3. **Enter Connection Details**:
   - Name: Parliament Video Clip Manager
   - Host: localhost
   - Port: 5432
   - User: postgres
   - Password: postgres
   - Database: parliament_db

4. **Test Connection**:
   - Click "Test" to verify the connection works
   - If successful, click "Connect"

5. **Explore the Database**:
   - Browse tables in the left sidebar
   - Execute SQL queries in the query editor
   - View and edit data directly

### DBeaver Setup

1. **Download and Install DBeaver**:
   - Download from [DBeaver website](https://dbeaver.io/)
   - Install following the instructions for your OS

2. **Create a New Connection**:
   - Open DBeaver
   - Click "New Database Connection"
   - Select PostgreSQL

3. **Enter Connection Details**:
   - Host: localhost
   - Port: 5432
   - Database: parliament_db
   - Username: postgres
   - Password: postgres

4. **Test Connection**:
   - Click "Test Connection"
   - If successful, click "Finish"

## Common Database Operations

### Viewing Tables and Data

```sql
-- List all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- View table structure
\d table_name

-- Count records in a table
SELECT COUNT(*) FROM users;

-- View all users
SELECT * FROM users;
```

### Managing Users

```sql
-- Create a new admin user (password is 'password')
INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, updated_at)
VALUES ('admin@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Admin User', 'ADMIN', true, NOW(), NOW());

-- Update user role
UPDATE users SET role = 'ADMIN' WHERE email = 'user@example.com';

-- Deactivate a user
UPDATE users SET is_active = false WHERE email = 'user@example.com';
```

### Checking Enum Values

```sql
-- View all enum types
SELECT typname, enumlabel
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
ORDER BY typname, enumsortorder;

-- View values for a specific enum
SELECT enumlabel
FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
WHERE t.typname = 'post_status_enum'
ORDER BY e.enumsortorder;
```

## Troubleshooting

### Common Issues

1. **Cannot connect to database**:
   - Ensure Docker containers are running: `docker-compose -f docker-compose.dev.yml ps`
   - Check if the database container is healthy: `docker-compose -f docker-compose.dev.yml logs db`
   - Verify port mapping: `docker-compose -f docker-compose.dev.yml port db 5432`

2. **Invalid enum values**:
   - Check the enum values in the database: 
     ```sql
     SELECT enumlabel FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'enum_name';
     ```
   - Run the database rebuild with the latest schema: `./setup.sh --rebuild-db`

3. **Missing tables or columns**:
   - Run migrations to ensure schema is up to date: `docker exec the-mp-app-1 alembic upgrade head`
   - Check if tables exist: 
     ```sql
     SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
     ```

For more detailed troubleshooting, see [Database Troubleshooting Guide](troubleshooting/database_issues.md).
