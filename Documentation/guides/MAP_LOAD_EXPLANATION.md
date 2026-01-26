# Understanding Map Loads: 50K Free Loads Explained

## What is a "Map Load"?

A **map load** is counted each time a user opens or refreshes a page that displays a map. It's a single count per page view, not per interaction.

### Important Details:
- ✅ **One load** = One page view with a map
- ✅ **Free interactions**: Once loaded, users can zoom, pan, click, and interact without additional charges
- ✅ **Session limit**: A single map session can last up to 12 hours before counting as a new load
- ❌ **Not counted**: Individual tile requests, zooming, panning, or clicking

## Real-World Examples

### Scenario 1: Typical User Session
- User opens your property map page → **1 load**
- User zooms in/out 20 times → **0 additional loads**
- User pans around for 10 minutes → **0 additional loads**
- User clicks on 5 properties → **0 additional loads**
- User refreshes the page → **1 new load**

**Total: 2 loads for this session**

### Scenario 2: Daily Usage Patterns

**Small Application (Personal/Small Business)**
- 10 unique visitors per day
- Each visitor views map 2-3 times (initial + refresh)
- **Daily loads: ~25 loads**
- **Monthly estimate: ~750 loads**
- **50K free tier: Would last ~66 months (5+ years)**

**Medium Application (Growing Business)**
- 100 unique visitors per day
- Each visitor views map 2-3 times
- **Daily loads: ~250 loads**
- **Monthly estimate: ~7,500 loads**
- **50K free tier: Would last ~6.7 months**

**Large Application (Popular Service)**
- 500 unique visitors per day
- Each visitor views map 2-3 times
- **Daily loads: ~1,250 loads**
- **Monthly estimate: ~37,500 loads**
- **50K free tier: Would last ~1.3 months**

**Very Large Application (High Traffic)**
- 2,000 unique visitors per day
- Each visitor views map 2-3 times
- **Daily loads: ~5,000 loads**
- **Monthly estimate: ~150,000 loads**
- **50K free tier: Would last ~10 days**
- **Cost after free tier: ~$500/month**

## How to Check Your Current Usage

### Option 1: Via API (If Backend is Running)

```bash
# Check your current usage
curl http://localhost:8000/api/analytics/map-usage?days=30
```

This returns:
```json
{
  "total_loads": 1250,
  "days_tracked": 30,
  "daily_average": 41.67,
  "monthly_estimate": 1250,
  "map_type_breakdown": {
    "leaflet": 1250
  },
  "loads_by_day": [
    {"date": "2025-01-01", "count": 45},
    {"date": "2025-01-02", "count": 38},
    ...
  ],
  "cost_estimates": {
    "mapbox": {
      "free_tier": 50000,
      "estimated_cost": 0,
      "tier": "free"
    }
  }
}
```

### Option 2: Via Frontend (If You Build a Dashboard)

You can call the `analyticsApi.getMapUsage()` method from your React app to display usage statistics.

### Option 3: Check Backend Logs

If analytics are being tracked, you can check the in-memory store (though it only keeps last 5,000 loads).

## Understanding Your Numbers

### If Your Monthly Estimate is:
- **< 1,000 loads**: Very small usage, free tier will last years
- **1,000 - 10,000 loads**: Small to medium, free tier lasts 5-50 months
- **10,000 - 50,000 loads**: Medium to large, free tier lasts 1-5 months
- **> 50,000 loads**: Large usage, will exceed free tier

### Cost After Free Tier (Mapbox)
- **50,001 - 100,000 loads**: ~$250/month
- **100,001 - 200,000 loads**: ~$500/month (with volume discounts)
- **200,000+ loads**: ~$750+/month (with volume discounts)

## Tips to Stay Within Free Tier

1. **Optimize Page Loads**: Reduce unnecessary page refreshes
2. **Use Caching**: Cache map tiles to reduce server requests
3. **Lazy Loading**: Only load map when user scrolls to it
4. **Session Management**: Keep users on same page instead of refreshing
5. **Monitor Daily**: Check usage regularly to catch spikes early

## Comparison: What 50K Loads Means

| Metric | 50K Loads |
|--------|-----------|
| Daily average | ~1,667 loads/day |
| Hourly average | ~69 loads/hour |
| Unique visitors (2 loads each) | ~25,000 visitors/month |
| Page views | 50,000 page views/month |
| Typical small business | 5-10 years of usage |
| Typical medium business | 6-12 months of usage |
| Typical large business | 1-2 months of usage |

## Next Steps

1. **Start Tracking**: Make sure your backend is running and tracking map loads
2. **Monitor for 1-2 Weeks**: Collect real usage data
3. **Calculate Projection**: Use daily average × 30 to estimate monthly usage
4. **Make Decision**: Based on your actual usage, decide if free tier is sufficient

## Example Calculation

If you check your usage and see:
- **Last 7 days**: 350 loads
- **Daily average**: 50 loads/day
- **Monthly projection**: 1,500 loads/month

**Conclusion**: You're using only 3% of the free tier. You have plenty of room to grow!
