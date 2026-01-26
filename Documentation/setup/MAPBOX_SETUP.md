# Mapbox Integration Setup Guide

## Overview

The application now supports both Mapbox and Leaflet map providers with automatic fallback. Mapbox provides better visual quality and performance, while Leaflet remains as a reliable free fallback.

## Quick Start

### 1. Get Mapbox Access Token

1. Sign up for a free account at https://account.mapbox.com/
2. Navigate to https://account.mapbox.com/access-tokens/
3. Create a new access token (or use the default public token)
4. Copy the token

### 2. Configure Environment Variable

Create or update `.env` in the frontend directory:

```env
# Optional: Set to 'mapbox', 'leaflet', or 'auto' (default)
VITE_MAP_PROVIDER=auto

# Required for Mapbox (if not set, uses Leaflet)
VITE_MAPBOX_ACCESS_TOKEN=your_mapbox_token_here

# Mapbox Style (Optional)
# Current: satellite-streets-v12 (satellite imagery with street labels)
# Default: streets-v12 if not specified
VITE_MAPBOX_STYLE=mapbox://styles/mapbox/satellite-streets-v12
```

### 3. Install Dependencies

```bash
cd frontend
npm install
```

Dependencies are already in `package.json`:
- `react-map-gl`: ^7.1.7
- `mapbox-gl`: ^3.0.1

### 4. Restart Application

```bash
# Stop current servers
./scripts/stop_all.sh

# Start with new configuration
./scripts/start_all.sh
```

## How It Works

### Automatic Provider Selection

The system automatically selects the map provider:

1. **If `VITE_MAPBOX_ACCESS_TOKEN` is set**: Uses Mapbox
2. **If token is missing**: Uses Leaflet (current free setup)
3. **If Mapbox fails**: Automatically falls back to Leaflet
4. **Manual override**: Set `VITE_MAP_PROVIDER=leaflet` to force Leaflet

### Fallback Behavior

- **Mapbox initialization fails**: Falls back to Leaflet
- **Mapbox token invalid**: Falls back to Leaflet
- **Network errors**: Falls back to Leaflet
- **All fallbacks are logged** for monitoring

## Features

### Both Providers Support

- ✅ Property GeoJSON rendering
- ✅ Property click handlers
- ✅ Hover effects
- ✅ Selected property popup
- ✅ Map bounds tracking
- ✅ Filter integration
- ✅ Search functionality
- ✅ Address number markers (Leaflet only for now)

### Mapbox-Specific Benefits

- Better visual quality
- Smoother zooming/panning
- Faster rendering with vector tiles
- Professional styling
- Better mobile performance

## Configuration Options

### Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `VITE_MAP_PROVIDER` | `auto`, `mapbox`, `leaflet` | `auto` | Manual provider selection |
| `VITE_MAPBOX_ACCESS_TOKEN` | Mapbox token string | (none) | Mapbox access token |

### Examples

**Use Mapbox (if token configured):**
```env
VITE_MAP_PROVIDER=auto
VITE_MAPBOX_ACCESS_TOKEN=pk.eyJ1Ijoi...
```

**Force Leaflet (even if token exists):**
```env
VITE_MAP_PROVIDER=leaflet
```

**Force Mapbox (will error if no token):**
```env
VITE_MAP_PROVIDER=mapbox
VITE_MAPBOX_ACCESS_TOKEN=pk.eyJ1Ijoi...
```

## Monitoring

### Check Which Provider is Active

The analytics endpoint tracks which provider is used:

```bash
curl http://localhost:8000/api/analytics/map-usage?days=30
```

Response includes:
- `map_type_breakdown`: Shows counts for 'mapbox' and 'leaflet'
- `fallback_reason`: If fallback occurred, reason is included

### View Fallback Events

Fallback events are logged in:
- Browser console (with ⚠️ warning)
- Backend analytics (with `fallback_reason` field)

## Troubleshooting

### Mapbox Not Loading

1. **Check token**: Verify `VITE_MAPBOX_ACCESS_TOKEN` is set correctly
2. **Check console**: Look for Mapbox errors in browser console
3. **Automatic fallback**: System should automatically use Leaflet if Mapbox fails
4. **Force Leaflet**: Set `VITE_MAP_PROVIDER=leaflet` to disable Mapbox

### Address Markers Not Showing (Mapbox)

Address number markers are currently only supported in Leaflet mode. This is a known limitation and will be enhanced in a future update.

### Performance Issues

- **Mapbox**: Should be faster than Leaflet
- **Leaflet**: If experiencing slowness, check network/tile loading
- **Both**: Property rendering performance is the same

## Cost Information

### Mapbox Pricing

- **Free tier**: 50,000 map loads/month
- **After free tier**: ~$5 per 1,000 loads
- **Your usage**: Check via `/api/analytics/map-usage`

### Leaflet (Current Default)

- **Cost**: $0/month (unlimited)
- **Tiles**: Free OpenStreetMap/CARTO tiles

## Rollback

To revert to Leaflet-only:

1. Remove or comment out `VITE_MAPBOX_ACCESS_TOKEN` in `.env`
2. Or set `VITE_MAP_PROVIDER=leaflet`
3. Restart the application

No code changes needed!

## Support

- Mapbox Documentation: https://docs.mapbox.com/
- Mapbox Support: https://support.mapbox.com/
- React Map GL: https://visgl.github.io/react-map-gl/
