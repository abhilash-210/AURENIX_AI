# Use a specific, slim version of Python
FROM python:3.11-slim

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Create a non-root user to run the app
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install uv package manager and curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

# Copy only the files needed for dependency resolution first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies using uv directly into the system python environment
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy the rest of the application code
COPY app/ ./app/
COPY alembic.ini ./

# Change ownership to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port uvicorn runs on
EXPOSE 8000

# Healthcheck to verify the server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
