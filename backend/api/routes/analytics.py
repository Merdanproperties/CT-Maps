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

class AnalyticsResponse(BaseModel):
    total_searches: int
    popular_filters: list
    popular_municipalities: list
    average_results_per_search: float

# In-memory analytics store (in production, use Redis or database)
analytics_store = {
    'searches': [],
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
    
    return AnalyticsResponse(
        total_searches=total_searches,
        popular_filters=[{"filter": k, "count": v} for k, v in popular_filters],
        popular_municipalities=[{"municipality": k, "count": v} for k, v in popular_municipalities],
        average_results_per_search=round(avg_results, 2)
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
