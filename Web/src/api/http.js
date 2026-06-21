import { startGlobalLoading, stopGlobalLoading } from '../composables/useGlobalLoading.js'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export function buildUrl(path) {
  return `${API_BASE}${path}`
}

export function buildHeaders(headers = {}) {
  return { ...headers }
}

export function buildFormBody(data) {
  return new URLSearchParams(Object.entries(data))
}

function extractErrorMessage(data, fallback) {
  const detail = data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || item.message || JSON.stringify(item)).join('；')
  }
  if (detail && typeof detail === 'object') {
    return detail.message || detail.msg || detail.error || JSON.stringify(detail)
  }
  return detail || data?.message || fallback || '请求失败'
}

function notifyUnauthorized(path) {
  if (path === '/auth/token' || typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('auth:unauthorized'))
}

export async function handleResponse(response, path = '') {
  const text = await response.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch (error) {
    data = null
  }

  if (!response.ok) {
    if (response.status === 401) {
      notifyUnauthorized(path)
    }
    throw new Error(extractErrorMessage(data, response.statusText))
  }

  return data
}

export async function request(path, options = {}) {
  const shouldShowGlobalLoading = options.globalLoading !== false
  if (shouldShowGlobalLoading) {
    startGlobalLoading()
  }
  try {
    const { globalLoading, ...fetchOptions } = options
    if (fetchOptions.body && (!fetchOptions.method || fetchOptions.method.toUpperCase() === 'GET')) {
      fetchOptions.method = 'POST'
    }
    const response = await fetch(buildUrl(path), fetchOptions)
    return await handleResponse(response, path)
  } finally {
    if (shouldShowGlobalLoading) {
      stopGlobalLoading()
    }
  }
}
