# Coolify Scheduled Tasks Configuration

This document provides the exact configuration needed to set up all scheduled tasks in Coolify to replace the Supabase pg_cron jobs.

## Prerequisites

1. **Environment Variable**: Ensure `CRON_SECRET` is set in your Coolify environment variables
2. **Deploy Application**: Deploy your Next.js app with the new API routes first
3. **Apply Migration**: Run the migration to remove pg_cron jobs from Supabase

## Scheduled Tasks Configuration

### 1. Parliament Daily Sync

**Purpose**: Syncs parliament member data daily

```bash
# Name
Parliament Daily Sync

# Command
curl -X POST "http://localhost:3000/api/cron/parliament-daily-sync" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 600

# Cron Expression
0 2 * * *

# Description
Daily parliament data synchronization at 2 AM UTC
```

### 2. Parliament Event Daily Sync

**Purpose**: Syncs parliament event data daily

```bash
# Name
Parliament Event Daily Sync

# Command
curl -X POST "http://localhost:3000/api/cron/parliament-event-sync" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 600

# Cron Expression
30 3 * * *

# Description
Daily parliament event synchronization at 3:30 AM UTC
```

### 3. Process Embedding Queue

**Purpose**: Processes embedding jobs from PGMQ queue

```bash
# Name
Process Embedding Queue

# Command
curl -X POST "http://localhost:3000/api/cron/process-embedding-queue" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 300

# Cron Expression
* * * * *

# Description
Process embedding queue every minute
```

### 4. Process RunPod Retries

**Purpose**: Processes failed RunPod clip creation jobs with automatic retry mechanism

```bash
# Name
Process RunPod Retries

# Command
curl -X POST "http://localhost:3000/api/cron/process-runpod-retries" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 300

# Cron Expression
*/10 * * * *

# Description
Process RunPod retry queue every 10 minutes - retries failed clip creation jobs up to 3 times
```

## Alternative: Using External URL

If you prefer to call the external URL instead of localhost:

```bash
# Replace localhost with your domain
curl -X POST "https://your-domain.com/api/cron/parliament-daily-sync" \
  -H "Authorization: Bearer ${CRON_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{}' \
  --max-time 600
```

## Environment Variables Required

Make sure these are set in your Coolify environment:

```bash
CRON_SECRET=your-secure-random-secret-key
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-role-key
# ... other environment variables
```

## Testing the Endpoints

You can test each endpoint individually:

```bash
# Test Parliament Daily Sync
curl -X POST "http://localhost:3000/api/cron/parliament-daily-sync" \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{}'

# Test Parliament Event Sync
curl -X POST "http://localhost:3000/api/cron/parliament-event-sync" \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{}'

# Test Embedding Queue Processing
curl -X POST "http://localhost:3000/api/cron/process-embedding-queue" \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{}'

# Test RunPod Retry Processing
curl -X POST "http://localhost:3000/api/cron/process-runpod-retries" \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{}'

# Test RunPod Retry Status
curl -X GET "http://localhost:3000/api/runpod/retry-status" \
  -H "Content-Type: application/json"
```

## Cron Expression Reference

```bash
# Every minute
* * * * *

# Every 5 minutes
*/5 * * * *

# Every hour at minute 0
0 * * * *

# Every day at 2 AM
0 2 * * *

# Every day at 3:30 AM
30 3 * * *

# Every Monday at 9 AM
0 9 * * 1

# Every weekday at 6 AM
0 6 * * 1-5
```

## Monitoring and Logs

- **Coolify Logs**: Check your application logs in Coolify dashboard
- **API Response**: Each endpoint returns success/failure status
- **Console Logs**: Detailed logging in Next.js application logs
- **Database Logs**: Functions still log to transcript_embedding_logs table

## Migration Steps

1. **Deploy Application**: Deploy with new API routes
2. **Apply Migration**: Run `supabase db push` to apply RunPod retry system migration
3. **Configure Coolify**: Add the 4 scheduled tasks above
4. **Test**: Manually trigger each endpoint to verify functionality
5. **Monitor**: Check logs to ensure scheduled tasks are running

## Benefits

✅ **No pg_cron dependency** - Works with any PostgreSQL version  
✅ **Better error handling** - API-level error responses and logging  
✅ **Easy testing** - Can manually trigger any endpoint  
✅ **Integrated monitoring** - Uses your app's logging infrastructure  
✅ **Environment consistency** - Uses same environment as your app  
✅ **Scalable** - Works with horizontal scaling  
✅ **Platform agnostic** - Works with any scheduler, not just Coolify  
✅ **Automatic retries** - RunPod failures retry up to 3 times with 10-minute delays  
✅ **Smart retry logic** - Only retries recoverable errors (timeouts, server errors)  
✅ **Retry monitoring** - Full visibility into retry attempts and success rates

## RunPod Retry System

The RunPod retry system provides automatic failure recovery for clip creation jobs:

### **Retry Logic**

- **Max Attempts**: 3 retries per job
- **Delay**: 10 minutes between retry attempts
- **Smart Filtering**: Only retries server errors, timeouts, and network issues
- **Permanent Failures**: Client errors (invalid data) are not retried

### **Monitoring**

- **Status Endpoint**: `/api/runpod/retry-status` - View retry queue metrics and health
- **Processing Logs**: All retry attempts logged in `runpod_processing_logs` table
- **Queue Metrics**: PGMQ provides queue length, message age, and processing stats

### **Error Types**

- **Retryable**: Timeouts, server errors (5xx), network issues, RunPod service errors
- **Non-Retryable**: Invalid data, authentication errors, malformed requests (4xx)

The system automatically queues failed jobs for retry and processes them every 10 minutes via the Coolify scheduled task.
