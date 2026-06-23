#!/bin/sh
set -eu

# Run on the OIM production host, from the project root or pass OIM_DATA_ROOT.
# Usage:
#   sh docs/openvpn/prepare-oim-openvpn-storage.sh
#   sh docs/openvpn/prepare-oim-openvpn-storage.sh PH-191 /path/to/private-key

SERVER_CODE="${1:-}"
SOURCE_KEY_PATH="${2:-}"
OIM_DATA_ROOT="${OIM_DATA_ROOT:-./data/oim}"
SSH_KEY_DIR="${OPENVPN_SSH_KEY_DIR:-${OIM_DATA_ROOT}/ssh}"
CLIENT_CONFIG_ROOT="${OPENVPN_CLIENT_CONFIG_ROOT:-${OIM_DATA_ROOT}/openvpn-clients}"

mkdir -p "${SSH_KEY_DIR}" "${CLIENT_CONFIG_ROOT}"
chmod 700 "${SSH_KEY_DIR}" || true
chmod 755 "${CLIENT_CONFIG_ROOT}" || true

if [ -n "${SERVER_CODE}" ]; then
  TARGET_KEY_PATH="${SSH_KEY_DIR}/${SERVER_CODE}.key"
  if [ -n "${SOURCE_KEY_PATH}" ]; then
    cp "${SOURCE_KEY_PATH}" "${TARGET_KEY_PATH}"
    chmod 600 "${TARGET_KEY_PATH}"
    echo "SSH private key installed: ${TARGET_KEY_PATH}"
  else
    echo "Expected SSH private key path for ${SERVER_CODE}: ${TARGET_KEY_PATH}"
    echo "Put the private key there, then run: chmod 600 ${TARGET_KEY_PATH}"
  fi
fi

find "${SSH_KEY_DIR}" -type f -exec chmod 600 {} \; || true

echo "OpenVPN storage is ready:"
echo "  SSH key dir: ${SSH_KEY_DIR}"
echo "  Client config root: ${CLIENT_CONFIG_ROOT}"
