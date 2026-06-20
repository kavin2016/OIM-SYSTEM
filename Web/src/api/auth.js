import { buildHeaders, request, buildFormBody } from './http.js'

function getAuthHeaders(token) {
  const headers = buildHeaders()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

export async function authRequest(path, { token, body, method = 'GET', headers = {}, isForm = false } = {}) {
  const requestHeaders = { ...getAuthHeaders(token), ...headers }

  let requestBody = body
  if (isForm && body) {
    requestHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
    requestBody = buildFormBody(body)
  } else if (body && typeof body === 'object') {
    requestHeaders['Content-Type'] = 'application/json'
    requestBody = JSON.stringify(body)
  }

  return request(path, {
    method,
    headers: requestHeaders,
    body: requestBody,
  })
}

export const authAPI = {
  getCaptcha() {
    return request(`/auth/captcha?_=${Date.now()}`, {
      cache: 'no-store',
      globalLoading: false,
    })
  },
  login({ username, password, captcha, captchaToken }) {
    return authRequest('/auth/token', {
      method: 'POST',
      isForm: true,
      body: {
        username,
        password,
        captcha,
        captcha_token: captchaToken,
      },
    })
  },
  register(payload) {
    return authRequest('/auth/register', {
      method: 'POST',
      body: payload,
    })
  },
  getCurrentUser(token) {
    return authRequest('/auth/me', {
      token,
    })
  },
  getSession(token) {
    return authRequest('/auth/session', {
      token,
    })
  },
  getCurrentMenus(token) {
    return authRequest('/auth/menus', {
      token,
    })
  },
  getCurrentPermissions(token) {
    return authRequest('/auth/permissions', {
      token,
    })
  },
}
