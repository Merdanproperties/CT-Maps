# Automatic Recovery & Self-Healing System

This application now includes a comprehensive automatic recovery system that keeps all services running and automatically recovers from failures.

## 🛡️ Protection Features

### 1. **Automatic Service Recovery**
- **Backend Auto-Restart**: If backend crashes, it automatically restarts
- **Database Reconnection**: Automatically reconnects to database if connection is lost
- **Frontend Resilience**: Frontend continues working even if backend is temporarily down
- **Health Monitoring**: Continuous health checks every 5-30 seconds

### 2. **Multi-Layer Recovery Strategy**

#### Layer 1: Connection Retry
- Automatic retry with exponential backoff (1s, 2s, 4s)
- Up to 3 retry attempts per request
- Only retries on network/server errors

#### Layer 2: Health-Based Recovery
- Detects service failures immediately
- Waits for automatic recovery (2-10 seconds)
- Attempts reconnection with backoff

#### Layer 3: Process-Level Recovery
- Watchdog script monitors processes
- Automatically restarts crashed services
- Verifies health after restart

#### Layer 4: Database Recovery
- Automatic database connection pool refresh
- Reconnection attempts on failure
- Connection health monitoring

### 3. **Graceful Degradation**
- App continues working with cached data when backend is down
- Clear status indicators show what's working
- User-friendly error messages with recovery actions

## 🚀 Usage

### Option 1: Watchdog Mode (Recommended for Production)

The watchdog automatically keeps everything running:

```bash
./scripts/watchdog.sh
```

This will:
- Start backend and frontend if not running
- Monitor processes every 10 seconds
- Automatically restart any crashed service
- Verify health after restart
- Log all actions

### Option 2: Orchestrated Startup

Start all services with proper health checks:

```bash
./scripts/start_all.sh
```

This will:
- Check and free ports if needed
- Start backend with health verification
- Start frontend after backend is ready
- Wait for services to be healthy
- Show status and log locations

### Option 3: Manual with Auto-Recovery

Start services manually - they'll still auto-recover:

```bash
# Terminal 1
cd backend
source venv/bin/activate
uvicorn main:app --reload

# Terminal 2
cd frontend
npm run dev
```

The frontend will automatically:
- Monitor backend health
- Retry failed requests
- Show connection status
- Attempt recovery when needed

## 🔍 Monitoring

### Connection Status Banner

The app shows a banner at the top:
- **Green**: All systems operational ✅
- **Red**: Service issue detected ⚠️
- **Recover Button**: Manual recovery trigger
- **Check Button**: Manual health check

### Recovery Actions

When a service fails, the system automatically:

1. **Detects Failure** (within 5 seconds)
2. **Waits for Recovery** (2-10 seconds with backoff)
3. **Attempts Reconnection** (up to 3 times)
4. **Notifies User** (if recovery fails after 3 attempts)
5. **Continues Monitoring** (keeps trying in background)

### Logs

All recovery actions are logged:
- **Backend**: `logs/backend.log`
- **Frontend**: `logs/frontend.log`
- **Watchdog**: `logs/watchdog.log`

## 🛠️ Recovery Scenarios

### Scenario 1: Backend Crashes
**What Happens:**
1. Health check detects failure (5 seconds)
2. Frontend shows red status banner
3. Automatic retry attempts begin
4. Watchdog detects process death (10 seconds)
5. Watchdog restarts backend
6. Health check confirms recovery
7. Frontend automatically reconnects
8. Green status banner appears

**User Experience:** Brief red banner, automatic recovery, no action needed

### Scenario 2: Database Connection Lost
**What Happens:**
1. Database query fails
2. Backend detects connection issue
3. Automatic connection pool refresh
4. Reconnection attempt
5. Health check verifies recovery
6. Normal operation resumes

**User Experience:** Brief delay, automatic recovery, no errors shown

### Scenario 3: Network Interruption
**What Happens:**
1. Request fails with network error
2. Automatic retry with exponential backoff
3. Up to 3 retry attempts
4. If all fail, shows error with recovery option
5. Continues monitoring in background
6. Auto-reconnects when network restored

**User Experience:** Automatic retries, clear error if persistent, easy recovery

### Scenario 4: Port Conflict
**What Happens:**
1. Startup script detects port in use
2. Kills existing process
3. Waits for port to be free
4. Starts service on clean port
5. Verifies health

**User Experience:** Automatic resolution, no manual intervention

## 📊 Health Check Endpoints

### Backend Health
```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "api": "operational"
}
```

### Frontend Health
The frontend automatically checks backend health every 5 seconds.

## 🔧 Configuration

### Health Check Intervals
- **Frontend → Backend**: 5 seconds
- **Backend → Database**: 30 seconds
- **Watchdog → Processes**: 10 seconds

### Retry Configuration
- **Max Retries**: 3 attempts
- **Initial Delay**: 1 second
- **Backoff**: Exponential (1s, 2s, 4s)
- **Max Delay**: 10 seconds

### Recovery Timeouts
- **Health Check Timeout**: 3 seconds
- **Recovery Cooldown**: 10 seconds
- **Startup Health Wait**: 30 seconds max

## 🚨 Manual Recovery

If automatic recovery doesn't work:

1. **Check Status Banner**: See what's failing
2. **Click "Recover"**: Trigger manual recovery
3. **Check Logs**: See detailed error messages
4. **Restart Services**: Use `./scripts/stop_all.sh` then `./scripts/start_all.sh`

## 🎯 Best Practices

1. **Use Watchdog for Production**: Keeps services running 24/7
2. **Monitor Logs**: Check logs regularly for patterns
3. **Health Checks**: Use `/health` endpoint for monitoring
4. **Graceful Shutdown**: Use `stop_all.sh` to stop services
5. **Port Management**: Let scripts handle port conflicts

## 🔐 Production Deployment

For production, use process managers:

### PM2 (Recommended)
```bash
# Install PM2
npm install -g pm2

# Start with PM2
cd backend
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name backend
pm2 save
pm2 startup

cd ../frontend
pm2 start "npm run dev" --name frontend
pm2 save
```

### systemd (Linux)
See `ALWAYS_RUNNING_GUIDE.md` for systemd configuration.

## ✅ Verification

To verify the recovery system is working:

1. **Start services**: `./scripts/start_all.sh`
2. **Kill backend**: `kill $(cat logs/backend.pid)`
3. **Watch logs**: `tail -f logs/watchdog.log`
4. **Verify restart**: Backend should restart within 10 seconds
5. **Check frontend**: Should show recovery in status banner

## 🎉 Result

Your application now:
- ✅ Automatically recovers from all failures
- ✅ Keeps services running 24/7
- ✅ Provides clear status feedback
- ✅ Requires zero manual intervention
- ✅ Handles all edge cases gracefully

**The app protects itself and always stays functional!**
