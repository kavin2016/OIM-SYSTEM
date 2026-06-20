import { api } from '../../../api/request.js'
import { token } from '../../../composables/useAuth.js'

function normalizeComparable(value) {
  return value === undefined || value === null ? '' : String(value).trim().toLowerCase()
}

function normalizeResultRows(result) {
  if (!result) return []
  return Array.isArray(result) ? result : [result]
}

export function createQueryActions(ctx) {
  const {
    apiKey,
    canOperate,
    closeRelationPanel,
    config,
    departmentFilterText,
    departmentOrgTreeRef,
    includeDeleted,
    loading,
    message,
    queryAdvancedVisible,
    queryForm,
    resourceKey,
    rows,
    selectedRowIds,
  } = ctx

  function buildListOptions() {
    if (resourceKey !== 'users') {
      const options = {
        includeDisabled: true,
        includeDeleted: queryForm.deletedStatus !== 'active',
        name: queryForm.name.trim(),
        code: queryForm.code.trim(),
      }
        if ((resourceKey === 'positions' || resourceKey === 'domains') && queryForm.status !== '') {
          options.status = queryForm.status === 'active' ? 0 : 1
        } else if (queryForm.status !== '') {
          options.is_active = queryForm.status === 'active'
        }
      return options
    }

    const options = {
      includeDisabled: true,
      includeDeleted: includeDeleted.value,
      nickname: queryForm.nickname.trim(),
      username: queryForm.username.trim(),
      department_id: queryForm.departmentId,
      role_id: queryForm.roleId,
      created_at_start: queryForm.createdAtStart,
      created_at_end: queryForm.createdAtEnd,
    }
    if (queryForm.status !== '') {
      options.is_active = queryForm.status === 'active'
    }
    return options
  }

  async function loadRows() {
    if (!token.value) {
      message.value = '未登录，无法加载数据。'
      return
    }
    if (!canOperate('query')) {
      rows.value = []
      message.value = `当前用户无权查询${config.entityName}。`
      return
    }
    loading.value = true
    message.value = ''
    try {
      const nextRows = await api.admin[apiKey].list(token.value, buildListOptions())
      const listRows = Array.isArray(nextRows) ? nextRows : []
      rows.value =
        resourceKey !== 'users' && queryForm.deletedStatus === 'deleted'
          ? listRows.filter((row) => row.is_deleted)
          : listRows
      selectedRowIds.value = []
      closeRelationPanel()
    } catch (err) {
      message.value = err.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  function valueIncludes(rowValue, queryValue) {
    const normalizedQuery = normalizeComparable(queryValue)
    if (!normalizedQuery) return true
    return normalizeComparable(rowValue).includes(normalizedQuery)
  }

  function idListIncludes(rowValue, queryValue) {
    if (queryValue === '' || queryValue === null || queryValue === undefined) return true
    const queryId = Number(queryValue)
    if (!Number.isInteger(queryId)) return false
    const values = Array.isArray(rowValue) ? rowValue : []
    return values.map((value) => Number(value)).includes(queryId)
  }

  function rowMatchesCurrentQuery(row) {
    if (resourceKey === 'users') {
      if (!includeDeleted.value && row.is_deleted) return false
      if (!valueIncludes(row.username, queryForm.username)) return false
      if (!valueIncludes(row.nickname, queryForm.nickname)) return false
      if (queryForm.status === 'active' && row.is_active !== true) return false
      if (queryForm.status === 'inactive' && row.is_active !== false) return false
      if (!idListIncludes(row.department_ids, queryForm.departmentId)) return false
      if (!idListIncludes(row.role_ids, queryForm.roleId)) return false
      if (queryForm.createdAtStart && (!row.created_at || row.created_at < queryForm.createdAtStart)) return false
      if (queryForm.createdAtEnd && (!row.created_at || row.created_at > queryForm.createdAtEnd)) return false
      return true
    }

    if (queryForm.deletedStatus === 'active' && row.is_deleted) return false
    if (queryForm.deletedStatus === 'deleted' && !row.is_deleted) return false
    if (queryForm.deletedStatus !== 'deleted' && queryForm.deletedStatus !== '' && row.is_deleted) return false
    if (!valueIncludes(row.name, queryForm.name)) return false
    if (!valueIncludes(row.code, queryForm.code)) return false
    if (queryForm.status === '') return true
    if (resourceKey === 'positions' || resourceKey === 'domains') {
      return Number(row.status) === (queryForm.status === 'active' ? 0 : 1)
    }
    return row.is_active === (queryForm.status === 'active')
  }

  function upsertRows(result, { prepend = false } = {}) {
    const incomingRows = normalizeResultRows(result)
    if (incomingRows.length === 0) return
    const nextRows = [...rows.value]
    incomingRows.forEach((row) => {
      const index = nextRows.findIndex((item) => item.id === row.id)
      const shouldShow = rowMatchesCurrentQuery(row)
      if (index >= 0) {
        if (shouldShow) {
          nextRows.splice(index, 1, row)
        } else {
          nextRows.splice(index, 1)
        }
        return
      }
      if (shouldShow) {
        if (prepend) {
          nextRows.unshift(row)
        } else {
          nextRows.push(row)
        }
      }
    })
    rows.value = nextRows
  }

  function removeRows(result) {
    const ids = new Set(normalizeResultRows(result).map((row) => row.id).filter(Boolean))
    if (ids.size === 0) return
    rows.value = rows.value.filter((row) => !ids.has(row.id))
    selectedRowIds.value = selectedRowIds.value.filter((id) => !ids.has(id))
  }

  async function resetQuery() {
    Object.assign(queryForm, {
      name: '',
      code: '',
      nickname: '',
      username: '',
      status: '',
      deletedStatus: '',
      departmentId: '',
      roleId: '',
      createdAtStart: '',
      createdAtEnd: '',
    })
    includeDeleted.value = false
    queryAdvancedVisible.value = false
    await loadRows()
  }

  function toggleQueryAdvanced() {
    queryAdvancedVisible.value = !queryAdvancedVisible.value
  }

  function filterDepartmentNode(keyword, data) {
    if (!keyword) return true
    return String(data?.label || '').toLowerCase().includes(String(keyword).trim().toLowerCase())
  }

  function filterDepartmentTree() {
    departmentOrgTreeRef.value?.filter?.(departmentFilterText.value)
  }

  async function handleDepartmentNodeClick(data) {
    queryForm.departmentId = data?.value || ''
    await loadRows()
  }

  async function clearDepartmentSelection() {
    departmentFilterText.value = ''
    queryForm.departmentId = ''
    departmentOrgTreeRef.value?.setCurrentKey?.(null)
    departmentOrgTreeRef.value?.filter?.('')
    await loadRows()
  }

  function openDateTimePicker(event) {
    const input = event?.currentTarget
    if (typeof input?.showPicker !== 'function') return
    try {
      input.showPicker()
    } catch {
      // Some browsers only allow showPicker during trusted click/focus events.
    }
  }

  return {
    buildListOptions,
    clearDepartmentSelection,
    filterDepartmentNode,
    filterDepartmentTree,
    handleDepartmentNodeClick,
    loadRows,
    openDateTimePicker,
    removeRows,
    resetQuery,
    toggleQueryAdvanced,
    upsertRows,
  }
}
