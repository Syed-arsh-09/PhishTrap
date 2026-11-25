# ==============================================================================
# PhishTrap Production Dockerfile
# Serves FastAPI REST API + Precompiled React SecOps Dashboard on single port
# ==============================================================================

FROM python:3.12-slim

# Prevent Python from writing bytecode and enable unbuffered terminal output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set working directory inside container
WORKDIR /app

# Install minimal OS utilities (curl for container healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code, trained model weights, and precompiled frontend bundle
COPY src/ ./src/
COPY models/ ./models/
COPY frontend/dist/ ./frontend/dist/
COPY scripts/ ./scripts/

# Ensure SQLite storage directory exists
RUN mkdir -p /app/data

# Expose default port
EXPOSE 8000

# Health check to ensure API is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start Uvicorn web server
# Uses shell form so cloud container platforms (Render, Railway, Fly.io, etc.)
# can inject their custom dynamic $PORT variable.
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
