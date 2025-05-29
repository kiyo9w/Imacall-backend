FROM python:3.10

WORKDIR /app

# Copy required files for dependency installation
COPY pyproject.toml uv.lock /app/
COPY scripts /app/scripts/
COPY alembic.ini /app/

# Install uv
RUN pip install --no-cache-dir uv

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1

# Install dependencies without mount
RUN uv pip install --system -r pyproject.toml

# Copy backend files
COPY app /app/app
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose the application port
EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"] 