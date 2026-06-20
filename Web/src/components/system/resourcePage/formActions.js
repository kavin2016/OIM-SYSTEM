import { api } from '../../../api/request.js'
import { token } from '../../../composables/useAuth.js'

function normalizeOptionalId(value) {
  const id = Number(value)
  return Number.isInteger(id) && id > 0 ? id : null
}

export function createFormActions(ctx, deps) {
  const {
    apiKey,
    canOperate,
    config,
    departmentOptions,
    editingId,
    form,
    formVisible,
    message,
    originalParentId,
    relationLoading,
    resourceKey,
    rolePermissionCheckAll,
    rolePermissionExpanded,
    rolePermissionLinkParents,
    saving,
  } = ctx
  const { loadFormOptions, syncRolePermissionTree, upsertRows } = deps

  function enrichResultWithPayload(result, payload) {
    if (!result || Array.isArray(result)) return result
    if (resourceKey !== 'users') return result
    return {
      ...result,
      department_ids: payload.department_ids || [],
      role_ids: payload.role_ids || [],
      position_ids: payload.position_ids || [],
    }
  }

  function resetForm() {
    const nextForm = config.emptyForm()
    Object.keys(form).forEach((key) => {
      delete form[key]
    })
    Object.assign(form, nextForm)
    editingId.value = null
    originalParentId.value = null
    rolePermissionExpanded.value = true
    rolePermissionCheckAll.value = false
    rolePermissionLinkParents.value = true
  }

  async function startCreate() {
    if (!canOperate('create')) {
      message.value = `当前用户无权新增${config.entityName}。`
      return
    }
    resetForm()
    await loadFormOptions(resourceKey === 'users' || resourceKey === 'departments' || resourceKey === 'roles')
    formVisible.value = true
    if (resourceKey === 'roles') {
      await syncRolePermissionTree()
    }
  }

  function cancelForm() {
    resetForm()
    formVisible.value = false
  }

  async function saveCurrent() {
    if (!token.value) {
      message.value = '未登录，无法保存数据。'
      return
    }
    if (!canOperate(editingId.value !== null ? 'update' : 'create')) {
      message.value = `当前用户无权${editingId.value !== null ? '修改' : '新增'}${config.entityName}。`
      return
    }
    saving.value = true
    message.value = ''
    try {
      const payload = config.toPayload(form, editingId.value !== null)
      if (resourceKey === 'departments' && editingId.value !== null) {
        const currentParentId = normalizeOptionalId(form.parent_id)
        if (currentParentId === originalParentId.value) {
          delete payload.parent_id
        }
      }
      let result
      if (editingId.value !== null) {
        result = await api.admin[apiKey].update(token.value, editingId.value, payload)
        upsertRows(enrichResultWithPayload(result, payload))
        message.value = `${config.entityName}已更新`
      } else {
        result = await api.admin[apiKey].create(token.value, payload)
        upsertRows(enrichResultWithPayload(result, payload), { prepend: true })
        message.value = `${config.entityName}已创建`
      }
      resetForm()
      formVisible.value = false
      if (resourceKey === 'departments') {
        departmentOptions.value = []
      }
      await loadFormOptions()
    } catch (err) {
      message.value = err.message || '保存失败'
    } finally {
      saving.value = false
    }
  }

  async function editRow(row) {
    if (!canOperate('update')) {
      message.value = `当前用户无权修改${config.entityName}。`
      return
    }
    if (resourceKey === 'users' && row.username === 'admin') {
      message.value = 'admin 用户不能修改。'
      return
    }
    resetForm()
    editingId.value = row.id
    await loadFormOptions(resourceKey === 'users' || resourceKey === 'departments' || resourceKey === 'roles')
    config.fillForm(form, row)
    if (resourceKey === 'users') {
      relationLoading.value = true
      try {
        const [userDepartments, userRoles, userPositions] = await Promise.all([
          api.admin.listUserDepartments(token.value, row.id),
          api.admin.listUserRoles(token.value, row.id),
          api.admin.listUserPositions(token.value, row.id),
        ])
        form.department_id = userDepartments[0]?.id || null
        form.role_id = userRoles[0]?.id || null
        form.position_ids = userPositions.map((position) => position.id)
      } catch (err) {
        message.value = err.message || '加载用户部门或角色失败'
      } finally {
        relationLoading.value = false
      }
    }
    if (resourceKey === 'departments') {
      originalParentId.value = normalizeOptionalId(row.parent_id)
    }
    if (resourceKey === 'roles') {
      relationLoading.value = true
      try {
        const rolePermissions = await api.admin.listRolePermissions(token.value, row.id)
        const hasCheckedField = rolePermissions.some((permission) =>
          Object.prototype.hasOwnProperty.call(permission, 'checked'),
        )
        form.permission_ids = rolePermissions
          .filter((permission) => (hasCheckedField ? permission.checked === true : true))
          .map((permission) => permission.id)
      } catch (err) {
        message.value = err.message || '加载角色权限失败'
      } finally {
        relationLoading.value = false
      }
    }
    formVisible.value = true
    if (resourceKey === 'roles') {
      await syncRolePermissionTree()
    }
  }

  return {
    cancelForm,
    editRow,
    resetForm,
    saveCurrent,
    startCreate,
  }
}
