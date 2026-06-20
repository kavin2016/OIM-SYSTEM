import { authRequest } from './auth.js'

function buildQuery(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  })
  return search.toString()
}

function requestPath(path, params = {}) {
  const query = buildQuery(params)
  return query ? `${path}?${query}` : path
}

export const openvpnAPI = {
  listOptions(token) {
    return authRequest('/openvpn/options', { token })
  },
  listServers(token, params = {}) {
    return authRequest(requestPath('/openvpn/servers', params), { token })
  },
  createServer(token, payload) {
    return authRequest('/openvpn/servers', { method: 'POST', token, body: payload })
  },
  updateServer(token, id, payload) {
    return authRequest(`/openvpn/servers/${id}`, { method: 'PUT', token, body: payload })
  },
  deleteServer(token, id) {
    return authRequest(`/openvpn/servers/${id}`, { method: 'DELETE', token })
  },
  setDefaultServer(token, id) {
    return authRequest(`/openvpn/servers/${id}/set-default`, { method: 'POST', token })
  },
  testServer(token, id) {
    return authRequest(`/openvpn/servers/${id}/test`, { method: 'POST', token })
  },
  listAccounts(token, params = {}) {
    return authRequest(requestPath('/openvpn/accounts', params), { token })
  },
  enableAccount(token, userId, payload) {
    return authRequest(`/openvpn/accounts/${userId}/enable`, { method: 'POST', token, body: payload })
  },
  disableAccount(token, userId) {
    return authRequest(`/openvpn/accounts/${userId}/disable`, { method: 'POST', token })
  },
  assignAccountServer(token, accountId, serverId) {
    return authRequest(`/openvpn/accounts/${accountId}/assign-server`, {
      method: 'POST',
      token,
      body: { server_id: serverId || null },
    })
  },
  downloadConfig(token, accountId) {
    return authRequest(`/openvpn/accounts/${accountId}/download-config`, { token })
  },
  listCertificates(token, params = {}) {
    return authRequest(requestPath('/openvpn/certificates', params), { token })
  },
  issueCertificate(token, accountId, payload = {}) {
    return authRequest(`/openvpn/accounts/${accountId}/certificates/issue`, { method: 'POST', token, body: payload })
  },
  revokeCertificate(token, certId, reason = '') {
    return authRequest(`/openvpn/certificates/${certId}/revoke`, {
      method: 'POST',
      token,
      body: { reason },
    })
  },
  renewCertificate(token, certId, payload = {}) {
    return authRequest(`/openvpn/certificates/${certId}/renew`, { method: 'POST', token, body: payload })
  },
  listSessions(token, params = {}) {
    return authRequest(requestPath('/openvpn/sessions', params), { token })
  },
  kickSession(token, sessionId) {
    return authRequest(`/openvpn/sessions/${sessionId}/kick`, { method: 'POST', token })
  },
  listLogs(token, params = {}) {
    return authRequest(requestPath('/openvpn/logs', params), { token })
  },
  exportLogs(token, params = {}) {
    return authRequest(requestPath('/openvpn/logs/export', params), { token })
  },
  listRules(token, params = {}) {
    return authRequest(requestPath('/openvpn/assignment-rules', params), { token })
  },
  createRule(token, payload) {
    return authRequest('/openvpn/assignment-rules', { method: 'POST', token, body: payload })
  },
  updateRule(token, id, payload) {
    return authRequest(`/openvpn/assignment-rules/${id}`, { method: 'PUT', token, body: payload })
  },
  deleteRule(token, id) {
    return authRequest(`/openvpn/assignment-rules/${id}`, { method: 'DELETE', token })
  },
}
