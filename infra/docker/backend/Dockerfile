# =============================================================================
# PlantOps Backend Dockerfile
# =============================================================================
# Uses uv for fast, reproducible Python dependency management.
# =============================================================================

# ---------------------------------------------------------------------------
# Base stage
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS base

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Install dependencies first (for layer caching)
COPY backend/pyproject.toml ./
RUN uv pip install --system --no-cache -e .

# ---------------------------------------------------------------------------
# Development stage
# ---------------------------------------------------------------------------
FROM base AS development

ENV DJANGO_SETTINGS_MODULE=config.settings.local
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY backend/ ./

# Expose Django dev server port
EXPOSE 8000

# Default command (overridden in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------------------
# Production stage
# ---------------------------------------------------------------------------
FROM base AS production

ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user
RUN groupadd -r plantops && useradd -r -g plantops plantops

# Copy application code
COPY backend/ ./

# Collect static files
RUN python manage.py collectstatic --noinput

# Change ownership
RUN chown -R plantops:plantops /app
USER plantops

# Expose Gunicorn port
EXPOSE 8000

# Run with Gunicorn (configured via docker-compose or orchestrator)
CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000", "-w", "4"]
