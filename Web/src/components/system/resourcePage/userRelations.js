import { api } from '../../../api/request.js'
import { hasPermission, token } from '../../../composables/useAuth.js'
import { normalizeIdList } from '../resourcePageUtils.js'

export function createUserRelationActions(ctx, deps) {
  const {
    canOperate,
    message,
    passwordLayer,
    relationLoading,
    relationPanel,
    roleLayer,
    saving,
  } = ctx
  const { loadFormOptions } = deps

  function closePasswordLayer() {
    Object.assign(passwordLayer, {
      visible: false,
      userId: null,
      username: '',
      password: '',
      confirmPassword: '',
    })
  }

  function closeRoleLayer() {
    Object.assign(roleLayer, {
      visible: false,
      userId: null,
      username: '',
      roleIds: [],
    })
  }

  function closeRelationPanel() {
    relationPanel.visible = false
    relationPanel.title = ''
    relationPanel.type = ''
    relationPanel.rows = []
  }

  function showResetPassword(row) {
    if (row.username === 'admin') {
      message.value = 'admin 用户不能重置密码。'
      return
    }
    if (!hasPermission('system:user:reset-password')) {
      message.value = '当前用户无权重置密码。'
      return
    }
    Object.assign(passwordLayer, {
      visible: true,
      userId: row.id,
      username: row.username || '',
      password: '',
      confirmPassword: '',
    })
  }

  async function showAssignRoles(row) {
    if (row.username === 'admin') {
      message.value = 'admin 用户不能分配角色。'
      return
    }
    if (!token.value || !hasPermission('system:user:assign-role')) {
      message.value = '当前用户无权分配角色。'
      return
    }
    relationLoading.value = true
    message.value = ''
    try {
      await loadFormOptions()
      const userRoles = await api.admin.listUserRoles(token.value, row.id)
      Object.assign(roleLayer, {
        visible: true,
        userId: row.id,
        username: row.username || '',
        roleIds: userRoles.map((role) => role.id),
      })
    } catch (err) {
      message.value = err.message || '加载用户角色失败'
    } finally {
      relationLoading.value = false
    }
  }

  async function submitResetPassword() {
    if (!hasPermission('system:user:reset-password')) {
      message.value = '当前用户无权重置密码。'
      return
    }
    if (!passwordLayer.password) {
      message.value = '请输入新密码。'
      return
    }
    if (passwordLayer.password !== passwordLayer.confirmPassword) {
      message.value = '两次输入的密码不一致。'
      return
    }
    saving.value = true
    message.value = ''
    try {
      await api.admin.resetUserPassword(token.value, passwordLayer.userId, passwordLayer.password)
      closePasswordLayer()
      message.value = '密码已重置'
    } catch (err) {
      message.value = err.message || '重置密码失败'
    } finally {
      saving.value = false
    }
  }

  async function submitAssignRoles() {
    if (!hasPermission('system:user:assign-role')) {
      message.value = '当前用户无权分配角色。'
      return
    }
    saving.value = true
    message.value = ''
    try {
      await api.admin.assignUserRoles(token.value, roleLayer.userId, normalizeIdList(roleLayer.roleIds))
      closeRoleLayer()
      message.value = '角色已分配'
    } catch (err) {
      message.value = err.message || '分配角色失败'
    } finally {
      saving.value = false
    }
  }

  async function showUserDepartments(row) {
    if (!token.value || !canOperate('query')) {
      message.value = '当前用户无权查询用户部门。'
      return
    }
    relationLoading.value = true
    message.value = ''
    try {
      relationPanel.rows = await api.admin.listUserDepartments(token.value, row.id)
      relationPanel.title = `${row.username} 的部门信息`
      relationPanel.type = 'departments'
      relationPanel.visible = true
    } catch (err) {
      message.value = err.message || '查询用户部门失败'
    } finally {
      relationLoading.value = false
    }
  }

  async function showRolePermissions(row) {
    if (!token.value || !canOperate('query')) {
      message.value = '当前用户无权查询角色权限。'
      return
    }
    relationLoading.value = true
    message.value = ''
    try {
      relationPanel.rows = await api.admin.listRolePermissions(token.value, row.id)
      relationPanel.title = `${row.name} 的权限信息`
      relationPanel.type = 'permissions'
      relationPanel.visible = true
    } catch (err) {
      message.value = err.message || '查询角色权限失败'
    } finally {
      relationLoading.value = false
    }
  }

  return {
    closePasswordLayer,
    closeRelationPanel,
    closeRoleLayer,
    showAssignRoles,
    showRolePermissions,
    showResetPassword,
    showUserDepartments,
    submitAssignRoles,
    submitResetPassword,
  }
}
