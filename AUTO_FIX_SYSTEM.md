# Automatic Fix System - Self-Healing Application

This application now has **full automatic remediation capabilities** - it can fix issues itself without requiring user intervention.

## 🤖 How Auto-Fix Works

### Automatic Detection & Fix Flow

1. **Issue Detected** → Health check finds problem
2. **Diagnostics Run** → System identifies specific issue
3. **Auto-Fix Triggered** → Remediation service attempts fix
4. **Fix Executed** → Backend/frontend performs recovery actions
5. **Verification** → System confirms fix worked
6. **Status Updated** → User sees recovery in real-time

### What Can Be Fixed Automatically

✅ **Database Connection Issues**
- Automatically reconnects to PostgreSQL
- Refreshes connection pool
- Verifies connection health

✅ **Backend Health Issues**
- Triggers database reconnection
- Waits for backend recovery
- Retries with exponential backoff

✅ **Network Connection Issues**
- Automatic retry with backoff
- Connection health verification
- Service recovery coordination

✅ **Temporary Service Outages**
- Waits for service recovery
- Automatic reconnection
- Status verification

## 🎯 Using Auto-Fix

### Method 1: Automatic (Background)

The system **automatically attempts fixes** when issues are detected:
- Health checks trigger auto-fix
- No user action required
- Fixes happen in background
- Status updates automatically

### Method 2: Manual Trigger (Diagnostics Panel)

1. Click **"Fix"** button in red status banner
2. Diagnostics panel opens
3. Click **"Auto-Fix"** button
4. System attempts to fix all issues
5. Results shown in real-time

### Method 3: Backend API (Programmatic)

```bash
# Reconnect database
curl -X POST http://localhost:8000/api/remediation/reconnect-database

# Check PostgreSQL
curl -X POST http://localhost:8000/api/remediation/check-postgres

# Execute custom remediation
curl -X POST http://localhost:8000/api/remediation/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "reconnect_database", "params": {}}'
```

## 🔧 Auto-Fix Capabilities

### Frontend Auto-Fix

**What it can do:**
- Retry failed connections
- Wait for backend recovery
- Trigger backend remediation APIs
- Verify service health
- Coordinate recovery attempts

**Limitations:**
- Cannot restart backend process (requires process manager)
- Cannot start PostgreSQL (requires system access)
- Cannot modify system files

### Backend Auto-Fix

**What it can do:**
- Reconnect to database
- Refresh connection pools
- Check PostgreSQL status
- Restart backend (if process manager available)
- Execute system commands (with proper permissions)

**API Endpoints:**
- `POST /api/remediation/reconnect-database` - Force database reconnection
- `POST /api/remediation/check-postgres` - Verify PostgreSQL is running
- `POST /api/remediation/restart-backend` - Restart backend (if script available)
- `POST /api/remediation/execute` - Execute custom remediation action

## 📊 Auto-Fix Results

After auto-fix runs, you'll see:

✅ **Success Indicators:**
- Green checkmark
- "Fixed successfully" message
- List of executed commands
- Updated system status

❌ **Failure Indicators:**
- Red alert icon
- Error message explaining why
- Commands that were attempted
- Manual fix instructions

## 🛡️ Safety Features

### Automatic Safeguards

1. **Timeout Protection**: All fixes have timeouts to prevent hanging
2. **Error Handling**: Failures are caught and logged, never crash the app
3. **Verification**: Every fix is verified before reporting success
4. **Rollback**: If fix makes things worse, system attempts to revert
5. **Logging**: All fix attempts are logged for debugging

### What Auto-Fix Won't Do

❌ Delete files or data
❌ Modify configuration without verification
❌ Run destructive commands
❌ Bypass security measures
❌ Make permanent system changes

## 🔄 Integration with Other Systems

### Watchdog Script
- Auto-fix works alongside watchdog
- Watchdog handles process-level recovery
- Auto-fix handles application-level recovery
- They complement each other

### Health Monitoring
- Health checks trigger auto-fix
- Auto-fix results update health status
- Continuous monitoring ensures fixes stick

### Error Handling
- All errors include auto-fix suggestions
- Failed auto-fixes provide manual steps
- Clear escalation path if auto-fix fails

## 📝 Example Scenarios

### Scenario 1: Database Disconnects

**What Happens:**
1. Health check detects database disconnect
2. Auto-fix triggers database reconnection
3. Backend refreshes connection pool
4. Connection verified
5. Status updates to "healthy"

**User Sees:** Brief red banner, then automatic recovery

### Scenario 2: Backend Slow Response

**What Happens:**
1. Request times out
2. Auto-fix retries with backoff
3. Health check verifies backend
4. If still slow, waits for recovery
5. Retries request

**User Sees:** Automatic retry, eventual success or clear error

### Scenario 3: Network Interruption

**What Happens:**
1. Network error detected
2. Auto-fix waits and retries
3. Connection restored
4. Services reconnect automatically
5. Normal operation resumes

**User Sees:** Automatic reconnection, seamless recovery

## 🎛️ Configuration

### Auto-Fix Settings

Located in `frontend/src/services/autoRemediation.ts`:

```typescript
// Retry configuration
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // Initial delay
const MAX_DELAY = 10000 // Maximum delay

// Timeout configuration
const HEALTH_CHECK_TIMEOUT = 5000
const REMEDIATION_TIMEOUT = 30000
```

### Backend Remediation Settings

Located in `backend/api/routes/remediation.py`:

```python
# Command timeouts
subprocess_timeout = 30  # seconds

# Script paths
restart_script = "scripts/restart_backend.sh"
```

## 🚀 Best Practices

1. **Let Auto-Fix Run First**: Give it a chance before manual intervention
2. **Monitor Results**: Check diagnostics panel to see what was fixed
3. **Review Logs**: Check logs if auto-fix fails
4. **Use Watchdog**: Combine with watchdog for complete protection
5. **Trust the System**: Auto-fix is safe and reversible

## 🔍 Troubleshooting Auto-Fix

### Auto-Fix Not Working?

1. **Check Backend API**: Verify `/api/remediation/*` endpoints are accessible
2. **Check Permissions**: Ensure scripts have execute permissions
3. **Check Logs**: Review auto-fix execution logs
4. **Manual Trigger**: Try clicking "Auto-Fix" button manually
5. **Verify Health**: Make sure health checks are running

### Auto-Fix Failed?

1. **Read Error Message**: Explains why it failed
2. **Check Executed Commands**: See what was attempted
3. **Try Manual Steps**: Use provided fix instructions
4. **Check System State**: Verify services are actually running
5. **Review Logs**: Check backend/frontend logs for details

## ✅ Verification

To verify auto-fix is working:

1. **Start services**: `./scripts/start_all.sh`
2. **Stop database**: `brew services stop postgresql` (or stop Postgres.app)
3. **Watch status banner**: Should show red, then auto-fix attempts
4. **Start database**: `brew services start postgresql`
5. **Watch recovery**: Should automatically detect and recover

## 🎉 Result

**The application can now fix itself!**

- ✅ Detects issues automatically
- ✅ Attempts fixes without user action
- ✅ Verifies fixes worked
- ✅ Provides clear status updates
- ✅ Falls back to manual steps if needed
- ✅ Logs everything for debugging

**You (the AI) and users can always see exactly what's wrong and how it's being fixed!**
