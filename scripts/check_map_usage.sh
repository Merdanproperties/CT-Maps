#!/bin/bash

# Check Map Usage Statistics
# This script queries the analytics API to show current map usage

echo "📊 Map Usage Statistics"
echo "========================"
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Backend is not running!"
    echo "   Start it with: ./scripts/start_all.sh"
    exit 1
fi

# Get usage data
echo "Fetching usage data..."
USAGE_DATA=$(curl -s "http://localhost:8000/api/analytics/map-usage?days=30")

# Parse and display
TOTAL_LOADS=$(echo "$USAGE_DATA" | grep -o '"total_loads":[0-9]*' | cut -d: -f2)
DAILY_AVG=$(echo "$USAGE_DATA" | grep -o '"daily_average":[0-9.]*' | cut -d: -f2)
MONTHLY_EST=$(echo "$USAGE_DATA" | grep -o '"monthly_estimate":[0-9.]*' | cut -d: -f2)
TIER=$(echo "$USAGE_DATA" | grep -o '"tier":"[^"]*"' | cut -d'"' -f4)

echo ""
echo "📈 Current Statistics (Last 30 Days):"
echo "   Total Map Loads: $TOTAL_LOADS"
echo "   Daily Average: $DAILY_AVG"
echo "   Monthly Estimate: $MONTHLY_EST"
echo ""

# Calculate percentage of free tier
if [ -n "$MONTHLY_EST" ] && [ "$MONTHLY_EST" != "0" ] && [ "$MONTHLY_EST" != "0.0" ]; then
    PERCENTAGE=$(echo "scale=2; ($MONTHLY_EST / 50000) * 100" | bc)
    echo "📊 Free Tier Usage:"
    echo "   Using: $PERCENTAGE% of 50,000 free loads/month"
    echo ""
    
    if (( $(echo "$MONTHLY_EST < 50000" | bc -l) )); then
        MONTHS_LEFT=$(echo "scale=1; 50000 / $MONTHLY_EST" | bc)
        echo "✅ Status: Within free tier"
        echo "   Free tier will last: ~$MONTHS_LEFT months at current rate"
    else
        EXCESS=$(echo "$MONTHLY_EST - 50000" | bc)
        COST=$(echo "scale=2; $EXCESS * 0.005" | bc)
        echo "⚠️  Status: Exceeds free tier"
        echo "   Estimated cost: \$$COST/month"
    fi
else
    echo "ℹ️  No usage data yet"
    echo "   This could mean:"
    echo "   - Backend was recently restarted (analytics are in-memory)"
    echo "   - Map page hasn't been opened since tracking was added"
    echo ""
    echo "   To test: Open your map page, then run this script again!"
fi

echo ""
echo "💡 Tip: Map loads are counted when you:"
echo "   - Open the map page"
echo "   - Refresh the page"
echo "   - Navigate back to the map"
echo ""
echo "   NOT counted:"
echo "   - Searching for properties"
echo "   - Filtering results"
echo "   - Zooming or panning"
echo ""
