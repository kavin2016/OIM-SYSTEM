#!/bin/sh
set -eu

OPENVPN_SSH_KEY_DIR="${OPENVPN_SSH_KEY_DIR:-/data/oim/ssh}"
OPENVPN_CLIENT_CONFIG_ROOT="${OPENVPN_CLIENT_CONFIG_ROOT:-/data/oim/openvpn-clients}"

echo "Preparing OpenVPN storage..."
mkdir -p "${OPENVPN_SSH_KEY_DIR}" "${OPENVPN_CLIENT_CONFIG_ROOT}"
chmod 700 "${OPENVPN_SSH_KEY_DIR}" || true
chmod 755 "${OPENVPN_CLIENT_CONFIG_ROOT}" || true
if [ -n "${OPENVPN_DEFAULT_SSH_KEY_PATH:-}" ]; then
  mkdir -p "$(dirname "${OPENVPN_DEFAULT_SSH_KEY_PATH}")"
fi
if find "${OPENVPN_SSH_KEY_DIR}" -type f >/dev/null 2>&1; then
  find "${OPENVPN_SSH_KEY_DIR}" -type f -exec chmod 600 {} \; || true
fi

echo "Waiting for MySQL at ${MYSQL_HOST}:${MYSQL_PORT}..."
until mysqladmin ping -h"${MYSQL_HOST}" -P"${MYSQL_PORT}" -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" --ssl=0 --silent; do
  sleep 2
done

echo "Running database migrations..."
alembic upgrade head

echo "Starting OIM backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
