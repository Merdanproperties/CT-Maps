# Ensuring Servers Always Run - Connection Reliability Guide

This guide ensures your application never experiences connection errors by keeping all servers running and monitoring their health.

## 🚀 Quick Start - Always Running Setup

### Option 1: Use the Startup Scripts (Recommended)

**Backend:**
```bash
cd backend
./start.sh
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### Option 2: Manual Startup

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## ✅ Built-in Connection Reliability Features

The application now includes several features to prevent connection errors:

### 1. **Automatic Health Monitoring**
- Backend health is checked every 5 seconds
- Connection status is displayed at the top of the app
- Automatic reconnection when backend comes back online

### 2. **Automatic Retry Logic**
- Failed requests automatically retry up to 3 times
- Uses exponential backoff (1s, 2s, 4s delays)
- Only retries on network errors and server errors (5xx)

### 3. **Startup Health Check**
- App waits for backend to be healthy before making requests
- Shows connection status immediately on load
- Prevents errors from happening in the first place

### 4. **Better Error Messages**
- Clear, actionable error messages
- Tells you exactly what's wrong and how to fix it
- Connection status banner shows real-time status

## 🔍 Connection Status Indicator

The app displays a connection status banner at the top:
- **Green**: Backend is connected and healthy ✅
- **Red**: Backend is disconnected or unhealthy ⚠️
- **Retry Button**: Click to manually check connection

## 🛠️ Troubleshooting

### Backend Not Starting?

1. **Check if port 8000 is already in use:**
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

2. **Verify PostgreSQL is running:**
   ```bash
   # macOS (Postgres.app)
   # Make sure Postgres.app is running
   
   # Or check with:
   psql -l
   ```

3. **Check backend logs for errors:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

### Frontend Can't Connect?

1. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy"}`

2. **Check browser console** for detailed error messages

3. **Verify Vite proxy** is configured correctly (should be automatic)

## 🔄 Auto-Restart on Crash (Advanced)

### Using PM2 (Process Manager)

**Install PM2:**
```bash
npm install -g pm2
```

**Start Backend with PM2:**
```bash
cd backend
source venv/bin/activate
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name ct-maps-backend
pm2 save
pm2 startup  # Follow instructions to enable auto-start on boot
```

**Start Frontend with PM2:**
```bash
cd frontend
pm2 start "npm run dev" --name ct-maps-frontend
pm2 save
```

**PM2 Commands:**
```bash
pm2 list              # View running processes
pm2 logs ct-maps-backend   # View backend logs
pm2 restart all       # Restart all processes
pm2 stop all          # Stop all processes
```

### Using systemd (Linux)

Create `/etc/systemd/system/ct-maps-backend.service`:
```ini
[Unit]
Description=CT Maps Backend
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/CT Maps/backend
Environment="PATH=/path/to/CT Maps/backend/venv/bin"
ExecStart=/path/to/CT Maps/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ct-maps-backend
sudo systemctl start ct-maps-backend
sudo systemctl status ct-maps-backend
```

## 📊 Monitoring

### Health Check Endpoint

The backend exposes a health check endpoint:
```bash
curl http://localhost:8000/health
```

### Frontend Monitoring

The frontend automatically:
- Checks backend health every 5 seconds
- Displays connection status
- Retries failed requests automatically
- Shows helpful error messages

## 🎯 Best Practices

1. **Always start backend before frontend**
2. **Keep both terminals open** during development
3. **Check the connection status banner** if you see errors
4. **Use PM2 or systemd** for production deployments
5. **Monitor logs** regularly for issues

## 🚨 What to Do If Connection Fails

1. **Check the connection status banner** at the top of the app
2. **Verify backend is running**: `curl http://localhost:8000/health`
3. **Check backend logs** for errors
4. **Restart backend** if needed
5. **Click "Retry"** in the connection status banner

The app will automatically reconnect once the backend is back online!
