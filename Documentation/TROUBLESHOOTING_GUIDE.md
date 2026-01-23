# Complete Troubleshooting Guide

This guide provides step-by-step solutions for every possible failure scenario. Each issue includes:
- **What it means**: Clear explanation of the problem
- **How to identify**: How to detect the issue
- **How to fix**: Step-by-step solution
- **Prevention**: How to avoid it in the future

## 🔍 Quick Diagnostic Tool

**Always start here**: Click the "Fix" button in the red status banner at the top of the app. This will show:
- Current system status
- Specific issues found
- Step-by-step fix instructions
- Commands to run

## 📋 Common Issues & Solutions

### Issue 1: "Backend server is not reachable"

**What it means**: The frontend cannot connect to the backend API server.

**How to identify**:
- Red status banner shows "Backend unreachable"
- All API requests fail
- Browser console shows network errors

**How to fix**:

1. **Check if backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```
   - If this fails, backend is not running

2. **Start the backend**:
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Or use the startup script**:
   ```bash
   ./scripts/start_all.sh
   ```

4. **Verify it's working**:
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy","database":"connected","api":"operational"}`

5. **Check for port conflicts**:
   ```bash
   lsof -i :8000
   ```
   If something else is using port 8000, kill it:
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

**Prevention**: Use `./scripts/watchdog.sh` to keep backend running automatically.

---

### Issue 2: "Database connection is lost"

**What it means**: Backend is running but cannot connect to PostgreSQL database.

**How to identify**:
- Status banner shows "Database: disconnected"
- Backend health check returns `"database": "disconnected"`
- API requests return 500 errors

**How to fix**:

1. **Verify PostgreSQL is running**:
   ```bash
   psql -l
   ```
   - If this fails, PostgreSQL is not running

2. **Start PostgreSQL**:
   
   **macOS (Postgres.app)**:
   - Open Postgres.app
   - Click "Initialize" if needed
   - Make sure it shows "Running"
   
   **macOS (Homebrew)**:
   ```bash
   brew services start postgresql
   ```
   
   **Linux**:
   ```bash
   sudo systemctl start postgresql
   ```

3. **Verify database exists**:
   ```bash
   psql -l | grep ct_properties
   ```
   If it doesn't exist, create it:
   ```bash
   createdb ct_properties
   psql ct_properties -c "CREATE EXTENSION postgis;"
   ```

4. **Check DATABASE_URL**:
   ```bash
   cat backend/.env | grep DATABASE_URL
   ```
   Should be: `DATABASE_URL=postgresql://localhost:5432/ct_properties`
   
   If wrong, edit `backend/.env`:
   ```bash
   echo "DATABASE_URL=postgresql://localhost:5432/ct_properties" > backend/.env
   ```

5. **Restart backend**:
   ```bash
   ./scripts/stop_all.sh
   ./scripts/start_all.sh
   ```

**Prevention**: Backend automatically attempts database reconnection every 30 seconds.

---

### Issue 3: "Request timeout"

**What it means**: Backend is taking too long to respond (over 30 seconds).

**How to identify**:
- Requests hang for 30+ seconds then fail
- Error message mentions "timeout"
- Backend may be overloaded or stuck

**How to fix**:

1. **Check backend logs**:
   ```bash
   tail -f logs/backend.log
   ```
   Look for:
   - Slow database queries
   - Error messages
   - Stuck processes

2. **Check database performance**:
   ```bash
   psql ct_properties -c "SELECT count(*) FROM properties;"
   ```
   If this is very slow, database may need optimization.

3. **Restart backend**:
   ```bash
   ./scripts/stop_all.sh
   ./scripts/start_all.sh
   ```

4. **Check system resources**:
   ```bash
   # Check CPU and memory
   top
   # Or on macOS:
   activity_monitor
   ```

5. **Reduce query size**:
   - If querying too many properties, add limits
   - Use pagination for large datasets

**Prevention**: Monitor backend logs regularly, optimize slow queries.

---

### Issue 4: "Port 8000 already in use"

**What it means**: Another process is using port 8000.

**How to identify**:
- Backend fails to start
- Error: "Address already in use" or "Port 8000 is in use"

**How to fix**:

1. **Find what's using the port**:
   ```bash
   lsof -i :8000
   ```

2. **Kill the process**:
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

3. **Or use the startup script** (handles this automatically):
   ```bash
   ./scripts/start_all.sh
   ```

4. **Verify port is free**:
   ```bash
   lsof -i :8000
   ```
   Should return nothing.

5. **Start backend**:
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

**Prevention**: Always use `./scripts/stop_all.sh` before starting services.

---

### Issue 5: "Port 3000 already in use"

