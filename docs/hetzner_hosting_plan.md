# Hetzner Hosting Plan for Parliament Video Clip Manager

## Application Components & Requirements

### 1. Core Services

#### API Server (FastAPI)
- **Requirements**: 
  - CPU: 4+ cores
  - RAM: 8GB+
  - SSD: 100GB+
- **Hetzner Solution**: 
  - CPX51 Dedicated Server (€49/month)
  - 8 vCPU, 32GB RAM, 360GB NVMe
  - Ubuntu 22.04 LTS

#### Database (PostgreSQL)
- **Requirements**:
  - CPU: 4+ cores
  - RAM: 16GB+
  - SSD: 256GB+
  - Regular backups
- **Hetzner Solution**:
  - AX41 Dedicated Server (€69/month)
  - 8 vCPU, 32GB RAM, 2x512GB NVMe
  - RAID 1 configuration for data safety
  - Automated backup system

### 2. Video Processing

#### Media Processing Server
- **Requirements**:
  - CPU: 8+ cores for transcoding
  - RAM: 32GB+ for video processing
  - SSD: 512GB+ for temporary storage
  - GPU (optional): For faster processing
- **Hetzner Solution**:
  - AX51 Dedicated Server (€79/month)
  - 16 vCPU, 64GB RAM, 2x512GB NVMe
  - Optional: Add RTX A2000 GPU (+€29/month)

#### Video Storage
- **Requirements**:
  - 5TB+ storage capacity
  - High bandwidth
  - Regular backups
- **Hetzner Solution**:
  - Storage Box (€29.90/month)
  - 5TB storage
  - Unlimited traffic
  - Daily backups included

### 3. Caching & Queue

#### Redis Cache
- **Requirements**:
  - RAM: 8GB+
  - Fast storage
  - Low latency
- **Hetzner Solution**:
  - CPX31 Cloud Server (€19.90/month)
  - 4 vCPU, 8GB RAM
  - Dedicated to Redis

#### Message Queue (Celery)
- **Requirements**:
  - CPU: 2+ cores
  - RAM: 4GB+
- **Hetzner Solution**:
  - Runs on API server
  - No additional server needed

### 4. Content Delivery

#### CDN Options
1. **Hetzner + Cloudflare (Recommended)**
   - Cloudflare Pro Plan (€20/month)
   - Global CDN network
   - DDoS protection
   - SSL certificates
   - Easy setup

2. **Pure Hetzner**
   - Load Balancer (€9.90/month)
   - Multiple locations in Europe
   - Direct network connection
   - Limited global reach

### 5. High Availability Setup

#### Load Balancing
- **Hetzner Load Balancer** (€9.90/month)
  - TCP/HTTP(S) load balancing
  - Health checks
  - SSL termination
  - Multiple backend servers

#### Backup Servers
- **Standby API Server**: CPX51 (€49/month)
- **Standby DB Server**: AX41 (€69/month)
- Activated when needed

## Total Cost Breakdown

### Minimal Setup
1. API + Celery Server: €49/month
2. Database Server: €69/month
3. Storage Box (5TB): €29.90/month
4. Redis Server: €19.90/month
5. Load Balancer: €9.90/month
6. Cloudflare Pro: €20/month
**Total: €197.70/month** (~£170/month)

### Production Setup (Recommended)
1. API + Celery Server: €49/month
2. Database Server: €69/month
3. Media Processing Server: €79/month
4. Storage Box (5TB): €29.90/month
5. Redis Server: €19.90/month
6. Load Balancer: €9.90/month
7. Cloudflare Pro: €20/month
8. Standby Servers: €118/month
**Total: €394.70/month** (~£340/month)

## Advantages of Full Hetzner Setup

1. **Cost Efficiency**
   - Predictable pricing
   - No bandwidth costs
   - No hidden fees
   - Better price/performance ratio

2. **Performance**
   - Dedicated hardware
   - NVMe storage
   - High bandwidth
   - Low latency in Europe

3. **Control**
   - Full server access
   - Custom configurations
   - No vendor lock-in
   - Direct hardware access

4. **Location**
   - EU data centers
   - GDPR compliance
   - Low latency for UK users
   - Multiple locations available

## Implementation Steps

1. **Initial Setup**
   - Order primary servers
   - Configure networking
   - Set up monitoring
   - Deploy core services

2. **Data Management**
   - Configure PostgreSQL
   - Set up Redis
   - Implement backup system
   - Configure storage

3. **Video Processing**
   - Set up processing server
   - Configure transcoding
   - Implement queue system
   - Test processing pipeline

4. **High Availability**
   - Configure load balancer
   - Set up failover
   - Test redundancy
   - Monitor performance

5. **Content Delivery**
   - Set up Cloudflare
   - Configure SSL
   - Optimize caching
   - Test delivery

## Conclusion

Hetzner can handle all hosting requirements for the Parliament Video Clip Manager. The recommended setup provides:
- Robust infrastructure
- High performance
- Cost efficiency
- Scalability
- European data centers
- Full control over infrastructure

The only recommended external service is Cloudflare for CDN, which provides better global content delivery than a pure Hetzner solution.
