#!/bin/sh
set -eu

echo "Waiting for MySQL at ${MYSQL_HOST}:${MYSQL_PORT}..."
until mysqladmin ping -h"${MYSQL_HOST}" -P"${MYSQL_PORT}" -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" --ssl=0 --silent; do
  sleep 2
done

echo "Running database migrations..."
alembic upgrade head

echo "Starting OIM backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
