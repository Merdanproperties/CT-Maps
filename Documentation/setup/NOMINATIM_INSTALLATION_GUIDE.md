# Local Nominatim Installation Guide

## Prerequisites

### 1. Install Docker Desktop

**For macOS:**
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Install the `.dmg` file
3. Open Docker Desktop and complete the setup
4. Verify installation:
   ```bash
   docker --version
   ```

**For Linux:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (optional, to avoid sudo)
sudo usermod -aG docker $USER
```

## Installation Steps

### Step 1: Install Docker (if not already installed)
Follow the instructions above for your operating system.

### Step 2: Run the Setup Script
```bash
cd backend
chmod +x scripts/setup_local_nominatim.sh
./scripts/setup_local_nominatim.sh
```

**What this does:**
- Downloads Connecticut map data (~2-4 hours first time)
- Sets up Nominatim database
- Starts container on `http://localhost:8080`
- Creates persistent data directory (`backend/nominatim-data`)

### Step 3: Configure Environment
Add to `backend/.env`:
```bash
NOMINATIM_URL=http://localhost:8080
```

### Step 4: Test the Installation
```bash
# Test reverse geocoding
curl "http://localhost:8080/reverse?lat=41.812302&lon=-73.104239&format=json"
```

### Step 5: Fix Torrington Addresses
```bash
cd backend
source venv/bin/activate
python3 scripts/fix_torrington_reverse_geocode.py
```

## Time Estimates

- **Docker Installation:** 5-10 minutes
- **Nominatim Setup (first time):** 2-4 hours (downloads CT map data)
- **Address Fixing:** 5-10 minutes (once Nominatim is ready)

## Disk Space Requirements

- **Nominatim data:** ~50GB
- **Available space:** 329GB (✅ sufficient)

## Troubleshooting

### Docker not starting
- Make sure Docker Desktop is running
- Check: `docker ps`

### Container fails to start
- Check logs: `docker logs nominatim`
- Ensure port 8080 is not in use: `lsof -i :8080`

### Out of disk space
- Clean Docker: `docker system prune -a`
- Remove old images: `docker image prune -a`

## Using the Local Instance

Once running, the local Nominatim instance:
- ✅ No rate limits (unlike public API)
- ✅ Always available (no blocking)
- ✅ Fast processing (parallel requests)
- ✅ Free (no ongoing costs)

## Stopping/Starting

**Stop:**
```bash
docker stop nominatim
```

**Start:**
```bash
docker start nominatim
```

**Remove (if needed):**
```bash
docker stop nominatim
docker rm nominatim
rm -rf backend/nominatim-data
```
