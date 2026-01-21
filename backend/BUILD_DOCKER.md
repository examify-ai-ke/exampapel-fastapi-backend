# Building Docker Image with Database Backup

This guide explains how to build the Docker image for production deployment with automatic database initialization.

## Prerequisites

Before building the Docker image, ensure you have:

1. ✅ The clean database backup file: `exams_fastapi_db_clean_backup.dump`
2. ✅ Docker installed on your system
3. ✅ The backup file placed in the project root directory

## File Structure

Your project structure should look like this:

```
exampapel-fastapi-backend/
├── exams_fastapi_db_clean_backup.dump  ← Backup file here
├── backend/
│   ├── Dockerfile                       ← Docker build file
│   └── app/
│       └── ... (application code)
└── ...
```

## Building the Image

### Step 1: Place the Backup File

Make sure the backup file is in the project root:

```bash
# From the project root
ls -lh exams_fastapi_db_clean_backup.dump

# Should show something like:
# -rw-r--r-- 1 user user 368K Jan 21 13:00 exams_fastapi_db_clean_backup.dump
```

### Step 2: Build the Docker Image

```bash
# From the backend directory
cd backend

# Build the image
docker build -t exampapel-backend:latest .

# Or with version tag
docker build -t exampapel-backend:v1.0.0 .
```

The Dockerfile will:
1. Copy all application code
2. **Copy the database backup file** from parent directory
3. Install all dependencies
4. Set up the environment

### Step 3: Verify the Backup File is Included

```bash
# Check if the backup file is in the image
docker run --rm exampapel-backend:latest ls -lh /code/exams_fastapi_db_clean_backup.dump

# Should show:
# -rw-r--r-- 1 root root 368K Jan 21 13:00 /code/exams_fastapi_db_clean_backup.dump
```

## Running the Container

### Using Docker

```bash
docker run -d \
  --name exampapel-backend \
  -p 8000:8000 \
  -e DATABASE_HOST=your-db-host \
  -e DATABASE_PORT=5432 \
  -e DATABASE_USER=postgres \
  -e DATABASE_PASSWORD=your-password \
  -e DATABASE_NAME=exams_fastapi_db \
  exampapel-backend:latest \
  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using Docker Compose

```yaml
version: '3.8'

services:
  backend:
    image: exampapel-backend:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_HOST=db
      - DATABASE_PORT=5432
      - DATABASE_USER=postgres
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
      - DATABASE_NAME=exams_fastapi_db
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    depends_on:
      - db
  
  db:
    image: postgres:17
    environment:
      - POSTGRES_DB=exams_fastapi_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

## Automatic Database Initialization

On first container startup:

1. **Application starts** and checks if database is empty
2. **Finds backup file** at `/code/exams_fastapi_db_clean_backup.dump`
3. **Automatically restores** the database from the backup
4. **Application ready** with all data loaded!

### Expected Logs

```
🚀 Starting database initialization check...
📦 Step 1: Checking for database backup file...
🔍 Checking if database needs initialization from backup...
🆕 Database is empty - will attempt to restore from backup
Found backup file: /code/exams_fastapi_db_clean_backup.dump
📦 Restoring database from: exams_fastapi_db_clean_backup.dump
✅ Database initialization completed successfully!
📊 Restored 36 tables with 1234 total records
```

## Important Notes

### ⚠️ Backup File Must Exist Before Building

The Docker build will **fail** if the backup file doesn't exist:

```bash
# Error you might see:
COPY failed: file not found in build context or excluded by .dockerignore: 
stat exams_fastapi_db_clean_backup.dump: file does not exist
```

**Solution:** Make sure the backup file is in the project root before building.

### 🔒 Security Considerations

**Production Best Practice:**

1. **Build the image** with the backup file for easy deployment
2. **Push to registry** (DockerHub, AWS ECR, etc.)
3. **Deploy** - database auto-initializes on first run
4. **(Optional) Rebuild without backup** for subsequent versions

**Alternative Approach (More Secure):**

Instead of including the backup in the image, you can:
- Use Docker volumes to mount the backup file
- Use init containers in Kubernetes
- Restore database manually before starting the app

```bash
# Using volume mount
docker run -v /path/to/backup:/code/backup.dump ...
```

## Troubleshooting

### Backup File Not Found During Build

**Error:**
```
COPY failed: file not found in build context
```

**Solution:**
```bash
# Make sure you're in the correct directory
pwd  # Should show: .../exampapel-fastapi-backend/backend

# Check parent directory has the backup
ls -l ../exams_fastapi_db_clean_backup.dump
```

### Backup Not Restoring in Container

**Check if file exists in container:**
```bash
docker exec -it exampapel-backend ls -l /code/exams_fastapi_db_clean_backup.dump
```

**View application logs:**
```bash
docker logs exampapel-backend | grep -i "backup\|initialization"
```

### PostgreSQL Client Tools Not Found

**Error:**
```
pg_restore: command not found
```

**Solution:** Update the Dockerfile to install PostgreSQL client:
```dockerfile
RUN apt-get update && apt-get install -y postgresql-client
```

## Building Without the Backup File

If you want to build an image **without** the automatic initialization:

1. Comment out the COPY line in `backend/Dockerfile`:
   ```dockerfile
   # COPY ../exams_fastapi_db_clean_backup.dump /code/
   ```

2. Build the image:
   ```bash
   docker build -t exampapel-backend:latest .
   ```

3. Restore database manually before starting the container

## Next Steps

After building and deploying:

1. ✅ **Verify** the application started successfully
2. ✅ **Check logs** to confirm database was initialized
3. ✅ **Test** by accessing the API endpoints
4. ✅ **Secure** your database credentials using secrets management
5. ✅ **Set up** regular backups using the provided backup scripts

---

For more information about database backup and restore, see [DATABASE_BACKUP_RESTORE.md](../docs/DATABASE_BACKUP_RESTORE.md)
