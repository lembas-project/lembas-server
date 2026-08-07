#!/bin/sh
set -e

# Run database migrations
alembic upgrade head

# Start the application
exec "$@"
