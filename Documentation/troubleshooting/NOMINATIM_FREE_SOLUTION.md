# Free Nominatim Solution - Install Your Own Instance

## Why Nominatim is "Blocked"

The connection refused error is likely due to:
1. **Network/Firewall restrictions** - Your network blocking external API calls
2. **Rate limiting** - Public Nominatim limits to 1 request/second
3. **Service availability** - Public instance may be temporarily unavailable

## Free Solution: Install Your Own Nominatim Instance

The Nominatim website offers **"Install your own"** option - this is **100% free** and has **no rate limits**!

### Benefits:
- ✅ **Free** - No cost
- ✅ **No rate limits** - Process all addresses as fast as your CPU allows
- ✅ **Private** - Runs on your machine
- ✅ **Reliable** - No external API dependencies

### Requirements:
- Docker Desktop installed
- ~50GB free disk space
- ~2-4 hours initial setup (downloads CT map data)

### Quick Setup:

1. **Install Docker Desktop** (if not already installed):
   - Download from: https://www.docker.com/products/docker-desktop
   - Install and start Docker

2. **Run the setup script**:
   ```bash
   cd backend
   chmod +x scripts/setup_local_nominatim.sh
   ./scripts/setup_local_nominatim.sh
   ```

   This will:
   - Download Connecticut map data (~2-4 hours, one-time)
   - Start Nominatim on `http://localhost:8080`
   - Set up with no rate limits

3. **Update `.env` file**:
   ```
   NOMINATIM_URL=http://localhost:8080
   GEOCODE_SERVICE=nominatim
   ```

4. **Run the geocoding script**:
   ```bash
   python3 scripts/fix_torrington_addresses_geocoding.py
   ```

   With local Nominatim, this will process all 14,000 addresses in **minutes** (not hours)!

### After Setup:

Once running, you can:
- Geocode unlimited addresses instantly
- Use it for all future imports
- No ongoing costs
- No API keys needed

## Alternative: Use Public API (Free, but Slow)

If you don't want to install locally, the public Nominatim API is free but:
- Rate limit: 1 request/second
- Time: ~4 hours for 14,000 addresses
- May be blocked by network

## Recommendation

**Install your own Nominatim instance** - it's free, fast, and solves the problem permanently!
