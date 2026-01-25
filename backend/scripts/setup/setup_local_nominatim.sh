#!/bin/bash
# Setup script for local Nominatim instance (free, no rate limits)
# Based on: https://nominatim.org/release-docs/latest/admin/Installation/

set -e

echo "============================================================"
echo "Setting Up Local Nominatim Instance (Free, No Rate Limits)"
echo "============================================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✅ Docker is installed"

# Check disk space (need ~50GB)
echo ""
echo "Checking disk space..."
available_space=$(df -h . | awk 'NR==2 {print $4}' | sed 's/[^0-9.]//g')
if (( $(echo "$available_space < 50" | bc -l) )); then
    echo "⚠️  Warning: Less than 50GB available. Nominatim needs ~50GB for CT data."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create data directory
DATA_DIR="./nominatim-data"
mkdir -p "$DATA_DIR"

echo ""
echo "Starting Nominatim container..."
echo "  This will download CT map data (~2-4 hours)"
echo "  Container will run on http://localhost:8080"

# Run Nominatim container for Connecticut
# Using -d (detached) mode so it runs in background
# This will take 2-4 hours to download and process CT data
echo ""
echo "Starting container in background..."
echo "  You can monitor progress with: docker logs -f nominatim"
echo "  This will take 2-4 hours for initial setup"
echo ""

docker run -d \
  -e PBF_URL=https://download.geofabrik.de/north-america/us/connecticut-latest.osm.pbf \
  -e REPLICATION_URL=https://download.geofabrik.de/north-america/us/connecticut-updates/ \
  -p 8080:8080 \
  --name nominatim \
  -v "$(pwd)/nominatim-data:/var/lib/postgresql/12/main" \
  --shm-size=1g \
  mediagis/nominatim:5.2

echo "✅ Container started!"
echo ""
echo "Monitor progress:"
echo "  docker logs -f nominatim"
echo ""
echo "When you see 'Nominatim is ready to accept requests', setup is complete!"
echo "This typically takes 2-4 hours for Connecticut data."

echo ""
echo "============================================================"
echo "✅ Nominatim setup complete!"
echo "============================================================"
echo ""
echo "Nominatim is now running at: http://localhost:8080"
echo ""
echo "To use it in the geocoding script, update .env:"
echo "  NOMINATIM_URL=http://localhost:8080"
echo ""
echo "Then run:"
echo "  python3 scripts/fix_torrington_addresses_geocoding.py"
echo ""
