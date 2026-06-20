import { authRequest } from './auth.js'
import { buildUrl } from './http.js'

function buildQuery(options = {}) {
  const params = new URLSearchParams()
  Object.entries(options).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  })
  return params.toString()
}

function collection(path) {
  return {
    list(token, options = {}) {
      const query = buildQuery(options)
      return authRequest(`/attendance/${path}${query ? `?${query}` : ''}`, { token })
    },
    create(token, payload) {
      return authRequest(`/attendance/${path}`, { method: 'POST', token, body: payload })
    },
    update(token, id, payload) {
      return authRequest(`/attendance/${path}/${id}`, { method: 'PUT', token, body: payload })
    },
    delete(token, id) {
      return authRequest(`/attendance/${path}/${id}`, { method: 'DELETE', token })
    },
  }
}

export const attendanceAPI = {
  shifts: collection('shifts'),
  restRules: collection('rest-rules'),
  schedules: collection('schedules'),
  records: collection('records'),
  requests: collection('requests'),
  dailyResults: collection('daily-results'),
  monthlySummaries: collection('monthly-summaries'),
  approveRequest(token, id, payload) {
    return authRequest(`/attendance/requests/${id}/approve`, { method: 'POST', token, body: payload })
  },
  withdrawRequest(token, id) {
    return authRequest(`/attendance/requests/${id}/withdraw`, { method: 'POST', token })
  },
  rebuildDaily(token, payload) {
    const query = buildQuery(payload)
    return authRequest(`/attendance/daily-results/rebuild?${query}`, { method: 'POST', token })
  },
  rebuildMonthly(token, payload) {
    const query = buildQuery(payload)
    return authRequest(`/attendance/monthly-summaries/rebuild?${query}`, { method: 'POST', token })
  },
  async exportReport(token, type, options = {}) {
    const path = type === 'monthly' ? 'monthly-summaries/export' : 'daily-results/export'
    const query = buildQuery(options)
    const response = await fetch(buildUrl(`/attendance/${path}${query ? `?${query}` : ''}`), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!response.ok) {
      throw new Error(response.statusText || '导出失败')
    }
    return response.blob()
  },
}
