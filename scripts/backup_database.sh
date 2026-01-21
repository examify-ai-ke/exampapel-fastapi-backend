#!/bin/bash
#############################################
# Database Backup Script for exams_fastapi_db
#############################################

# Load environment variables
set -a
source .env
set +a

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="${DATABASE_NAME:-exams_fastapi_db}"
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5454}"
DB_USER="${DATABASE_USER:-postgres}"
DB_PASSWORD="${DATABASE_PASSWORD:-postgres_exams1}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "================================================"
echo "Starting backup of database: $DB_NAME"
echo "Timestamp: $TIMESTAMP"
echo "================================================"

# Option 1: Custom format backup (recommended for production)
# - Compressed
# - Can do selective restore
# - Use with pg_restore
CUSTOM_BACKUP="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
echo "Creating custom format backup: $CUSTOM_BACKUP"
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -F c \
  -b \
  -v \
  -f "$CUSTOM_BACKUP"

if [ $? -eq 0 ]; then
  echo "✅ Custom format backup created successfully"
  echo "   Size: $(du -h "$CUSTOM_BACKUP" | cut -f1)"
else
  echo "❌ Custom format backup failed"
  exit 1
fi

# Option 2: SQL format backup (for version control or manual inspection)
# - Plain SQL text file
# - Easy to read and edit
# - Can be used directly with psql
SQL_BACKUP="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql"
echo ""
echo "Creating SQL format backup: $SQL_BACKUP"
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --clean \
  --if-exists \
  -f "$SQL_BACKUP"

if [ $? -eq 0 ]; then
  echo "✅ SQL format backup created successfully"
  echo "   Size: $(du -h "$SQL_BACKUP" | cut -f1)"
else
  echo "❌ SQL format backup failed"
  exit 1
fi

# Create a "latest" symlink for easy access
ln -sf "$(basename "$CUSTOM_BACKUP")" "$BACKUP_DIR/latest.dump"
ln -sf "$(basename "$SQL_BACKUP")" "$BACKUP_DIR/latest.sql"

echo ""
echo "================================================"
echo "Backup completed successfully!"
echo "Custom format: $CUSTOM_BACKUP"
echo "SQL format:    $SQL_BACKUP"
echo "================================================"

# Optional: Clean up old backups (keep last 7 days)
echo ""
echo "Cleaning up old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.dump" -mtime +7 -delete
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql" -mtime +7 -delete
echo "✅ Cleanup completed"
