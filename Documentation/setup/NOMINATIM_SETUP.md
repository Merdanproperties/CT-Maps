# Nominatim Setup Options

## Why Nominatim is "Blocked"

The connection refused error suggests:
1. **Network/Firewall blocking** - Your network may be blocking external API calls
2. **Rate limiting** - Nominatim limits to 1 request/second (free tier)
3. **Service availability** - The public instance may be temporarily down

## Free Options from Nominatim Website

The Nominatim website (nominatim.org) offers **two free options**:

### Option 1: Use the Public API (Free, but Rate Limited)
- **Rate limit:** 1 request per second
- **For:** Occasional use
- **Time:** ~4 hours for 14,000 addresses
- **Setup:** Just use the API (what we tried)

### Option 2: Install Your Own Instance (Free, No Rate Limits!) ⭐
- **Latest version:** 5.2.0
- **For:** Power users
- **Benefits:** 
  - No rate limits
  - Full control
  - Can process all addresses quickly
- **Setup:** Requires Docker and ~50GB disk space

## Installing Your Own Nominatim Instance

This is the **best free solution** - you run Nominatim locally with no rate limits!

### Quick Setup (Docker):

```bash
# Install Docker if not already installed
# Then run Nominatim container

docker run -it \
  -e PBF_URL=https://download.geofabrik.de/north-america/us/connecticut-latest.osm.pbf \
  -e REPLICATION_URL=https://download.geofabrik.de/north-america/us/connecticut-updates/ \
  -p 8080:8080 \
  --name nominatim \
  -v nominatim-data:/var/lib/postgresql/12/main \
  mediagis/nominatim:5.2
```

**Time to setup:** ~2-4 hours (downloads CT map data)
**Disk space needed:** ~50GB
**After setup:** No rate limits, can geocode all addresses in minutes!

## Recommendation

**For immediate fix:** Use Google/Mapbox API ($5-10, 5 minutes)
**For long-term free solution:** Install your own Nominatim instance (free, 2-4 hours setup, then unlimited)

Would you like me to:
1. Set up a script to install Nominatim locally?
2. Or proceed with a paid service for immediate results?
