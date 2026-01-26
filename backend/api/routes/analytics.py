from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import json

router = APIRouter()

class SearchEvent(BaseModel):
    query: Optional[str] = None
    filter_type: Optional[str] = None
    municipality: Optional[str] = None
    result_count: int

class MapLoadEvent(BaseModel):
    map_type: Optional[str] = None  # e.g., 'leaflet', 'mapbox', 'google'
    viewport: Optional[dict] = None  # center, zoom, bounds
    user_agent: Optional[str] = None
    fallback_reason: Optional[str] = None  # Reason for fallback if applicable

class AnalyticsResponse(BaseModel):
    total_searches: int
    popular_filters: list
    popular_municipalities: list
    average_results_per_search: float
    total_map_loads: int
    map_loads_by_day: list

# In-memory analytics store (in production, use Redis or database)
analytics_store = {
    'searches': [],
    'map_loads': [],
    'filter_usage': {},
    'municipality_searches': {},
    'total_results': 0
}

@router.post("/track-search")
async def track_search(event: SearchEvent, request: Request):
    """Track a search event for analytics"""
    # Store search event
    analytics_store['searches'].append({
        'timestamp': datetime.now().isoformat(),
        'query': event.query,
        'filter_type': event.filter_type,
        'municipality': event.municipality,
        'result_count': event.result_count,
        'ip': request.client.host if request.client else None
    })
    
    # Track filter usage
    if event.filter_type:
        analytics_store['filter_usage'][event.filter_type] = \
            analytics_store['filter_usage'].get(event.filter_type, 0) + 1
    
    # Track municipality searches
    if event.municipality:
        analytics_store['municipality_searches'][event.municipality] = \
            analytics_store['municipality_searches'].get(event.municipality, 0) + 1
    
    analytics_store['total_results'] += event.result_count
    
    # Keep only last 1000 searches in memory
    if len(analytics_store['searches']) > 1000:
        analytics_store['searches'] = analytics_store['searches'][-1000:]
    
    return {"status": "tracked"}

@router.post("/track-map-load")
async def track_map_load(event: MapLoadEvent, request: Request):
    """Track a map load event for analytics"""
    # Store map load event
    map_load_data = {
        'timestamp': datetime.now().isoformat(),
        'map_type': event.map_type or 'leaflet',
        'viewport': event.viewport,
        'user_agent': event.user_agent or request.headers.get('user-agent'),
        'ip': request.client.host if request.client else None
    }
    
    # Track fallback if applicable
    if event.fallback_reason:
        map_load_data['fallback_reason'] = event.fallback_reason
        map_load_data['fallback'] = True
        print(f"⚠️ Map fallback tracked: {event.fallback_reason}")
    
    analytics_store['map_loads'].append(map_load_data)
    
    # Keep only last 5000 map loads in memory
    if len(analytics_store['map_loads']) > 5000:
        analytics_store['map_loads'] = analytics_store['map_loads'][-5000:]
    
    return {"status": "tracked"}

@router.get("/stats")
async def get_analytics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get analytics statistics"""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Filter recent searches
    recent_searches = [
        s for s in analytics_store['searches']
        if datetime.fromisoformat(s['timestamp']) >= cutoff_date
    ]
    
    total_searches = len(recent_searches)
    
    # Calculate average results
    avg_results = 0
    if total_searches > 0:
        total_results = sum(s['result_count'] for s in recent_searches)
        avg_results = total_results / total_searches
    
    # Get popular filters
    popular_filters = sorted(
        analytics_store['filter_usage'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Get popular municipalities
    popular_municipalities = sorted(
        analytics_store['municipality_searches'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Filter recent map loads
    recent_map_loads = [
        m for m in analytics_store['map_loads']
        if datetime.fromisoformat(m['timestamp']) >= cutoff_date
    ]
    
    total_map_loads = len(recent_map_loads)
    
    # Calculate map loads by day
    map_loads_by_day = {}
    for load in recent_map_loads:
        load_date = datetime.fromisoformat(load['timestamp']).date()
        map_loads_by_day[str(load_date)] = map_loads_by_day.get(str(load_date), 0) + 1
    
    # Convert to list format sorted by date
    map_loads_by_day_list = [
        {"date": date, "count": count}
        for date, count in sorted(map_loads_by_day.items())
    ]
    
    return AnalyticsResponse(
        total_searches=total_searches,
        popular_filters=[{"filter": k, "count": v} for k, v in popular_filters],
        popular_municipalities=[{"municipality": k, "count": v} for k, v in popular_municipalities],
        average_results_per_search=round(avg_results, 2),
        total_map_loads=total_map_loads,
        map_loads_by_day=map_loads_by_day_list
    )

@router.get("/popular-searches")
async def get_popular_searches(days: int = 7):
    """Get popular search queries"""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    recent_searches = [
        s for s in analytics_store['searches']
        if datetime.fromisoformat(s['timestamp']) >= cutoff_date and s['query']
    ]
    
    # Count query frequency
    query_counts = {}
    for search in recent_searches:
        query = search['query'].lower().strip()
        if query:
            query_counts[query] = query_counts.get(query, 0) + 1
    
    popular = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    return [{"query": k, "count": v} for k, v in popular]

@router.get("/map-usage")
async def get_map_usage(days: int = 30):
    """Get map usage statistics for cost estimation"""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    recent_map_loads = [
        m for m in analytics_store['map_loads']
        if datetime.fromisoformat(m['timestamp']) >= cutoff_date
    ]
    
    total_loads = len(recent_map_loads)
    
    # Calculate daily averages
    days_count = max(days, 1)
    daily_average = total_loads / days_count
    monthly_estimate = daily_average * 30
    
    # Group by map type
    map_type_counts = {}
    for load in recent_map_loads:
        map_type = load.get('map_type', 'unknown')
        map_type_counts[map_type] = map_type_counts.get(map_type, 0) + 1
    
    # Calculate loads by day
    loads_by_day = {}
    for load in recent_map_loads:
        load_date = datetime.fromisoformat(load['timestamp']).date()
        loads_by_day[str(load_date)] = loads_by_day.get(str(load_date), 0) + 1
    
    loads_by_day_list = [
        {"date": date, "count": count}
        for date, count in sorted(loads_by_day.items())
    ]
    
    return {
        "total_loads": total_loads,
        "days_tracked": days_count,
        "daily_average": round(daily_average, 2),
        "monthly_estimate": round(monthly_estimate, 0),
        "map_type_breakdown": map_type_counts,
        "loads_by_day": loads_by_day_list,
        "cost_estimates": {
            "mapbox": {
                "free_tier": 50000,
                "estimated_cost": max(0, (monthly_estimate - 50000) * 0.005) if monthly_estimate > 50000 else 0,
                "tier": "free" if monthly_estimate <= 50000 else "pay_as_you_go"
            },
            "google_maps": {
                "starter_plan": 50000,
                "cost": 100 if monthly_estimate <= 50000 else 275,
                "plan": "starter" if monthly_estimate <= 50000 else "essentials"
            }
        }
    }
