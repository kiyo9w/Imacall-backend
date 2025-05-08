FROM python:3.10

WORKDIR /app

# Copy required files for dependency installation
COPY backend/pyproject.toml backend/uv.lock /app/
COPY backend/scripts /app/scripts/
COPY backend/alembic.ini /app/

# Install uv
RUN pip install --no-cache-dir uv

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1

# Install dependencies without mount
RUN uv pip install --system -r pyproject.toml

# Copy backend files
COPY backend/app /app/app
COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose the application port
EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"] 