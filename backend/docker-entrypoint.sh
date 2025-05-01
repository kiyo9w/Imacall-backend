#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Creating initial data"
python -m app.initial_data

echo "Migrations and initial data finished. Starting server..."
# Execute the command passed as arguments to this script (which will be the Docker CMD)
# Or, directly execute the intended Uvicorn command if CMD is removed/changed
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4 