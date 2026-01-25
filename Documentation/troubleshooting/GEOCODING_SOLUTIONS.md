# Geocoding Solutions for Torrington Address Matching

## The Problem

We need to match ~14,000 CAMA addresses to property geometries. The free Nominatim API is blocked/rate-limited (1 req/sec = ~4 hours for all addresses).

## Solutions

### Option 1: Free Solution (Nominatim with Rate Limiting) ⏱️ ~4 hours

**Pros:**
- Free
- No API key needed
- Works automatically

**Cons:**
- Slow (1 request per second = ~4 hours for 14k addresses)
- May be blocked by network/firewall

**Usage:**
```bash
cd backend
source venv/bin/activate
python3 scripts/fix_torrington_addresses_geocoding.py
```

The script will:
- Cache results to avoid re-geocoding
- Show progress and ETA
- Can be stopped and resumed (cache persists)

### Option 2: Google Geocoding API 💰 ~$5-10

**Pricing:** $5 per 1,000 requests (first $200 free/month)
**Speed:** ~50 requests/second
**Time:** ~5 minutes for 14k addresses

**Setup:**
1. Get API key: https://console.cloud.google.com/apis/credentials
2. Enable Geocoding API
3. Add to `.env`:
   ```
   GEOCODE_SERVICE=google
   GOOGLE_GEOCODING_API_KEY=your_key_here
   ```
4. Run: `python3 scripts/fix_torrington_addresses_geocoding.py --service google`

### Option 3: Mapbox Geocoding API 💰 ~$5-10

**Pricing:** $0.75 per 1,000 requests (first 100k free/month)
**Speed:** ~50 requests/second
**Time:** ~5 minutes for 14k addresses

**Setup:**
1. Get access token: https://account.mapbox.com/access-tokens/
2. Add to `.env`:
   ```
   GEOCODE_SERVICE=mapbox
   MAPBOX_ACCESS_TOKEN=your_token_here
   ```
3. Run: `python3 scripts/fix_torrington_addresses_geocoding.py --service mapbox`

### Option 4: Here Geocoding API 💰 ~$5-10

**Pricing:** $0.50 per 1,000 requests (free tier available)
**Speed:** ~50 requests/second

## Recommendation

**For immediate fix:** Use **Google Geocoding API** ($5-10 one-time cost, ~5 minutes)
- Most reliable
- Best address matching
- Easy setup

**For free solution:** Use Nominatim with rate limiting (run overnight, ~4 hours)

## Current Status

The script `fix_torrington_addresses_geocoding.py` is ready to use with any of these services. It includes:
- ✅ Caching to avoid re-geocoding
- ✅ Progress tracking
- ✅ Resume capability
- ✅ Maximum CPU usage for parallel processing (paid services)
- ✅ Spatial matching to find nearest property

## Next Steps

1. **Quick fix (paid):** Get Google API key, add to `.env`, run script
2. **Free fix:** Run Nominatim script and let it complete (~4 hours)
3. **Test first:** Run with `--limit 100` to test before full run
