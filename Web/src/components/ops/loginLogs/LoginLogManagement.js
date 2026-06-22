import '../../../styles/components/resource-page.css'
import 'element-plus/theme-chalk/el-message.css'
import '../operationLogs/OperationLogManagement.css'
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { token, hasPermission } from '../../../composables/useAuth.js'
import { loginLogAPI } from '../../../api/loginLog.js'
import { actionIconMap } from '../../system/resourcePageConstants.js'
import {
  downloadOpenVpnTextFile,
  emptyOpenVpnPagination,
  formatOpenVpnDate,
  openVpnPageEnd,
  openVpnPageSizeOptions,
  openVpnPageStart,
  openVpnPaginationTotal,
  resetOpenVpnPagination,
  sliceOpenVpnPageRows,
} from '../openvpn/shared/openVpnConfig.js'

const loginTypeOptions = [
  { value: '', label: '全部方式' },
  { value: 'password', label: '账号密码' },
]

const resultOptions = [
  { value: '', label: '全部结果' },
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
]

function emptyFilters() {
  return {
    username: '',
    department_name: '',
    login_type: '',
    result: '',
    client_ip: '',
    keyword: '',
    created_at_start: '',
    created_at_end: '',
  }
}

function filterParams(filters) {
  const params = { ...filters }
  if (params.created_at_start) params.created_at_start = new Date(params.created_at_start).toISOString()
  if (params.created_at_end) params.created_at_end = new Date(params.created_at_end).toISOString()
  return params
}

function withAllOption(label, rows = []) {
  return [{ value: '', label }, ...rows.filter((item) => item.value)]
}

function formatDateTimeInput(date) {
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0)
}

function endOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59)
}

function formatJson(value) {
  if (!value) return '-'
  return JSON.stringify(value, null, 2)
}

function methodClass(value) {
  return String(value || '').toLowerCase()
}

export default {
  setup() {
    const loading = ref(false)
    const detailLoading = ref(false)
    const logs = ref([])
    const detail = ref(null)
    const detailVisible = ref(false)
    const filters = reactive(emptyFilters())
    const pagination = reactive(emptyOpenVpnPagination())
    const pageCursors = reactive({ 1: null })
    const dynamicLoginTypeOptions = ref(loginTypeOptions)
    const dynamicResultOptions = ref(resultOptions)
    let loadSeq = 0
    let lockedScrollY = 0
    let pageScrollLocked = false
    const can = (permission) => hasPermission(permission)
    const formatDate = formatOpenVpnDate

    function lockPageScroll() {
      if (typeof window === 'undefined' || pageScrollLocked) return
      lockedScrollY = window.scrollY || document.documentElement.scrollTop || 0
      pageScrollLocked = true
      document.body.style.position = 'fixed'
      document.body.style.top = `-${lockedScrollY}px`
      document.body.style.left = '0'
      document.body.style.right = '0'
      document.body.style.width = '100%'
      document.body.style.overflow = 'hidden'
    }

    function unlockPageScroll() {
      if (typeof window === 'undefined' || !pageScrollLocked) return
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.left = ''
      document.body.style.right = ''
      document.body.style.width = ''
      document.body.style.overflow = ''
      pageScrollLocked = false
      window.scrollTo(0, lockedScrollY)
    }

    async function loadLogs() {
      const seq = ++loadSeq
      loading.value = true
      try {
        const cursorId = pageCursors[pagination.page] || null
        const rows = await loginLogAPI.list(token.value, {
          ...filterParams(filters),
          limit: pagination.pageSize + 1,
          cursor_id: cursorId,
        })
        if (seq !== loadSeq) return
        logs.value = sliceOpenVpnPageRows(rows, pagination)
        if (pagination.hasNext && logs.value.length > 0) {
          pageCursors[pagination.page + 1] = logs.value[logs.value.length - 1].id
        }
      } catch (error) {
        ElMessage.error(error.message || '登录日志加载失败')
      } finally {
        if (seq === loadSeq) loading.value = false
      }
    }

    async function loadOptions() {
      try {
        const options = await loginLogAPI.options(token.value)
        dynamicLoginTypeOptions.value = withAllOption('全部方式', options.login_types || [])
        dynamicResultOptions.value = withAllOption('全部结果', options.results || [])
      } catch (error) {
        ElMessage.error(error.message || '查询选项加载失败')
      }
    }

    function resetPagination() {
      resetOpenVpnPagination(pagination)
      Object.keys(pageCursors).forEach((key) => delete pageCursors[key])
      pageCursors[1] = null
    }

    function searchLogs() {
      resetPagination()
      loadLogs()
    }

    function resetFilters() {
      Object.assign(filters, emptyFilters())
      searchLogs()
    }

    function changePageSize() {
      resetPagination()
      loadLogs()
    }

    function changePage(page) {
      if (page > 1 && !(page in pageCursors)) return
      pagination.page = page
      loadLogs()
    }

    async function openDetail(row) {
      detailLoading.value = true
      detailVisible.value = true
      try {
        detail.value = await loginLogAPI.get(token.value, row.id)
      } catch (error) {
        ElMessage.error(error.message || '登录日志详情加载失败')
      } finally {
        detailLoading.value = false
      }
    }

    async function exportLogs() {
      try {
        const result = await loginLogAPI.export(token.value, filterParams(filters))
        downloadOpenVpnTextFile(result.filename, result.content, 'text/csv;charset=utf-8')
        ElMessage.success('登录日志已导出')
      } catch (error) {
        ElMessage.error(error.message || '登录日志导出失败')
      }
    }

    function resultText(value) {
      return value === 'success' ? '成功' : '失败'
    }

    function loginTypeText(value) {
      return dynamicLoginTypeOptions.value.find((item) => item.value === value)?.label || value || '-'
    }

    async function copyText(value, label) {
      try {
        await navigator.clipboard.writeText(value || '')
        ElMessage.success(`${label}已复制`)
      } catch (error) {
        ElMessage.error('复制失败')
      }
    }

    function applyTimeRange(type) {
      const now = new Date()
      let start = startOfDay(now)
      if (type === '7d') {
        start = startOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6))
      } else if (type === '30d') {
        start = startOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 29))
      }
      filters.created_at_start = formatDateTimeInput(start)
      filters.created_at_end = formatDateTimeInput(endOfDay(now))
      searchLogs()
    }

    onMounted(async () => {
      await loadOptions()
      await loadLogs()
    })

    watch(detailVisible, (visible) => {
      if (visible) lockPageScroll()
      else unlockPageScroll()
    })

    onBeforeUnmount(unlockPageScroll)

    return {
      actionIconMap,
      applyTimeRange,
      can,
      changePage,
      changePageSize,
      copyText,
      detail,
      detailLoading,
      detailVisible,
      dynamicLoginTypeOptions,
      dynamicResultOptions,
      exportLogs,
      filters,
      formatDate,
      formatJson,
      loading,
      logs,
      loginTypeText,
      methodClass,
      openDetail,
      openVpnPageEnd,
      openVpnPageSizeOptions,
      openVpnPageStart,
      openVpnPaginationTotal,
      pagination,
      resetFilters,
      resultText,
      searchLogs,
    }
  },
}
