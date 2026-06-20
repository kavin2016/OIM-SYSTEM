import { api } from '../../../api/request.js'
import { token } from '../../../composables/useAuth.js'

export function createOptionActions(ctx) {
  const {
    canAccessPage,
    departmentNameMap,
    departmentOptions,
    filterDepartmentTree,
    message,
    permissionOptions,
    positionOptions,
    resourceKey,
    roleOptions,
  } = ctx

  function parentDepartmentName(parentId) {
    return parentId ? departmentNameMap.value.get(parentId) || '-' : '顶级部门'
  }

  async function loadFormOptions(force = false) {
    if (!token.value || !canAccessPage.value) return
    if (
      !force &&
      resourceKey === 'users' &&
      departmentOptions.value.length > 0 &&
      roleOptions.value.length > 0 &&
      positionOptions.value.length > 0
    ) return
    if (!force && resourceKey === 'departments' && departmentOptions.value.length > 0) return
    if (!force && resourceKey === 'roles' && permissionOptions.value.length > 0) return
    try {
      if (resourceKey === 'users') {
        const [departments, roles, positions] = await Promise.all([
          api.admin.departments.list(token.value, { includeDisabled: true }),
          api.admin.roles.list(token.value),
          api.admin.positions.list(token.value, { includeDisabled: true }),
        ])
        departmentOptions.value = departments
        roleOptions.value = roles
        positionOptions.value = positions
        return
      }
      if (resourceKey === 'departments') {
        departmentOptions.value = await api.admin.departments.list(token.value, { includeDisabled: true })
      }
      if (resourceKey === 'roles') {
        permissionOptions.value = await api.admin.permissions.list(token.value, { includeDisabled: true, limit: 500 })
      }
    } catch (err) {
      message.value = err.message || '加载部门或角色失败'
    }
  }

  async function refreshUserDepartmentTree() {
    departmentOptions.value = []
    await loadFormOptions(true)
    filterDepartmentTree()
  }

  return {
    loadFormOptions,
    parentDepartmentName,
    refreshUserDepartmentTree,
  }
}
