import '../../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { token, hasPermission } from '../../../../composables/useAuth.js'
import { openvpnAPI } from '../../../../api/openvpn.js'
import { actionIconMap } from '../../../system/resourcePageConstants.js'
import {
  asOpenVpnArray,
  emptyOpenVpnPagination,
  formatOpenVpnDate,
  openVpnPageEnd,
  openVpnPageParams,
  openVpnPageSizeOptions,
  openVpnPageStart,
  openVpnPaginationTotal,
  openVpnStatusText,
  resetOpenVpnPagination,
  resetOpenVpnReactive,
  sliceOpenVpnPageRows,
} from '../shared/openVpnConfig.js'

export default {
  setup() {
    const loading = ref(false)
    const servers = ref([])
    const accounts = ref([])
    const sessions = ref([])
    const selectedRowIds = ref([])
    const sessionQuery = reactive({ server_id: '', user_id: '', status: 'online' })
    const pagination = reactive(emptyOpenVpnPagination())

    const selectedRows = computed(() => sessions.value.filter((row) => selectedRowIds.value.includes(row.id)))
    const selectedRow = computed(() => selectedRows.value[0] || null)
    const isAllRowsSelected = computed(
      () => sessions.value.length > 0 && selectedRows.value.length === sessions.value.length,
    )
    const can = (permission) => hasPermission(permission)
    const formatDate = formatOpenVpnDate
    const statusText = openVpnStatusText

    function serverName(id) {
      return servers.value.find((item) => item.id === id)?.name || '-'
    }

    function accountLabel(account) {
      return `${account.username || account.vpn_username || '-'}${account.nickname ? ` / ${account.nickname}` : ''}`
    }

    function formatBytes(value) {
      const bytes = Number(value) || 0
      if (bytes < 1024) return `${bytes} B`
      const units = ['KB', 'MB', 'GB', 'TB']
      let size = bytes / 1024
      let unitIndex = 0
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024
        unitIndex += 1
      }
      return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unitIndex]}`
    }

    function formatTraffic(row) {
      return `${formatBytes(row.bytes_in)} / ${formatBytes(row.bytes_out)}`
    }

    function formatDuration(row) {
      if (!row.connected_at) return '-'
      const endTime = row.disconnected_at ? new Date(row.disconnected_at).getTime() : Date.now()
      const startTime = new Date(row.connected_at).getTime()
      const totalSeconds = Math.max(0, Math.floor((endTime - startTime) / 1000))
      const hours = Math.floor(totalSeconds / 3600)
      const minutes = Math.floor((totalSeconds % 3600) / 60)
      const seconds = totalSeconds % 60
      if (hours > 0) return `${hours}小时${minutes}分`
      if (minutes > 0) return `${minutes}分${seconds}秒`
      return `${seconds}秒`
    }

    async function loadServers() {
      servers.value = asOpenVpnArray(await openvpnAPI.listServers(token.value, { include_disabled: true }))
    }

    async function loadAccounts() {
      accounts.value = asOpenVpnArray(await openvpnAPI.listAccounts(token.value, { limit: 1000 }))
    }

    async function loadSessions() {
      loading.value = true
      try {
        const rows = await openvpnAPI.listSessions(token.value, { ...sessionQuery, ...openVpnPageParams(pagination) })
        sessions.value = sliceOpenVpnPageRows(rows, pagination)
        selectedRowIds.value = selectedRowIds.value.filter((id) => sessions.value.some((row) => row.id === id))
      } finally {
        loading.value = false
      }
    }

    function resetQuery() {
      resetOpenVpnReactive(sessionQuery, { server_id: '', user_id: '', status: 'online' })
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadSessions()
    }

    function searchSessions() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadSessions()
    }

    function changePageSize() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadSessions()
    }

    function changePage(page) {
      pagination.page = page
      selectedRowIds.value = []
      loadSessions()
    }

    function toggleRowSelection(row) {
      if (selectedRowIds.value.includes(row.id)) {
        selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
        return
      }
      selectedRowIds.value = [...selectedRowIds.value, row.id]
    }

    function toggleAllRows() {
      selectedRowIds.value = isAllRowsSelected.value ? [] : sessions.value.map((row) => row.id)
    }

    function requireSingleSelection(actionName) {
      if (selectedRows.value.length !== 1) {
        ElMessage.warning(`请选择一条数据进行${actionName}`)
        return null
      }
      return selectedRow.value
    }

    async function kickSession(row) {
      if (row.status !== 'online') {
        ElMessage.warning('只有在线会话可以强制下线')
        return
      }
      try {
        await ElMessageBox.confirm(`确认强制下线 ${row.username || row.common_name} 的OpenVPN会话？`, '强制下线确认', {
          type: 'warning',
        })
        await openvpnAPI.kickSession(token.value, row.id)
        selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
        ElMessage.success('会话已下线')
        await loadSessions()
      } catch (error) {
        if (error !== 'cancel' && error !== 'close' && error?.action !== 'cancel' && error?.action !== 'close') {
          ElMessage.error(error.message || '会话下线失败')
        }
      }
    }

    async function kickSelectedSession() {
      const row = requireSingleSelection('强制下线')
      if (row) await kickSession(row)
    }

    onMounted(async () => {
      await Promise.all([loadServers(), loadAccounts(), loadSessions()])
    })

    return {
      accounts,
      actionIconMap,
      accountLabel,
      can,
      changePage,
      changePageSize,
      formatDate,
      formatDuration,
      formatTraffic,
      isAllRowsSelected,
      loadSessions,
      kickSelectedSession,
      kickSession,
      loading,
      openVpnPageEnd,
      openVpnPageSizeOptions,
      openVpnPageStart,
      openVpnPaginationTotal,
      pagination,
      resetQuery,
      searchSessions,
      selectedRow,
      selectedRowIds,
      selectedRows,
      serverName,
      servers,
      sessions,
      sessionQuery,
      statusText,
      toggleAllRows,
      toggleRowSelection,
    }
  },
}
