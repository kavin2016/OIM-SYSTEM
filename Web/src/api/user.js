import { authRequest } from './auth.js'

export const userAPI = {
  getCurrentUser(token) {
    return authRequest('/users/me', {
      token,
    })
  },
  updateCurrentUser(token, payload) {
    return authRequest('/users/me', {
      method: 'PUT',
      token,
      body: payload,
    })
  },
  deleteCurrentUser(token) {
    return authRequest('/users/me', {
      method: 'DELETE',
      token,
    })
  },
}
