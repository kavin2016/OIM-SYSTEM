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

export const operationLogAPI = {
  options(token) {
    return authRequest('/operation-logs/options', { token })
  },
  list(token, params = {}) {
    return authRequest(requestPath('/operation-logs', params), { token })
  },
  get(token, id) {
    return authRequest(`/operation-logs/${id}`, { token })
  },
  export(token, params = {}) {
    return authRequest(requestPath('/operation-logs/export', params), { token })
  },
}
