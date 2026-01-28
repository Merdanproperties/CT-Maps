# CT Maps backend - FastAPI + uvicorn
FROM python:3.11-slim

WORKDIR /app

# API only: no fiona/geopandas (used by scripts, excluded from image). curl for healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY api/ api/
COPY database.py main.py models.py ./
COPY services/ services/

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# 2 workers to handle health + search + options without one request blocking others
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
