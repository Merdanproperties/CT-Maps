from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging

from api.routes import properties, search, filters, export, analytics, autocomplete, remediation
from database import engine, Base

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Health monitoring
health_status = {"database": True, "api": True}

def check_database_health():
    """Check database connection health (synchronous)"""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = True
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = False
        return False

def recover_database():
    """Attempt to recover database connection (synchronous)"""
    try:
        from sqlalchemy import text
        # Dispose and recreate connection pool
        engine.dispose()
        # Wait a bit before retry
        import time
        time.sleep(2)
        # Test new connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = True
        logger.info("Database connection recovered")
        return True
    except Exception as e:
        logger.error(f"Database recovery failed: {e}")
        return False

async def health_monitor_task():
    """Background task to monitor and recover services"""
    import asyncio
    import concurrent.futures
    
    # Use thread pool for sync database operations
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    while True:
        try:
            # Run sync database check in thread pool
            loop = asyncio.get_event_loop()
            db_healthy = await loop.run_in_executor(executor, check_database_health)
            
            if not db_healthy:
                logger.warning("Database unhealthy, attempting recovery...")
                await loop.run_in_executor(executor, recover_database)
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in health monitor: {e}")
            await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("Starting CT Property Search API...")
    
    # Initial health check (run in thread pool)
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, check_database_health)
    
    # Start health monitoring task
    monitor_task = asyncio.create_task(health_monitor_task())
    
    yield
    
    # Shutdown
    logger.info("Shutting down CT Property Search API...")
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="CT Property Search API",
    description="API for searching and filtering Connecticut property data",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(properties.router, prefix="/api/properties", tags=["properties"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(filters.router, prefix="/api/filters", tags=["filters"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(autocomplete.router, prefix="/api/autocomplete", tags=["autocomplete"])
app.include_router(remediation.router, prefix="/api/remediation", tags=["remediation"])

@app.get("/")
async def root():
    return {"message": "CT Property Search API", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Enhanced health check endpoint with diagnostic information"""
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_event_loop()
    
    db_healthy = await loop.run_in_executor(executor, check_database_health)
    
    if not db_healthy:
        # Attempt recovery
        await loop.run_in_executor(executor, recover_database)
        db_healthy = await loop.run_in_executor(executor, check_database_health)
    
    status = "healthy" if db_healthy else "degraded"
    
    response = {
        "status": status,
        "database": "connected" if db_healthy else "disconnected",
        "api": "operational"
    }
    
    # Add diagnostic information if unhealthy
    if not db_healthy:
        response["diagnostics"] = {
            "issue": "Database connection failed",
            "fix_steps": [
                "1. Verify PostgreSQL is running: psql -l",
                "2. Check DATABASE_URL in backend/.env",
                "3. Restart PostgreSQL if needed",
                "4. Restart backend: cd backend && source venv/bin/activate && uvicorn main:app --reload"
            ],
            "check_commands": [
                "psql -l",
                "ps aux | grep postgres",
                "cat backend/.env | grep DATABASE_URL"
            ]
        }
    
    return response
