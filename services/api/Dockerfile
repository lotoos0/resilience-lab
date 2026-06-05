# Minimal API Dockerfile with security baseline (M0)
# Updated: 2025-10-29

FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade "wheel>=0.46.2" && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (will be added in next commits)
COPY services/api/ ./services/api/

# Security: Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# Run the service
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