**What it means**: Another process is using the frontend port.

**How to fix**:

1. **Kill process on port 3000**:
   ```bash
   lsof -ti:3000 | xargs kill -9
   ```

2. **Or use startup script**:
   ```bash
   ./scripts/start_all.sh
   ```

3. **Start frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

---

### Issue 6: "Module not found" or "Import error"

**What it means**: Python dependencies are missing or virtual environment not activated.

**How to fix**:

1. **Activate virtual environment**:
   ```bash
   cd backend
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import fastapi; print('OK')"
   ```

4. **If virtual environment doesn't exist**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

### Issue 7: "npm: command not found"

**What it means**: Node.js/npm is not installed.

**How to fix**:

1. **Install Node.js**:
   
   **macOS (Homebrew)**:
   ```bash
   brew install node
   ```
   
   **Or download from**: https://nodejs.org/

2. **Verify installation**:
   ```bash
   node --version
   npm --version
   ```

3. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   ```

---

### Issue 8: "Properties not loading" or "Empty results"

**What it means**: Database may be empty or query is failing.

**How to fix**:

1. **Check if database has data**:
   ```bash
   psql ct_properties -c "SELECT COUNT(*) FROM properties;"
   ```

2. **If empty, load data**:
   ```bash
   cd backend
   source venv/bin/activate
   python scripts/process_parcels.py --limit 10000
   ```

3. **Check backend logs**:
   ```bash
   tail -f logs/backend.log
   ```
   Look for query errors.

4. **Test API directly**:
   ```bash
   curl "http://localhost:8000/api/search/?bbox=-73.5,41.0,-72.0,42.0&page_size=10"
   ```

---

### Issue 9: "CORS error" in browser console

**What it means**: Backend CORS configuration issue.

**How to fix**:

1. **Check backend CORS settings** in `backend/main.py`:
   ```python
   allow_origins=[
       "http://localhost:3000",
       "http://localhost:5173",
       ...
   ]
   ```

2. **Add your frontend URL** if different

3. **Restart backend**:
   ```bash
   ./scripts/stop_all.sh && ./scripts/start_all.sh
   ```

---

### Issue 10: "Watchdog not restarting services"

**What it means**: Watchdog script may have issues.

**How to fix**:

1. **Check watchdog is running**:
   ```bash
   ps aux | grep watchdog
   ```

2. **Check watchdog logs**:
   ```bash
   tail -f logs/watchdog.log
   ```

3. **Restart watchdog**:
   ```bash
   pkill -f watchdog.sh
   ./scripts/watchdog.sh
   ```

4. **Verify script permissions**:
   ```bash
   chmod +x scripts/watchdog.sh
   ```

---

## 🛠️ Diagnostic Commands Reference

### Check Backend
```bash
# Health check
curl http://localhost:8000/health

# Check if running
lsof -i :8000

# View logs
tail -f logs/backend.log

# Check process
ps aux | grep uvicorn
```

### Check Database
```bash
# List databases
psql -l

# Connect to database
psql ct_properties

# Check table count
psql ct_properties -c "SELECT COUNT(*) FROM properties;"

# Check if PostgreSQL is running
ps aux | grep postgres
```

### Check Frontend
```bash
# Check if running
lsof -i :3000

# View logs
tail -f logs/frontend.log

# Check process
ps aux | grep "npm run dev"
```

### Check Ports
```bash
# Check all listening ports
lsof -i -P | grep LISTEN

# Check specific port
lsof -i :8000
lsof -i :3000
```

### Kill Processes
```bash
# Kill by port
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Kill by name
pkill -f uvicorn
pkill -f "npm run dev"
```

## 🚨 Emergency Recovery

If nothing works, complete reset:

```bash
# 1. Stop everything
./scripts/stop_all.sh

# 2. Kill any remaining processes
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# 3. Clean up
rm -f logs/*.pid

# 4. Restart
./scripts/start_all.sh
```

## 📞 Still Having Issues?

1. **Run diagnostics**: Click "Fix" button in status banner
2. **Check all logs**: `tail -f logs/*.log`
3. **Verify all services**: Use diagnostic commands above
4. **Check system resources**: `top` or Activity Monitor
5. **Review this guide**: Find your specific issue

## ✅ Prevention Checklist

- [ ] Use `./scripts/watchdog.sh` for production
- [ ] Keep PostgreSQL running
- [ ] Monitor logs regularly
- [ ] Use startup scripts instead of manual start
- [ ] Keep dependencies updated
- [ ] Check health endpoints regularly

---

**Remember**: The "Fix" button in the status banner provides the most up-to-date diagnostic information and fix instructions for your specific situation!
