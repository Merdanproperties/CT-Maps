from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from api.routes import properties, search, filters, export, analytics, autocomplete
from database import engine, Base

app = FastAPI(
    title="CT Property Search API",
    description="API for searching and filtering Connecticut property data",
    version="1.0.0"
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

@app.get("/")
async def root():
    return {"message": "CT Property Search API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
