# Dienstplan - Docker Image
# Python OR-Tools Shift Planning System

FROM python:3.11-slim

LABEL maintainer="Timo Braun"
LABEL description="Dienstplan - Automatisches Schichtverwaltungssystem"
LABEL version="2.1"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies (without build tools for production)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY api/ ./api/
COPY wwwroot/ ./wwwroot/
COPY migrations/ ./migrations/
COPY *.py ./
COPY alembic.ini .

# Create data directory for persistent database storage
RUN mkdir -p /data

# Expose application port
EXPOSE 5000

# Environment variables with defaults
ENV DB_PATH=/data/dienstplan.db
ENV HOST=0.0.0.0
ENV PORT=5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

# Initialize database and start server
CMD ["sh", "-c", "python main.py init-db --db ${DB_PATH} && python main.py serve --host ${HOST} --port ${PORT} --db ${DB_PATH}"]
