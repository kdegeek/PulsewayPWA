# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set environment variables for builder stage
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Set work directory for builder
WORKDIR /build

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies into a specific prefix
RUN pip install --no-cache-dir --prefix="/install" -r requirements.txt

# Stage 2: Final image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.11/site-packages"

# Create a non-root user and group
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser

# Set work directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY ./backend/ /app/

# Create and set permissions for data directory (before switching user)
# /app/data is also a volume mount point, permissions might be managed by Docker at runtime.
# However, ensuring the directory exists with correct ownership is good practice.
RUN mkdir -p /app/data && chown -R appuser:appgroup /app/data
RUN chown -R appuser:appgroup /app

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
