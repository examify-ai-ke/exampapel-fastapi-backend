# Database Backup and Restore Guide

This guide explains how to properly backup and restore the `exams_fastapi_db` PostgreSQL database.

## Quick Start

### Create a Backup

```bash
# Automated backup with both formats
./scripts/backup_database.sh

# Manual backup (custom format - recommended)
PGPASSWORD=postgres_exams1 pg_dump -h localhost -p 5454 -U postgres -d exams_fastapi_db -F c -f backup.dump

# Manual backup (SQL format - for version control)
PGPASSWORD=postgres_exams1 pg_dump -h localhost -p 5454 -U postgres -d exams_fastapi_db --clean --if-exists -f backup.sql
```

### Restore a Backup

```bash
# Automated restore
./scripts/restore_database.sh backups/latest.dump

# Manual restore (custom format)
PGPASSWORD=postgres_exams1 pg_restore -h localhost -p 5454 -U postgres -d exams_fastapi_db backup.dump

# Manual restore (SQL format)
PGPASSWORD=postgres_exams1 psql -h localhost -p 5454 -U postgres -d exams_fastapi_db -f backup.sql
```

---

## 🎉 Automatic Database Initialization (NEW!)

**The application now automatically initializes the database from backup files on first run!**

### How It Works

1. **On First App Startup:**
   - The app checks if the database is completely empty (no tables)
   - If empty, it looks for a backup file in the project root
   - If found, it automatically restores the database from the backup
   - No manual intervention needed!

2. **On Subsequent Startups:**
   - The app detects that tables already exist
   - **No restoration happens** - your data is safe
   - Works even with app reloads during development

### Backup File Priority

The app searches for backup files in this order:

1. `exams_fastapi_db_clean_backup.dump` (in project root) ✅ **Preferred**
2. `exams_fastapi_db_clean_backup.sql` (in project root)
3. `backups/latest.dump`
4. `backups/latest.sql`

### First-Time Setup (Development)

**Scenario 1: Fresh Database**
```bash
# 1. Make sure your backup file is in the project root
ls exams_fastapi_db_clean_backup.dump

# 2. Start the app - database will auto-initialize!
cd backend/app
uvicorn app.main:app --reload
```

**Scenario 2: Existing Database**
```bash
# Database already has data - nothing happens
# The app will detect existing tables and skip initialization
uvicorn app.main:app --reload
```

### Production Deployment

For production deployment, simply:

1. **Place the backup file** in your project root before starting the app
2. **Start the application** - it will auto-initialize on first run
3. **Remove the backup file** (optional, for security)

```bash
# Production deployment example
cp exams_fastapi_db_clean_backup.dump /path/to/production/app/
cd /path/to/production/app/backend/app
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Database automatically initialized on first run!
```

### Logs to Watch

When the app starts with an empty database, you'll see:

```
🔍 Checking if database needs initialization from backup...
🆕 Database is empty - will attempt to restore from backup
📦 Restoring database from: exams_fastapi_db_clean_backup.dump
✅ Database initialization completed successfully!
📊 Restored 36 tables with 1234 total records
```

On subsequent runs:
```
🔍 Checking if database needs initialization from backup...
📊 Database already has tables - skipping backup restore
Database contains 36 tables with 1234 total records
```

---

## Backup Formats

### Custom Format (`.dump`) - **Recommended**

✅ **Best for production use**

**Advantages:**
- Compressed (smaller file size)
- Supports selective restore
- Parallel restore support for large databases
- Binary format (not human-readable but more efficient)

**How to create:**
```bash
pg_dump -h localhost -p 5454 -U postgres -d exams_fastapi_db -F c -f backup.dump
```

**How to restore:**
```bash
pg_restore -h localhost -p 5454 -U postgres -d exams_fastapi_db backup.dump
```

### SQL Format (`.sql`)

✅ **Best for version control and inspection**

**Advantages:**
- Plain text SQL file
- Easy to read and manually edit
- Can be added to git (if small)
- Good for reviewing what's being backed up

**How to create:**
```bash
pg_dump -h localhost -p 5454 -U postgres -d exams_fastapi_db --clean --if-exists -f backup.sql
```

**How to restore:**
```bash
psql -h localhost -p 5454 -U postgres -d exams_fastapi_db -f backup.sql
```

---

## Current Clean Backups

We've created two clean backup files for you:

