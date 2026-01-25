#!/bin/bash
# Check Docker and guide through Nominatim setup

set -e

echo "============================================================"
echo "Local Nominatim Setup Check"
echo "============================================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo ""
    echo "❌ Docker is not installed"
    echo ""
    echo "📥 Please install Docker Desktop first:"
    echo "   1. Download: https://www.docker.com/products/docker-desktop"
    echo "   2. Install the .dmg file"
    echo "   3. Open Docker Desktop and wait for it to start"
    echo "   4. Run this script again"
    echo ""
    exit 1
fi

echo "✅ Docker is installed: $(docker --version)"

# Check if Docker is running
if ! docker ps &> /dev/null; then
    echo ""
    echo "⚠️  Docker is installed but not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

echo "✅ Docker is running"

# Check if Nominatim container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^nominatim$"; then
    echo ""
    echo "📦 Nominatim container already exists"
    
    if docker ps --format '{{.Names}}' | grep -q "^nominatim$"; then
        echo "✅ Nominatim is already running on http://localhost:8080"
        echo ""
        echo "To test it:"
        echo "  curl 'http://localhost:8080/reverse?lat=41.812302&lon=-73.104239&format=json'"
        exit 0
    else
        echo "🔄 Starting existing Nominatim container..."
        docker start nominatim
        echo "✅ Nominatim started. Waiting 30 seconds for it to be ready..."
        sleep 30
        echo ""
        echo "To test it:"
        echo "  curl 'http://localhost:8080/reverse?lat=41.812302&lon=-73.104239&format=json'"
        exit 0
    fi
fi

# Check disk space
echo ""
echo "Checking disk space..."
available_gb=$(df -h . | awk 'NR==2 {print $4}' | sed 's/[^0-9.]//g')
echo "  Available: ${available_gb}GB"

if (( $(echo "$available_gb < 50" | bc -l 2>/dev/null || echo "0") )); then
    echo "⚠️  Warning: Less than 50GB available"
    echo "   Nominatim needs ~50GB for Connecticut data"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create data directory
DATA_DIR="$(pwd)/nominatim-data"
mkdir -p "$DATA_DIR"

echo ""
echo "============================================================"
echo "Starting Nominatim Setup"
echo "============================================================"
echo ""
echo "This will:"
echo "  1. Download Connecticut map data (~2-4 hours first time)"
echo "  2. Set up Nominatim database"
echo "  3. Start container on http://localhost:8080"
echo ""
echo "⚠️  This is a long-running process. You can:"
echo "   - Press Ctrl+C to stop (you can restart later)"
echo "   - Check progress with: docker logs -f nominatim"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "Starting Nominatim container..."
echo "  This may take 2-4 hours for initial setup"
echo ""

# Run Nominatim container for Connecticut
docker run -it \
  -e PBF_URL=https://download.geofabrik.de/north-america/us/connecticut-latest.osm.pbf \
  -e REPLICATION_URL=https://download.geofabrik.de/north-america/us/connecticut-updates/ \
  -p 8080:8080 \
  --name nominatim \
  -v "$DATA_DIR:/var/lib/postgresql/12/main" \
  --shm-size=1g \
  mediagis/nominatim:5.2

echo ""
echo "============================================================"
echo "✅ Nominatim setup complete!"
echo "============================================================"
echo ""
echo "Nominatim is now running at: http://localhost:8080"
echo ""
echo "Next steps:"
echo "  1. Update backend/.env:"
echo "     NOMINATIM_URL=http://localhost:8080"
echo ""
echo "  2. Test it:"
echo "     curl 'http://localhost:8080/reverse?lat=41.812302&lon=-73.104239&format=json'"
echo ""
echo "  3. Fix Torrington addresses:"
echo "     python3 scripts/fix_torrington_reverse_geocode.py"
echo ""
