import { api } from '../../../api/request.js'
import { token } from '../../../composables/useAuth.js'

export function createSelectionActions(ctx, deps) {
  const {
    apiKey,
    canOperate,
    config,
    departmentOptions,
    editingId,
    message,
    resourceKey,
    saving,
    selectableRows,
    selectedRowIds,
    selectedRows,
  } = ctx
  const { cancelForm, loadFormOptions, upsertRows } = deps

  function editSelectedRow() {
    if (selectedRows.value.length !== 1) {
      message.value = '请选择一条需要修改的用户。'
      return
    }
    deps.editRow(selectedRows.value[0])
  }

  function toggleRowSelection(row) {
    if (row.is_deleted) return
    if (resourceKey === 'users' && row.username === 'admin') return
    if (selectedRowIds.value.includes(row.id)) {
      selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
      return
    }
    selectedRowIds.value = [...selectedRowIds.value, row.id]
  }

  function toggleAllRows() {
    if (selectableRows.value.length > 0 && selectedRows.value.length === selectableRows.value.length) {
      selectedRowIds.value = []
      return
    }
    selectedRowIds.value = selectableRows.value.map((row) => row.id)
  }

  async function deleteRow(row) {
    if (!token.value) {
      message.value = '未登录，无法删除数据。'
      return
    }
    if (!canOperate('delete')) {
      message.value = `当前用户无权删除${config.entityName}。`
      return
    }
    if (resourceKey === 'users' && row.username === 'admin') {
      message.value = '内置 admin 用户不能删除。'
      return
    }
    const targetName = row.username || row.name || row.code
    const confirmed = window.confirm(`确认删除「${targetName}」？\n删除后数据会被标记为已删除，请确认该操作。`)
    if (!confirmed) return
    try {
      const result = await api.admin[apiKey].delete(token.value, row.id)
      selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
      message.value = `${config.entityName}已逻辑删除`
      if (editingId.value === row.id) {
        cancelForm()
      }
      if (resourceKey === 'departments') {
        departmentOptions.value = []
      }
      upsertRows(result || { ...row, is_deleted: true })
      await loadFormOptions()
    } catch (err) {
      message.value = err.message || '删除失败'
    }
  }

  async function deleteSelectedRows() {
    if (!token.value) {
      message.value = '未登录，无法删除数据。'
      return
    }
    if (!canOperate('delete')) {
      message.value = '当前用户无权删除用户。'
      return
    }
    const targets = selectedRows.value
    if (targets.length === 0) {
      message.value = '请选择需要删除的用户。'
      return
    }
    if (targets.some((row) => row.username === 'admin')) {
      message.value = '选中数据包含内置 admin 用户，不能删除。'
      return
    }
    const confirmed = window.confirm(`确认删除选中的 ${targets.length} 个用户？\n删除后数据会被标记为已删除，请确认该操作。`)
    if (!confirmed) return
    saving.value = true
    message.value = ''
    try {
      const result = await api.admin[apiKey].batchDelete(token.value, targets.map((row) => row.id))
      selectedRowIds.value = []
      upsertRows(result || targets.map((row) => ({ ...row, is_deleted: true })))
      message.value = `已逻辑删除 ${targets.length} 个用户`
    } catch (err) {
      message.value = err.message || '批量删除失败'
    } finally {
      saving.value = false
    }
  }

  return {
    deleteRow,
    deleteSelectedRows,
    editSelectedRow,
    toggleAllRows,
    toggleRowSelection,
  }
}
