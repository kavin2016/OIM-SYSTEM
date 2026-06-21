#!/usr/bin/env sh
set -eu

: "${OIM_OPENVPN_EVENT_URL:?OIM_OPENVPN_EVENT_URL is required}"
: "${OIM_OPENVPN_EVENT_TOKEN:?OIM_OPENVPN_EVENT_TOKEN is required}"
: "${OIM_OPENVPN_SERVER_CODE:?OIM_OPENVPN_SERVER_CODE is required}"

COMMON_NAME="${common_name:-}"
VIRTUAL_IP="${ifconfig_pool_remote_ip:-}"
REAL_IP="${trusted_ip:-${untrusted_ip:-}}"

payload=$(printf '{"server_code":"%s","common_name":"%s","virtual_ip":"%s","real_ip":"%s","message":"client-connect"}' \
  "$OIM_OPENVPN_SERVER_CODE" "$COMMON_NAME" "$VIRTUAL_IP" "$REAL_IP")

curl -fsS \
  -X POST "${OIM_OPENVPN_EVENT_URL%/}/openvpn/events/connect" \
  -H "Content-Type: application/json" \
  -H "X-OpenVPN-Token: ${OIM_OPENVPN_EVENT_TOKEN}" \
  --data "$payload" >/dev/null || logger -t openvpn-oim "client-connect event sync failed for ${COMMON_NAME}"

exit 0
