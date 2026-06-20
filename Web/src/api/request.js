import { authAPI } from './auth.js'
import { userAPI } from './user.js'
import { adminAPI } from './admin.js'

export const api = {
  auth: authAPI,
  user: userAPI,
  admin: adminAPI,
}
