import { ref, computed } from 'vue'
import { api } from '../api/request.js'

const token = ref(localStorage.getItem('auth_token') || '')
const user = ref(null)
const menus = ref([])
const permissions = ref([])
const authLoading = ref(false)

const isAuthenticated = computed(() => !!token.value)
const permissionSet = computed(() => new Set(permissions.value))

function saveToken(value) {
  token.value = value
  if (value) {
    localStorage.setItem('auth_token', value)
  } else {
    localStorage.removeItem('auth_token')
  }
}

function clearAuth() {
  saveToken('')
  user.value = null
  menus.value = []
  permissions.value = []
}

async function getMe() {
  if (!token.value) {
    user.value = null
    menus.value = []
    return null
  }

  authLoading.value = true
  try {
    const session = await api.auth.getSession(token.value)
    user.value = session.user
    menus.value = session.menus
    permissions.value = session.permissions
    return session.user
  } catch (error) {
    clearAuth()
    throw error
  } finally {
    authLoading.value = false
  }
}

async function login({ username, password, captcha, captchaToken }) {
  const data = await api.auth.login({
    username,
    password,
    captcha,
    captchaToken,
  })

  saveToken(data.access_token)
  try {
    await getMe()
  } catch (error) {
    clearAuth()
    throw error
  }
  return data
}

function logout() {
  clearAuth()
}

function hasPermission(code) {
  return permissionSet.value.has(code)
}

export { token, user, menus, permissions, authLoading, isAuthenticated, hasPermission, login, logout, getMe }
