#!/bin/bash
# Run migrations, seed, and start the server.
# PostgreSQL readiness is handled by docker-compose healthcheck.
set -e

# Ensure log directory exists
mkdir -p /app/logs

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "🌱 Seeding admin user..."
python manage.py seed_admin

echo "🚀 Starting server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --config /app/gunicorn.conf.py
