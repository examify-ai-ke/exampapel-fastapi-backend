# Production Deployment Guide

## Overview

This guide explains how to deploy the Examify backend to production using Docker Compose.

**Architecture:**
- **API Domain**: api.exampapel.com
- **Frontend Domain**: exampapel.com (separate repository)
- **Database**: PostgreSQL 17 in Docker container
- **Cache**: Redis in Docker container
- **Background Jobs**: Celery worker + beat
- **Reverse Proxy**: Caddy with automatic HTTPS

---

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 22.04 LTS or newer
- **RAM**: Minimum 4GB (8GB recommended)
- **CPU**: 2+ cores
- **Disk**: 50GB+ SSD
- **Docker**: Version 24.0+ 
- **Docker Compose**: Version 2.20+

### Domain Setup

**Required DNS Records:**

```
Type    Name                Value               TTL
A       api.exampapel.com   YOUR_SERVER_IP     300
```

Verify DNS propagation:
```bash
dig api.exampapel.com
# Should show your server IP
```

---

## Step 1: Server Setup

### Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (if not already allowed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

---

## Step 2: Deploy Backend Code

### Option A: Using Git (Recommended)

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/yourusername/exampapel-fastapi-backend.git
sudo chown -R $USER:$USER exampapel-fastapi-backend
cd exampapel-fastapi-backend
```

### Option B: Upload Files

```bash
# From your local machine
rsync -avz --progress \
  /path/to/local/exampapel-fastapi-backend/ \
  user@your-server:/opt/exampapel-fastapi-backend/
```

---

## Step 3: Configure Environment

```bash
cd /opt/exampapel-fastapi-backend

# Copy environment template
cp .env.production.example .env.production

# Edit with secure values
nano .env.production
```

### Critical Variables to Change:

```bash
# Generate random secret key (32+ characters)
SECRET_KEY=your_very_long_random_secret_key_here

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output to ENCRYPT_KEY

# Set strong passwords
DATABASE_PASSWORD=your_strong_database_password
REDIS_PASSWORD=your_strong_redis_password
FIRST_SUPERUSER_PASSWORD=your_admin_password

# Update email settings
MAIL_SMTP_SERVER=your_smtp_server
MAIL_SMTP_USERNAME=your_email
MAIL_SMTP_PASSWORD=your_email_password
```

---

## Step 4: Prepare Database Backup

If you want to initialize with data:

```bash
# Make sure backup file is in project root
ls -lh exams_fastapi_db_clean_backup.dump

# Should show: 368K file
```

The database will **automatically initialize** from this backup on first run!

---

## Step 5: Deploy

```bash
# Make deployment script executable
chmod +x scripts/deploy_production.sh

# Run deployment
./scripts/deploy_production.sh
```

The script will:
1. ✅ Build Docker images
2. ✅ Start all services
3. ✅ Initialize database from backup (if empty)
4. ✅ Run health checks
5. ✅ Show service status

---

## Step 6: Verify Deployment

### Check Services

```bash
# View all containers
docker compose -f docker-compose.prod.yml ps

# Should show all services as "Up" and "healthy"
```

### Test API

```bash
# Health check (local)
curl http://localhost:8000/api/v1/health

# Health check (domain - wait for DNS + HTTPS setup)
curl https://api.exampapel.com/api/v1/health
```

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f examify_backend_prod

# Check database initialization
docker compose -f docker-compose.prod.yml logs examify_backend_prod | grep -i "initialization\|backup"
```

---

## Step 7: HTTPS Setup

Caddy automatically handles HTTPS with Let's Encrypt!

**Wait 1-2 minutes** after deployment, then test:

```bash
curl -I https://api.exampapel.com/api/v1/health

# Should return: HTTP/2 200
```

If HTTPS fails:
- Verify DNS points to your server
- Check Caddy logs: `docker compose -f docker-compose.prod.yml logs examify_caddy_prod`
- Ensure ports 80 and 443 are open in firewall

---

## Frontend Integration

Your Next.js frontend (exampapel.com) should use these API settings:

### Environment Variables for Frontend

```bash
# Frontend .env.production
NEXT_PUBLIC_API_URL=https://api.exampapel.com
NEXT_PUBLIC_API_VERSION=v1
```

### CORS Configuration

Backend is already configured to allow:
- `https://exampapel.com`
- `https://www.exampapel.com`

### Example API Calls from Frontend

```javascript
// Fetch exam papers
const response = await fetch('https://api.exampapel.com/api/v1/exampaper');
const papers = await response.json();
```

---

## Maintenance

### View Logs

```bash
# Real-time logs
docker compose -f docker-compose.prod.yml logs -f

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart examify_backend_prod
```

### Update Deployment

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

### Database Backup

```bash
# Create backup
./scripts/backup_database.sh

# Backups stored in: ./backups/
```

### Stop All Services

```bash
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (CAUTION: deletes data!)
docker compose -f docker-compose.prod.yml down -v
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs examify_backend_prod

# Check service health
docker inspect examify_backend_prod | grep -A 10 Health
```

### Database Connection Failed

```bash
# Check database is running
docker compose -f docker-compose.prod.yml ps examify_database

# Check database logs
docker compose -f docker-compose.prod.yml logs examify_database

# Test connection
docker exec examify_backend_prod env | grep DATABASE
```

### HTTPS Not Working

```bash
# Check Caddy logs
docker compose -f docker-compose.prod.yml logs examify_caddy_prod

# Verify DNS
dig api.exampapel.com

# Test HTTP (should redirect to HTTPS)
curl -I http://api.exampapel.com
```

### Out of Disk Space

```bash
# Clean up Docker
docker system prune -a --volumes

# Check disk usage
df -h
docker system df
```

---

## Security Checklist

- [ ] Changed all default passwords in `.env.production`
- [ ] Generated unique `SECRET_KEY` and `ENCRYPT_KEY`
- [ ] Firewall configured (ports 80, 443, 22 only)
- [ ] HTTPS working (automatic via Caddy)
- [ ] Database password is strong
- [ ] Redis password is set
- [ ] Environment file permissions: `chmod 600 .env.production`
- [ ] Regular backups scheduled
- [ ] Server patches up to date

---

## Monitoring

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

### Health Endpoints

- Backend: `https://api.exampapel.com/api/v1/health`
- Database: Check via backend logs
- Redis: Check via backend logs

---

## Quick Reference

```bash
# Start services
./scripts/deploy_production.sh

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart service
docker compose -f docker-compose.prod.yml restart examify_backend_prod

# Stop all
docker compose -f docker-compose.prod.yml down

# Backup database
./scripts/backup_database.sh

# Shell into container
docker exec -it examify_backend_prod /bin/sh
```

---

## Support

For issues or questions:
- Check logs: `docker compose -f docker-compose.prod.yml logs`
- Review [DATABASE_BACKUP_RESTORE.md](docs/DATABASE_BACKUP_RESTORE.md)
- Email: support@exampapel.com
