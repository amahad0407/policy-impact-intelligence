FROM python:3.9-slim

# Prevent .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies first (better layer caching)
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI application code
COPY backend/app ./app

# Copy pre-generated analysis data (the demo data — no secrets)
WORKDIR /app
COPY data/processed ./data/processed

# Run uvicorn from /app/backend so "app.main" module resolves correctly.
# The path logic in main.py traverses 3 levels up from main.py to find /app/data/processed.
WORKDIR /app/backend

# Azure Container Apps injects PORT; default to 8000 for local docker run.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
