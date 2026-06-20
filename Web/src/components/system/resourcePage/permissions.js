import { hasPermission } from '../../../composables/useAuth.js'

const RESOURCE_PERMISSION_PREFIX = {
  users: 'system:user',
  departments: 'system:department',
  roles: 'system:role',
  positions: 'system:position',
  domains: 'system:domain',
}

export function createPermissionActions(resourceKey) {
  function operationPermission(action) {
    const prefix = RESOURCE_PERMISSION_PREFIX[resourceKey]
    return prefix ? `${prefix}:${action}` : ''
  }

  function canOperate(action) {
    const permissionCode = operationPermission(action)
    return !permissionCode || hasPermission(permissionCode)
  }

  return {
    canOperate,
    hasPermission,
    operationPermission,
  }
}