| File | Format | Size | Use Case |
|------|--------|------|----------|
| `exams_fastapi_db_clean_backup.dump` | Custom | 368K | **Production deployments** |
| `exams_fastapi_db_clean_backup.sql` | SQL | 1.3M | **Version control & inspection** |

---

## Automated Scripts

### `scripts/backup_database.sh`

Creates both custom and SQL format backups with:
- Automatic timestamping
- Latest backup symlinks
- Cleanup of old backups (>7 days)
- Size reporting

**Usage:**
```bash
./scripts/backup_database.sh
```

**Output location:** `./backups/`

### `scripts/restore_database.sh`

Restores from either format with:
- Automatic format detection
- Safety confirmation prompt
- Connection termination
- Database recreation
- Data verification

**Usage:**
```bash
./scripts/restore_database.sh <backup_file>
```

**Examples:**
```bash
./scripts/restore_database.sh backups/latest.dump
./scripts/restore_database.sh exams_fastapi_db_clean_backup.sql
```

---

## Production Deployment Workflow

### Initial Production Setup

1. **Upload the clean backup file to your production server:**
   ```bash
   scp exams_fastapi_db_clean_backup.dump user@production-server:/path/to/app/
   ```

2. **On the production server, restore the database:**
   ```bash
   # Create the database first
   PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE exams_fastapi_db;"

   # Restore from backup
   PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d exams_fastapi_db -v exams_fastapi_db_clean_backup.dump
   ```

### Using Docker/Docker Compose

If your production uses Docker, add an init script:

**docker-compose.yml:**
```yaml
services:
  db:
    image: postgres:17
    volumes:
      - ./exams_fastapi_db_clean_backup.dump:/docker-entrypoint-initdb.d/init.dump:ro
      - ./scripts/init_db.sh:/docker-entrypoint-initdb.d/01_init.sh:ro
    environment:
      POSTGRES_DB: exams_fastapi_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
```

**scripts/init_db.sh:**
```bash
#!/bin/bash
set -e

if [ -f /docker-entrypoint-initdb.d/init.dump ]; then
  echo "Restoring database from backup..."
  pg_restore -U postgres -d exams_fastapi_db /docker-entrypoint-initdb.d/init.dump
  echo "Database restored successfully!"
fi
```

---

## Backup Strategy Recommendations

### Development
- **Frequency:** Before major changes
- **Format:** Both (custom for safety, SQL for git)
- **Retention:** 7 days
- **Location:** Local `./backups/` directory

### Production
- **Frequency:** Daily (automated via cron)
- **Format:** Custom format (compressed)
- **Retention:** 30 days minimum
- **Location:** Off-site storage (S3, backup server, etc.)

### Example Cron Job

Add to your crontab for daily backups at 2 AM:
```bash
0 2 * * * cd /path/to/app && ./scripts/backup_database.sh >> /var/log/db_backup.log 2>&1
```

---

## Troubleshooting

### Error: "database is being accessed by other users"

**Solution:** Terminate active connections first:
```bash
PGPASSWORD=postgres_exams1 psql -h localhost -p 5454 -U postgres << 'EOF'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'exams_fastapi_db' AND pid <> pg_backend_pid();
EOF
```

### Error: Foreign key constraint violations

**Solution:** Use the clean backup files we created. They restore data in the correct order.

### Backup is too large

**Solution:** Use custom format (`.dump`) which is compressed, or use gzip:
```bash
pg_dump ... | gzip > backup.sql.gz
```

### Need to restore only specific tables

**Solution:** Use custom format with selective restore:
```bash
pg_restore -h localhost -p 5454 -U postgres -d exams_fastapi_db -t User -t Role backup.dump
```

---

## Best Practices

1. ✅ **Always test your backups** by restoring them to a test database
2. ✅ **Store backups in a different location** than your database server
3. ✅ **Automate backups** using cron jobs or scheduled tasks
4. ✅ **Verify backup integrity** after creation
5. ✅ **Document your backup procedures** (like this file!)
6. ✅ **Use custom format for production** (smaller, more flexible)
7. ✅ **Keep SQL format for development** (easier to review changes)
8. ✅ **Encrypt sensitive backups** in production environments

---

## Additional Resources

- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [pg_dump Manual](https://www.postgresql.org/docs/current/app-pgdump.html)
- [pg_restore Manual](https://www.postgresql.org/docs/current/app-pgrestore.html)
