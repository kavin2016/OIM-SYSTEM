#!/usr/bin/env bash
set -euo pipefail

# Install OIM OpenVPN event hooks on a new OpenVPN server.
#
# Usage:
#   sudo bash install-openvpn-oim-hooks.sh local /path/to/openvpn/server.conf
#   sudo bash install-openvpn-oim-hooks.sh production /path/to/openvpn/server.conf
#
# Required environment variables:
#   OIM_OPENVPN_EVENT_URL
#   OIM_OPENVPN_EVENT_TOKEN
#   OIM_OPENVPN_SERVER_CODE
#
# Optional environment variables:
#   OIM_OPENVPN_CONNECT_SOURCE
#   OIM_OPENVPN_DISCONNECT_SOURCE
#   OIM_OPENVPN_SERVICE

MODE="${1:-}"
OPENVPN_CONFIG="${2:-/etc/openvpn/server.conf}"

if [[ "${MODE}" != "local" && "${MODE}" != "production" ]]; then
  echo "Usage: sudo bash $0 local|production [/path/to/openvpn/server.conf]" >&2
  exit 2
fi

: "${OIM_OPENVPN_EVENT_URL:?OIM_OPENVPN_EVENT_URL is required}"
: "${OIM_OPENVPN_EVENT_TOKEN:?OIM_OPENVPN_EVENT_TOKEN is required}"
: "${OIM_OPENVPN_SERVER_CODE:?OIM_OPENVPN_SERVER_CODE is required}"

CONNECT_TARGET="/etc/openvpn/oim-client-connect.sh"
DISCONNECT_TARGET="/etc/openvpn/oim-client-disconnect.sh"
CONNECT_SOURCE="${OIM_OPENVPN_CONNECT_SOURCE:-./openvpn-client-connect.sh}"
DISCONNECT_SOURCE="${OIM_OPENVPN_DISCONNECT_SOURCE:-./openvpn-client-disconnect.sh}"
OPENVPN_SERVICE="${OIM_OPENVPN_SERVICE:-openvpn-server@server.service}"
BACKUP_PATH="${OPENVPN_CONFIG}.oim-backup-$(date +%Y%m%d%H%M%S)"

if [[ ! -f "${OPENVPN_CONFIG}" ]]; then
  echo "OpenVPN config not found: ${OPENVPN_CONFIG}" >&2
  exit 1
fi

if [[ ! -f "${CONNECT_SOURCE}" ]]; then
  echo "Connect script source not found: ${CONNECT_SOURCE}" >&2
  exit 1
fi

if [[ ! -f "${DISCONNECT_SOURCE}" ]]; then
  echo "Disconnect script source not found: ${DISCONNECT_SOURCE}" >&2
  exit 1
fi

install -m 0755 "${CONNECT_SOURCE}" "${CONNECT_TARGET}"
install -m 0755 "${DISCONNECT_SOURCE}" "${DISCONNECT_TARGET}"
cp "${OPENVPN_CONFIG}" "${BACKUP_PATH}"

python3 - "$OPENVPN_CONFIG" <<'PY'
from pathlib import Path
import os
import sys

path = Path(sys.argv[1])
content = path.read_text()
lines = [
    "script-security 2",
    f"setenv OIM_OPENVPN_EVENT_URL {os.environ['OIM_OPENVPN_EVENT_URL']}",
    f"setenv OIM_OPENVPN_EVENT_TOKEN {os.environ['OIM_OPENVPN_EVENT_TOKEN']}",
    f"setenv OIM_OPENVPN_SERVER_CODE {os.environ['OIM_OPENVPN_SERVER_CODE']}",
    "client-connect /etc/openvpn/oim-client-connect.sh",
    "client-disconnect /etc/openvpn/oim-client-disconnect.sh",
]

filtered = []
for line in content.splitlines():
    stripped = line.strip()
    if stripped.startswith("setenv OIM_OPENVPN_"):
      continue
    if stripped.startswith("client-connect "):
      continue
    if stripped.startswith("client-disconnect "):
      continue
    if stripped == "script-security 2":
      continue
    filtered.append(line)

filtered.extend(["", "# OIM OpenVPN integration", *lines])
path.write_text("\n".join(filtered).rstrip() + "\n")
PY

systemctl restart "${OPENVPN_SERVICE}"
systemctl --no-pager --full status "${OPENVPN_SERVICE}" | sed -n '1,20p'

echo "Installed OIM OpenVPN hooks."
echo "Config backup: ${BACKUP_PATH}"
