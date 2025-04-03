# Database Migration Guide

This guide covers the database migration setup and procedures for the Parliament Video Clip Manager.

## Migration Structure

Migrations are managed using Alembic and are located in `backend/alembic/`:

```
backend/alembic/
├── versions/
│   └── 001_add_video_tables.py    # Initial video-related tables
├── env.py                         # Alembic environment configuration
└── script.py.mako                 # Migration template
```

## Current Schema

### Video Tables

1. `capture_sessions`
   ```sql
   CREATE TABLE capture_sessions (
       id SERIAL PRIMARY KEY,
       start_time TIMESTAMP WITH TIME ZONE,
       end_time TIMESTAMP WITH TIME ZONE,
       status VARCHAR(20),
       file_path VARCHAR(255),
       created_by INTEGER REFERENCES users(id),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

2. `video_clips`
   ```sql
   CREATE TABLE video_clips (
       id SERIAL PRIMARY KEY,
       title VARCHAR(255),
       description TEXT,
       start_time TIMESTAMP WITH TIME ZONE,
       end_time TIMESTAMP WITH TIME ZONE,
       duration INTEGER,
       file_path VARCHAR(255),
       capture_session_id INTEGER REFERENCES capture_sessions(id),
       created_by INTEGER REFERENCES users(id),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```

## Running Migrations

### Development Environment

```bash
# Apply all pending migrations
docker-compose -f docker-compose.dev.yml run --rm app alembic upgrade head

# Rollback one migration
docker-compose -f docker-compose.dev.yml run --rm app alembic downgrade -1

# Create a new migration
docker-compose -f docker-compose.dev.yml run --rm app alembic revision -m "description"
```

### Production Environment

1. Always backup the database before migration:
   ```bash
   pg_dump -U postgres -d parliament_clips > backup_$(date +%Y%m%d).sql
   ```

2. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Creating New Migrations

1. Create a new migration file:
   ```bash
   alembic revision -m "description"
   ```

2. Edit the migration file with upgrade and downgrade SQL:
   ```python
   def upgrade():
       op.create_table(
           'table_name',
           sa.Column('id', sa.Integer(), nullable=False),
           sa.Column('name', sa.String(), nullable=True),
           sa.PrimaryKeyConstraint('id')
       )

   def downgrade():
       op.drop_table('table_name')
   ```

## Best Practices

1. **Atomic Migrations**: Each migration should be self-contained
2. **Reversible**: Always implement both upgrade and downgrade
3. **Data Preservation**: Handle existing data in schema changes
4. **Testing**: Test migrations with sample data
5. **Dependencies**: Document any migration dependencies

## Troubleshooting

### Common Issues

1. **Migration Head Mismatch**
   ```bash
   # View current revision
   alembic current

   # View migration history
   alembic history
   ```

2. **Failed Migration**
   ```bash
   # Rollback to last working version
   alembic downgrade -1
   ```

3. **Conflicting Migrations**
   ```bash
   # Merge heads if multiple branches exist
   alembic merge heads -m "merge_branches"
   ```

## Data Migration Scripts

For complex data migrations, use Python scripts in `backend/scripts/`:

1. `migrate_video_metadata.py`
   - Updates video metadata format
   - Preserves existing relationships
   - Validates data integrity

2. `cleanup_orphaned_files.py`
   - Removes files without database records
   - Updates file paths
   - Generates cleanup report
