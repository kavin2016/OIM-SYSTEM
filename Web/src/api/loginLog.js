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

export const loginLogAPI = {
  options(token) {
    return authRequest('/login-logs/options', { token })
  },
  list(token, params = {}) {
    return authRequest(requestPath('/login-logs', params), { token })
  },
  get(token, id) {
    return authRequest(`/login-logs/${id}`, { token })
  },
  export(token, params = {}) {
    return authRequest(requestPath('/login-logs/export', params), { token })
  },
}
