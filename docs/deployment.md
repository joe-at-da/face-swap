# Deployment Guide

## Hosting Architecture

### Infrastructure Overview

1. **Single Server Setup** (Hetzner AX41)
   - €69/month (~£59)
   - 8 vCPU
   - 32GB RAM
   - 2x512GB NVMe SSDs (RAID 1)
   - Unlimited traffic

2. **Core Components**
   All running on the same server:
   - FastAPI Backend
   - PostgreSQL Database
   - Redis Cache
   - Celery Workers
   - Video Storage
   - Media Processing

3. **External Services**
   - Cloudflare (Free tier)
     - CDN
     - SSL certificates
     - DDoS protection

## Deployment Steps

### 1. Server Setup
```bash
# Update system
apt update && apt upgrade -y

# Install Docker and Docker Compose
apt install docker.io docker-compose -y

# Install monitoring tools
apt install htop nginx prometheus node-exporter -y
```

### 2. Docker Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  celery:
    build: .
    command: celery -A app.worker worker --loglevel=info
    volumes:
      - ./data:/data
    depends_on:
      - redis
      - db

volumes:
  postgres_data:
  redis_data:
```

### 3. Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /data/static;
    }

    location /media {
        alias /data/media;
    }
}
```

### 4. Backup Strategy
```bash
# Daily database backup
0 0 * * * pg_dump -U postgres app > /backup/db/app_$(date +%Y%m%d).sql

# Weekly system backup
0 0 * * 0 tar -czf /backup/system/backup_$(date +%Y%m%d).tar.gz /data
```

### 5. Monitoring Setup
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'app'
    static_configs:
      - targets: ['localhost:8000']
```

## Resource Management

### Storage Planning
- Videos stored in `/data/media`
- Database in `/data/postgres`
- Regular cleanup of old files
- Compression for video files

### Memory Allocation
- PostgreSQL: 8GB
- Redis: 4GB
- Application: 8GB
- Video Processing: 8GB
- System: 4GB

### Backup Strategy
1. **Database**
   - Daily dumps
   - Keep last 7 days
   - Weekly archives

2. **Media Files**
   - Weekly incremental backups
   - Monthly full backups
   - Off-site storage

## Scaling Strategy

### 1. Initial Phase
- Monitor resource usage
- Optimize configurations
- Implement caching

### 2. Storage Expansion
When needed:
- Add Hetzner Storage Box (1TB)
- Move media files
- Update paths

### 3. Performance Scaling
If required:
- Separate database
- Add load balancer
- Split services

## Security Setup

### 1. Basic Security
```bash
# UFW Firewall
ufw allow ssh
ufw allow http
ufw allow https
ufw enable

# Fail2ban
apt install fail2ban
systemctl enable fail2ban
```

### 2. SSL Configuration
```bash
# Using Cloudflare SSL
apt install certbot
certbot certonly --dns-cloudflare
```

### 3. Database Security
```bash
# PostgreSQL configuration
listen_addresses = 'localhost'
ssl = on
```

## Maintenance Procedures

### Daily Tasks
- Check system logs
- Monitor disk usage
- Verify backups

### Weekly Tasks
- Review performance metrics
- Clean old backups
- Update system packages

### Monthly Tasks
- Full backup verification
- Security updates
- Performance optimization

## Emergency Procedures

### 1. Server Down
```bash
# Quick health check
systemctl status docker
journalctl -xe
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d
```

### 2. Backup Restoration
```bash
# Database restore
pg_restore -U postgres -d app latest_backup.sql

# Media files restore
tar -xzf backup.tar.gz -C /data/media
```

## Monitoring Dashboard

Access monitoring at:
- System: http://your-ip:9090
- Application: http://your-ip:8000/metrics
- Node: http://your-ip:9100/metrics

## Cost Management

### Monthly Costs
- Server: €69 (~£59)
- Bandwidth: Included
- Backups: Local storage
- CDN: Free (Cloudflare)

### Optional Additions
- Storage Box: €9.90/month (1TB)
- Backup Box: €9.90/month (1TB)

## Getting Started

1. Order Hetzner AX41 server
2. Follow setup steps above
3. Deploy application
4. Configure monitoring
5. Set up backups
6. Add Cloudflare
