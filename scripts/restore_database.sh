#!/bin/bash
#############################################
# Database Restore Script for exams_fastapi_db
#############################################

# Load environment variables
set -a
source .env
set +a

# Configuration
DB_NAME="${DATABASE_NAME:-exams_fastapi_db}"
DB_HOST="${DATABASE_HOST:-localhost}"
DB_PORT="${DATABASE_PORT:-5454}"
DB_USER="${DATABASE_USER:-postgres}"
DB_PASSWORD="${DATABASE_PASSWORD:-postgres_exams1}"

# Check if backup file is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <backup_file>"
  echo ""
  echo "Examples:"
  echo "  $0 backups/latest.dump       # Restore from custom format"
  echo "  $0 backups/latest.sql        # Restore from SQL format"
  echo "  $0 exams_fastapi_db_clean_backup.dump"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Error: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "================================================"
echo "Database Restore"
echo "================================================"
echo "Backup file: $BACKUP_FILE"
echo "Database:    $DB_NAME"
echo "Host:        $DB_HOST:$DB_PORT"
echo "User:        $DB_USER"
echo "================================================"
echo ""

# Ask for confirmation
read -p "⚠️  This will DROP and recreate the database. Continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
  echo "Restore cancelled."
  exit 0
fi

echo "Step 1: Terminating active connections..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" << EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
EOF

echo "Step 2: Dropping existing database..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "Step 3: Creating fresh database..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME WITH ENCODING = 'UTF8' LOCALE = 'en_US.UTF-8';"

echo "Step 4: Restoring backup..."

# Detect backup format and restore accordingly
if [[ "$BACKUP_FILE" == *.dump ]]; then
  echo "Detected custom format backup, using pg_restore..."
  PGPASSWORD="$DB_PASSWORD" pg_restore \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -v \
    "$BACKUP_FILE"
elif [[ "$BACKUP_FILE" == *.sql ]]; then
  echo "Detected SQL format backup, using psql..."
  PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$BACKUP_FILE"
else
  echo "❌ Error: Unknown backup format. Use .dump or .sql file"
  exit 1
fi

if [ $? -eq 0 ]; then
  echo ""
  echo "================================================"
  echo "✅ Database restored successfully!"
  echo "================================================"
  
  # Show table counts
  echo ""
  echo "Verifying data..."
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
SELECT 
    tablename,
    (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
FROM (
    SELECT 
        tablename, 
        query_to_xml(format('SELECT COUNT(*) as cnt FROM %I', tablename), false, true, '') as xml_count
    FROM pg_tables
    WHERE schemaname = 'public' 
    AND tablename NOT LIKE 'pg_%'
) t
WHERE (xpath('/row/cnt/text()', xml_count))[1]::text::int > 0
ORDER BY row_count DESC
LIMIT 10;
EOF
else
  echo ""
  echo "❌ Restore failed! Check the error messages above."
  exit 1
fi
