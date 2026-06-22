import '../../../styles/components/resource-page.css'
import 'element-plus/theme-chalk/el-message.css'
import './OperationLogManagement.css'
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { token, hasPermission } from '../../../composables/useAuth.js'
import { operationLogAPI } from '../../../api/operationLog.js'
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

const moduleOptions = [
  { value: '', label: '全部模块' },
  { value: 'system', label: '系统管理' },
  { value: 'ops', label: '运维管理' },
  { value: 'attendance', label: '考勤管理' },
]

const actionOptions = [
  { value: '', label: '全部动作' },
  { value: 'create', label: '新增' },
  { value: 'update', label: '修改' },
  { value: 'delete', label: '删除' },
  { value: 'login', label: '登录' },
  { value: 'export', label: '导出' },
  { value: 'enable', label: '启用' },
  { value: 'disable', label: '禁用' },
  { value: 'assign-role', label: '分配角色' },
  { value: 'assign-server', label: '分配服务器' },
  { value: 'reset-password', label: '重置密码' },
  { value: 'issue', label: '签发' },
  { value: 'renew', label: '续期' },
  { value: 'revoke', label: '吊销' },
  { value: 'kick', label: '强制下线' },
  { value: 'download-config', label: '下载配置' },
  { value: 'process', label: '处理' },
  { value: 'set-default', label: '设为默认' },
  { value: 'test', label: '测试' },
]

const resourceTypeFallbackOptions = [
  { value: '', label: '全部资源' },
  { value: 'auth', label: '认证' },
  { value: 'user', label: '用户' },
  { value: 'role', label: '角色' },
  { value: 'permission', label: '权限' },
  { value: 'department', label: '部门' },
  { value: 'position', label: '岗位' },
  { value: 'domain', label: '域名' },
  { value: 'operation_log', label: '操作日志' },
  { value: 'openvpn_server', label: 'OpenVPN服务器' },
  { value: 'openvpn_account', label: 'OpenVPN账号' },
  { value: 'openvpn_certificate', label: 'OpenVPN证书' },
  { value: 'openvpn_session', label: 'OpenVPN会话' },
  { value: 'openvpn_log', label: 'OpenVPN连接日志' },
  { value: 'openvpn_rule', label: 'OpenVPN分配策略' },
  { value: 'openvpn_traffic_threshold', label: 'OpenVPN流量阈值' },
  { value: 'openvpn_traffic_alert', label: 'OpenVPN流量告警' },
]

const resultOptions = [
  { value: '', label: '全部结果' },
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
]

function emptyFilters() {
  return {
    operator_username: '',
    department_name: '',
    module: '',
    resource_type: '',
    action: '',
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
    const dynamicModuleOptions = ref(moduleOptions)
    const dynamicResourceTypeOptions = ref(resourceTypeFallbackOptions)
    const dynamicActionOptions = ref(actionOptions)
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
        const rows = await operationLogAPI.list(token.value, {
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
        ElMessage.error(error.message || '操作日志加载失败')
      } finally {
        if (seq === loadSeq) loading.value = false
      }
    }

    async function loadOptions() {
      try {
        const options = await operationLogAPI.options(token.value)
        dynamicModuleOptions.value = withAllOption('全部模块', options.modules || [])
        dynamicResourceTypeOptions.value = withAllOption('全部资源', options.resource_types || [])
        dynamicActionOptions.value = withAllOption('全部动作', options.actions || [])
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
        detail.value = await operationLogAPI.get(token.value, row.id)
      } catch (error) {
        ElMessage.error(error.message || '操作日志详情加载失败')
      } finally {
        detailLoading.value = false
      }
    }

    async function exportLogs() {
      try {
        const result = await operationLogAPI.export(token.value, filterParams(filters))
        downloadOpenVpnTextFile(result.filename, result.content, 'text/csv;charset=utf-8')
        ElMessage.success('操作日志已导出')
      } catch (error) {
        ElMessage.error(error.message || '操作日志导出失败')
      }
    }

    function resultText(value) {
      return value === 'success' ? '成功' : '失败'
    }

    function detailResourceText(row) {
      if (!row) return '-'
      return row.resource_name || row.resource_type || '-'
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
      if (visible) {
        lockPageScroll()
      } else {
        unlockPageScroll()
      }
    })

    onBeforeUnmount(unlockPageScroll)

    return {
      actionIconMap,
      applyTimeRange,
      can,
      changePage,
      changePageSize,
      detail,
      detailLoading,
      detailVisible,
      detailResourceText,
      dynamicActionOptions,
      dynamicModuleOptions,
      dynamicResourceTypeOptions,
      dynamicResultOptions,
      exportLogs,
      filters,
      formatDate,
      formatJson,
      loading,
      logs,
      openDetail,
      openVpnPageEnd,
      openVpnPageSizeOptions,
      openVpnPageStart,
      openVpnPaginationTotal,
      pagination,
      resetFilters,
      resultText,
      copyText,
      methodClass,
      searchLogs,
    }
  },
}
