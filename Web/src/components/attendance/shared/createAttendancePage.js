import '../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { attendanceAPI } from '../../../api/attendance.js'
import { hasPermission, token, user } from '../../../composables/useAuth.js'
import { formatDate } from '../../system/resourcePageUtils.js'
import { ATTENDANCE_CONFIG } from '../config/attendancePageConfig.js'

function normalizeValue(value) {
  if (value === '') return null
  return value
}

function defaultPayload(form, fields = []) {
  return fields.reduce((payload, [key, , type]) => {
    if (key.endsWith('_text')) return payload
    const value = form[key]
    if (type === 'number') {
      payload[key] = value === '' || value === null ? null : Number(value)
    } else {
      payload[key] = normalizeValue(value)
    }
    return payload
  }, {})
}

function normalizeComparable(value) {
  return value === undefined || value === null ? '' : String(value)
}

export function createAttendancePage(pageKey) {
  return {
    setup() {
      const config = ATTENDANCE_CONFIG[pageKey]
      const rows = ref([])
      const loading = ref(false)
      const saving = ref(false)
      const message = ref('')
      const formVisible = ref(false)
      const editingId = ref(null)
      const approvalRemark = ref('')
      const rebuildForm = reactive({
        work_date: new Date().toISOString().slice(0, 10),
        year: new Date().getFullYear(),
        month: new Date().getMonth() + 1,
        user_id: '',
        department_id: '',
      })
      const queryForm = reactive({
        user_id: '',
        department_id: '',
        start_date: '',
        end_date: '',
        start_at: '',
        end_at: '',
        record_type: '',
        request_type: '',
        request_status: '',
        year: '',
        month: '',
        name: '',
      })
      const form = reactive(config.empty ? config.empty() : {})

      const canAccessPage = computed(() => user.value?.is_admin === true || hasPermission(config.listPermission))
      const canCreate = computed(() => !config.readOnly && (user.value?.is_admin === true || hasPermission(config.createPermission || config.writePermission)))
      const canUpdate = computed(() => !config.readOnly && (user.value?.is_admin === true || hasPermission(config.updatePermission || config.writePermission)))
      const canDelete = computed(() => !config.readOnly && (user.value?.is_admin === true || hasPermission(config.deletePermission || config.writePermission)))
      const canApprove = computed(() => user.value?.is_admin === true || hasPermission(config.approvePermission))
      const isEditing = computed(() => editingId.value !== null)
      const visibleFields = computed(() =>
        (config.fields || []).filter((field) => {
          const mode = field[4]
          if (mode === 'createOnly') return !isEditing.value
          if (mode === 'editOnly') return isEditing.value
          return true
        }),
      )

      function formatCell(row, column) {
        const [key, , type] = column
        const value = row[key]
        if (type === 'datetime') return formatDate(value)
        if (type === 'boolean') return value ? '是' : '否'
        return value ?? '-'
      }

      function buildListQuery() {
        const query = { ...(config.defaultQuery || {}) }
        Object.entries(queryForm).forEach(([key, value]) => {
          if (value !== '') query[key] = value
        })
        return query
      }

      function rowDateValue(row) {
        return row.work_date || row.record_time || row.start_at || row.created_at || ''
      }

      function rowMatchesQuery(row) {
        const query = buildListQuery()
        return Object.entries(query).every(([key, value]) => {
          if (value === '' || value === undefined || value === null) return true
          if (key === 'request_status') return row.status === value
          if (key === 'start_date') return !rowDateValue(row) || rowDateValue(row).slice(0, 10) >= value
          if (key === 'end_date') return !rowDateValue(row) || rowDateValue(row).slice(0, 10) <= value
          if (key === 'start_at') return !row.record_time || row.record_time >= value
          if (key === 'end_at') return !row.record_time || row.record_time <= value
          if (key === 'name') return normalizeComparable(row.name).includes(String(value).trim())
          return normalizeComparable(row[key]) === normalizeComparable(value)
        })
      }

      function normalizeResultRows(result) {
        if (!result) return []
        return Array.isArray(result) ? result : [result]
      }

      function upsertRows(result, { prepend = false } = {}) {
        const incomingRows = normalizeResultRows(result)
        if (incomingRows.length === 0) return
        const nextRows = [...rows.value]
        incomingRows.forEach((row) => {
          const index = nextRows.findIndex((item) => item.id === row.id)
          const shouldShow = rowMatchesQuery(row)
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
      }

      function queryInputType(field) {
        return field[2] || 'text'
      }

      function isFieldRequired(field) {
        if (field[4] === 'createOnly' && isEditing.value) return false
        if (field[4] === 'editOnly' && !isEditing.value) return false
        return field[3] === true
      }

      function canWithdrawRow(row) {
        return config.apiKey === 'requests' && row.status === 'pending' && row.user_id === user.value?.id
      }

      async function loadRows() {
        if (!canAccessPage.value) return
        loading.value = true
        message.value = ''
        try {
          rows.value = await attendanceAPI[config.apiKey].list(token.value, buildListQuery())
        } catch (error) {
          message.value = error.message || '加载失败'
        } finally {
          loading.value = false
        }
      }

      function resetQuery() {
        Object.keys(queryForm).forEach((key) => {
          queryForm[key] = ''
        })
        loadRows()
      }

      function startCreate() {
        editingId.value = null
        Object.assign(form, config.empty ? config.empty() : {})
        formVisible.value = true
      }

      function editRow(row) {
        editingId.value = row.id
        Object.assign(form, config.empty ? config.empty() : {})
        if (config.fillForm) {
          config.fillForm(form, row)
        } else {
          Object.assign(form, row)
        }
        formVisible.value = true
      }

      function cancelForm() {
        formVisible.value = false
        editingId.value = null
      }

      function payloadFromForm() {
        return config.toPayload ? config.toPayload(form, isEditing.value) : defaultPayload(form, config.fields)
      }

      async function saveCurrent() {
        saving.value = true
        message.value = ''
        try {
          const payload = payloadFromForm()
          let result
          if (isEditing.value) {
            result = await attendanceAPI[config.apiKey].update(token.value, editingId.value, payload)
            upsertRows(result)
          } else {
            result = await attendanceAPI[config.apiKey].create(token.value, payload)
            upsertRows(result, { prepend: true })
          }
          formVisible.value = false
          message.value = '保存成功'
        } catch (error) {
          message.value = error.message || '保存失败'
        } finally {
          saving.value = false
        }
      }

      async function deleteRow(row) {
        if (!window.confirm(`确认删除 ID ${row.id}？`)) return
        saving.value = true
        try {
          const result = await attendanceAPI[config.apiKey].delete(token.value, row.id)
          removeRows(result || row)
          message.value = '删除成功'
        } catch (error) {
          message.value = error.message || '删除失败'
        } finally {
          saving.value = false
        }
      }

      async function approveRow(row, status) {
        saving.value = true
        try {
          const result = await attendanceAPI.approveRequest(token.value, row.id, {
            status,
            approval_remark: approvalRemark.value || null,
          })
          approvalRemark.value = ''
          upsertRows(result)
          message.value = status === 'approved' ? '已通过' : '已驳回'
        } catch (error) {
          message.value = error.message || '审批失败'
        } finally {
          saving.value = false
        }
      }

      async function withdrawRow(row) {
        if (!window.confirm(`确认撤回申请 ${row.request_no || row.id}？`)) return
        saving.value = true
        try {
          const result = await attendanceAPI.withdrawRequest(token.value, row.id)
          upsertRows(result)
          message.value = '已撤回'
        } catch (error) {
          message.value = error.message || '撤回失败'
        } finally {
          saving.value = false
        }
      }

      async function rebuildReport() {
        saving.value = true
        try {
          if (config.rebuild === 'daily') {
            const result = await attendanceAPI.rebuildDaily(token.value, {
              work_date: rebuildForm.work_date,
              user_id: rebuildForm.user_id || undefined,
              department_id: rebuildForm.department_id || undefined,
            })
            upsertRows(result)
          } else if (config.rebuild === 'monthly') {
            const result = await attendanceAPI.rebuildMonthly(token.value, {
              year: rebuildForm.year,
              month: rebuildForm.month,
              user_id: rebuildForm.user_id || undefined,
              department_id: rebuildForm.department_id || undefined,
            })
            upsertRows(result)
          }
          message.value = '重算完成'
        } catch (error) {
          message.value = error.message || '重算失败'
        } finally {
          saving.value = false
        }
      }

      async function exportReport() {
        saving.value = true
        try {
          const type = config.rebuild === 'monthly' ? 'monthly' : 'daily'
          const blob = await attendanceAPI.exportReport(token.value, type, buildListQuery())
          const url = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.download = type === 'monthly' ? 'attendance_monthly_report.csv' : 'attendance_daily_report.csv'
          document.body.appendChild(link)
          link.click()
          link.remove()
          URL.revokeObjectURL(url)
        } catch (error) {
          message.value = error.message || '导出失败'
        } finally {
          saving.value = false
        }
      }

      onMounted(loadRows)

      return {
        approvalRemark,
        canAccessPage,
        canApprove,
        canCreate,
        canDelete,
        canWithdrawRow,
        canUpdate,
        columns: config.columns,
        config,
        fields: config.fields || [],
        form,
        formVisible,
        formatCell,
        isFieldRequired,
        isEditing,
        loading,
        message,
        queryForm,
        queryInputType,
        queryFields: config.queryFields || [],
        rebuildForm,
        rows,
        saving,
        title: config.title,
        approveRow,
        cancelForm,
        deleteRow,
        editRow,
        exportReport,
        loadRows,
        rebuildReport,
        resetQuery,
        saveCurrent,
        startCreate,
        visibleFields,
        withdrawRow,
      }
    },
  }
}
