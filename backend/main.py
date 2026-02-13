from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging

from sqlalchemy.exc import OperationalError, DBAPIError

from api.routes import properties, search, filters, export, analytics, autocomplete, remediation
from database import engine, Base

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Health monitoring
health_status = {"database": True, "api": True}

# Cache database health status to avoid frequent checks
_db_health_cache = {"status": True, "timestamp": 0}
_db_health_cache_duration = 2  # Cache for 2 seconds

def check_database_health():
    """Check database connection health (synchronous, with caching)"""
    import time
    current_time = time.time()
    
    # Return cached result if still valid
    if current_time - _db_health_cache["timestamp"] < _db_health_cache_duration:
        return _db_health_cache["status"]
    
    try:
        from sqlalchemy import text
        # Use a lightweight query - just check connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = True
        _db_health_cache["status"] = True
        _db_health_cache["timestamp"] = current_time
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = False
        _db_health_cache["status"] = False
        _db_health_cache["timestamp"] = current_time
        return False

def setup_database_tables():
    """Create PostGIS extension and tables if they do not exist (e.g. fresh Docker DB)."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready (PostGIS + schema).")
    except Exception as e:
        logger.warning("Database setup skipped or failed (tables may already exist): %s", e)

def recover_database():
    """Attempt to recover database connection and ensure tables exist (synchronous)"""
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
        # Ensure schema exists (e.g. backend started before Postgres was ready)
        setup_database_tables()
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
            
            await asyncio.sleep(60)  # Check every 60s to reduce CPU
        except Exception as e:
            logger.error(f"Error in health monitor: {e}")
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("Starting CT Property Search API...")
    try:
        # Initial health check and DB setup (run in thread pool)
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, check_database_health)
        await loop.run_in_executor(executor, setup_database_tables)
    except Exception as e:
        logger.warning("Startup DB check/setup failed (app will still serve; /health will work): %s", e)
        health_status["database"] = False

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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
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


@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
async def database_exception_handler(request, exc):
    """Return 503 with clear message when database is unreachable or errors."""
    logger.error(f"Database error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database is unavailable. Check that PostgreSQL is running and DATABASE_URL is correct.",
            "error_type": type(exc).__name__,
        },
    )


@app.exception_handler(Exception)
async def catch_all_exception_handler(request, exc):
    """Convert 500 and any unhandled exception to 503 so frontend sees 'unavailable' not 500."""
    if isinstance(exc, HTTPException):
        if exc.status_code >= 500:
            logger.error(f"Server error on {request.url.path}: {exc.detail}")
            return JSONResponse(
                status_code=503,
                content={"detail": "Service temporarily unavailable. Check that PostgreSQL and the backend are running."},
            )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Service temporarily unavailable. Check that PostgreSQL and the backend are running.",
            "error_type": type(exc).__name__,
        },
    )


@app.get("/")
async def root():
    return {"message": "CT Property Search API", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Shallow liveness check - returns 200 immediately, no DB. Use for Docker and fast 'is backend up?'."""
    return {"status": "ok", "api": "operational"}


@app.get("/health/ready")
async def health_ready():
    """Readiness check including DB - use for UI banner (database connected/disconnected)."""
    import concurrent.futures

    db_healthy = False
    try:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()

        try:
            db_healthy = await asyncio.wait_for(
                loop.run_in_executor(executor, check_database_health),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            logger.warning("Database health check timed out")
            db_healthy = False
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
            db_healthy = False

        if not db_healthy:
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(executor, recover_database),
                    timeout=3.0
                )
                db_healthy = await asyncio.wait_for(
                    loop.run_in_executor(executor, check_database_health),
                    timeout=2.0
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Recovery attempt failed or timed out: {e}")
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        db_healthy = False

    status = "healthy" if db_healthy else "degraded"
    response = {
        "status": status,
        "database": "connected" if db_healthy else "disconnected",
        "api": "operational"
    }
    if not db_healthy:
        response["diagnostics"] = {
            "issue": "Database connection failed",
            "fix_steps": [
                "1. Verify PostgreSQL is running: psql -l",
                "2. Check DATABASE_URL in backend/.env",
                "3. Restart PostgreSQL if needed",
                "4. Restart backend: cd backend && source venv/bin/activate && uvicorn main:app --reload"
            ]
        }
    return response
