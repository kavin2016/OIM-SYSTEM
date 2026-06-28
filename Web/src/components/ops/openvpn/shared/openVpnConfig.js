export const openVpnTabs = [
  { key: 'servers', label: '服务器管理', permission: 'ops:openvpn:server:query' },
  { key: 'accounts', label: '用户管理', permission: 'ops:openvpn:account:query' },
  { key: 'sessions', label: '在线会话', permission: 'ops:openvpn:session:query' },
  { key: 'logs', label: '连接日志', permission: 'ops:openvpn:log:query' },
  { key: 'rules', label: '分配策略', permission: 'ops:openvpn:rule:query' },
  { key: 'traffic', label: '流量统计', permission: 'ops:openvpn:traffic:query' },
]

export const openVpnTabPaths = {
  servers: '/ops/vpn/servers',
  accounts: '/ops/vpn/accounts',
  sessions: '/ops/vpn/sessions',
  logs: '/ops/vpn/logs',
  rules: '/ops/vpn/rules',
  traffic: '/ops/vpn/traffic',
}

export const openVpnRouteTabMap = {
  '/ops/vpn/servers': 'servers',
  '/ops/vpn/accounts': 'accounts',
  '/ops/vpn/sessions': 'sessions',
  '/ops/vpn/logs': 'logs',
  '/ops/vpn/rules': 'rules',
  '/ops/vpn/traffic': 'traffic',
  '/ops/openvpn/servers': 'servers',
  '/ops/openvpn/accounts': 'accounts',
  '/ops/openvpn/sessions': 'sessions',
  '/ops/openvpn/logs': 'logs',
  '/ops/openvpn/rules': 'rules',
  '/ops/openvpn/traffic': 'traffic',
}

export const openVpnStatusTextMap = {
  online: '在线',
  offline: '离线',
  maintenance: '维护',
  disabled: '停用',
  pending: '待开通',
  enabled: '已启用',
  revoked: '已吊销',
  issued: '已签发',
  expired: '已过期',
}

export function emptyOpenVpnServerForm() {
  return {
    name: '',
    code: '',
    vpn_type: 'openvpn',
    region: '',
    host: '',
    port: 1194,
    protocol: 'udp',
    max_clients: 0,
    current_clients: 0,
    status: 'online',
    is_default: false,
    is_active: true,
    certificate_backend: 'ssh_easyrsa',
    ssh_host: '',
    ssh_port: 22,
    ssh_user: '',
    ssh_key_path: '',
    ssh_private_key_content: '',
    easy_rsa_dir: '',
    pki_dir: '',
    ca_cert_path: '',
    tls_crypt_key_path: '',
    crl_path: '',
    client_config_dir: '',
    config_template: '',
    wg_interface: 'wg0',
    wg_network_cidr: '10.66.0.0/24',
    wg_dns: '1.1.1.1,1.0.0.1',
    wg_allowed_ips: '0.0.0.0/0,::/0',
    wg_persistent_keepalive: 25,
    wg_public_key: '',
    remark: '',
  }
}

export function asOpenVpnArray(value) {
  return Array.isArray(value) ? value : []
}

export function formatOpenVpnDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

export function openVpnStatusText(value) {
  return openVpnStatusTextMap[value] || value || '-'
}

export function resetOpenVpnReactive(target, source) {
  Object.keys(target).forEach((key) => delete target[key])
  Object.assign(target, source)
}

export function downloadOpenVpnTextFile(filename, content, type = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function emptyOpenVpnRuleForm() {
  return {
    name: '',
    server_id: '',
    target_type: 'department',
    target_id: '',
    priority: 100,
    fallback_enabled: false,
    is_active: true,
    remark: '',
  }
}

export const openVpnPageSizeOptions = [20, 50, 100, 200, 500]

export function emptyOpenVpnPagination(pageSize = 20) {
  return {
    page: 1,
    pageSize,
    hasNext: false,
  }
}

export function openVpnPageParams(pagination) {
  return {
    skip: (pagination.page - 1) * pagination.pageSize,
    limit: pagination.pageSize + 1,
  }
}

export function sliceOpenVpnPageRows(rows, pagination) {
  const safeRows = asOpenVpnArray(rows)
  pagination.hasNext = safeRows.length > pagination.pageSize
  return safeRows.slice(0, pagination.pageSize)
}

export function resetOpenVpnPagination(pagination) {
  pagination.page = 1
  pagination.hasNext = false
}

export function openVpnPageStart(pagination, currentLength) {
  if (!currentLength) return 0
  return (pagination.page - 1) * pagination.pageSize + 1
}

export function openVpnPageEnd(pagination, currentLength) {
  if (!currentLength) return 0
  return (pagination.page - 1) * pagination.pageSize + currentLength
}

export function openVpnPaginationTotal(pagination, currentLength) {
  return openVpnPageEnd(pagination, currentLength) + (pagination.hasNext ? 1 : 0)
}
