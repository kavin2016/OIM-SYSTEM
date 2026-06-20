import { authRequest } from './auth.js'

function buildQuery({ skip = 0, limit = 100, includeDisabled = false, includeDeleted = false, ...filters } = {}) {
  const params = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
    include_disabled: String(includeDisabled),
    include_deleted: String(includeDeleted),
  })
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  })
  return params.toString()
}

function resourceAPI(path) {
  return {
    list(token, options = {}) {
      return authRequest(`/${path}?${buildQuery(options)}`, { token })
    },
    create(token, payload) {
      return authRequest(`/${path}`, {
        method: 'POST',
        token,
        body: payload,
      })
    },
    get(token, id, options = {}) {
      const params = new URLSearchParams({
        include_deleted: String(options.includeDeleted || false),
      })
      return authRequest(`/${path}/${id}?${params.toString()}`, { token })
    },
    update(token, id, payload) {
      return authRequest(`/${path}/${id}`, {
        method: 'PUT',
        token,
        body: payload,
      })
    },
    delete(token, id) {
      return authRequest(`/${path}/${id}`, {
        method: 'DELETE',
        token,
      })
    },
    batchDelete(token, ids) {
      return authRequest(`/${path}/batch-delete`, {
        method: 'POST',
        token,
        body: { [`${path.slice(0, -1)}_ids`]: ids },
      })
    },
  }
}

export const adminAPI = {
  users: resourceAPI('users'),
  departments: resourceAPI('departments'),
  roles: resourceAPI('roles'),
  positions: resourceAPI('positions'),
  domains: resourceAPI('domains'),
  permissions: resourceAPI('permissions'),
  listUserDepartments(token, userId) {
    return authRequest(`/users/${userId}/departments`, { token })
  },
  listUserRoles(token, userId) {
    return authRequest(`/users/${userId}/roles`, { token })
  },
  listUserPositions(token, userId) {
    return authRequest(`/users/${userId}/positions`, { token })
  },
  assignUserRoles(token, userId, roleIds) {
    return authRequest(`/users/${userId}/roles`, {
      method: 'PUT',
      token,
      body: { role_ids: roleIds },
    })
  },
  resetUserPassword(token, userId, password) {
    return authRequest(`/users/${userId}/reset-password`, {
      method: 'POST',
      token,
      body: { password },
    })
  },
  listRolePermissions(token, roleId) {
    return authRequest(`/roles/${roleId}/permissions`, { token })
  },
}
