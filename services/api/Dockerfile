# Minimal API Dockerfile with security baseline (M0)
# Updated: 2025-10-29

FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (will be added in next commits)
COPY services/api/ ./services/api/

# Security: Switch to non-root user
USER appuser

# Health check (basic for now)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "print('healthy')" || exit 1

# Placeholder entrypoint (will be replaced with uvicorn in next commits)
CMD ["python", "-c", "print('API service container is ready'); import time; time.sleep(3600)"]
