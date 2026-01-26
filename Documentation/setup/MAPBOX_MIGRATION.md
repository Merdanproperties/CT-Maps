# Mapbox Migration Guide

## Overview

The application has been migrated from Leaflet (with free CARTO basemaps) to Mapbox GL JS for improved performance and visual quality. Mapbox offers:

- **Free tier**: 50,000 map loads per month
- **Pay-as-you-go**: $5 per 1,000 loads after free tier
- **Volume discounts**: Automatically applied

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install react-map-gl mapbox-gl
```

### 2. Get Mapbox Access Token

1. Sign up for a free account at https://account.mapbox.com/
2. Navigate to https://account.mapbox.com/access-tokens/
3. Create a new access token (or use the default public token)
4. Copy the token

### 3. Configure Environment Variables

Create or update `.env` in the frontend directory:

```env
VITE_MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
```

Or set it in your deployment environment.

### 4. Update MapView Component

The MapView component has been updated to use Mapbox. The migration includes:

- Replaced `react-leaflet` with `react-map-gl`
- Replaced `MapContainer` with `Map` from react-map-gl
- Converted GeoJSON layers to Mapbox layers
- Updated markers and popups to use Mapbox components
- Preserved all existing functionality (filters, property selection, etc.)

### 5. Restart the Application

```bash
# Stop current servers
./scripts/stop_all.sh

# Start with new dependencies
cd frontend && npm install
cd ../backend
./scripts/start_all.sh
```

## Cost Monitoring

### Check Usage Statistics

The analytics endpoint now tracks map loads:

```bash
# Get map usage statistics
curl http://localhost:8000/api/analytics/map-usage?days=30
```

This returns:
- Total map loads
- Daily averages
- Monthly estimates
- Cost estimates for Mapbox and Google Maps

### Set Up Billing Alerts

1. Log in to https://account.mapbox.com/
2. Go to Account Settings > Billing
3. Set up usage alerts:
   - Alert at 40,000 loads (80% of free tier)
   - Alert at 50,000 loads (free tier limit)
   - Alert at custom thresholds for pay-as-you-go

### Monitor Usage Dashboard

Mapbox provides a usage dashboard at:
https://account.mapbox.com/usage/

Monitor:
- Map loads per day
- Cost per day
- Projected monthly costs

## Rollback Instructions

If you need to rollback to Leaflet:

1. The Leaflet code is preserved in git history
2. Revert the MapView.tsx changes
3. Remove Mapbox dependencies:
   ```bash
   npm uninstall react-map-gl mapbox-gl
   ```

## Features Preserved

All existing features work with Mapbox:
- ✅ Property GeoJSON rendering
- ✅ Property click handlers
- ✅ Hover effects
- ✅ Address number markers
- ✅ Selected property popup
- ✅ Map bounds tracking
- ✅ Filter integration
- ✅ Search functionality

## Performance Improvements

Mapbox GL JS provides:
- Vector tiles (faster rendering)
- Smooth zooming and panning
- Better mobile performance
- Custom styling options

## Support

For issues or questions:
- Mapbox documentation: https://docs.mapbox.com/
- Mapbox support: https://support.mapbox.com/
