#!/bin/sh
set -e
attempt=0
until python manage.py migrate --noinput; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 15 ]; then
    echo "migrations failed" >&2
    exit 1
  fi
  sleep 2
done
python manage.py seed_users
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
