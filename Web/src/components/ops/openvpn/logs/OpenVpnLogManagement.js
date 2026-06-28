import '../../../../styles/components/resource-page.css'
import { onMounted, reactive, ref } from 'vue'
import { token, hasPermission } from '../../../../composables/useAuth.js'
import { openvpnAPI } from '../../../../api/openvpn.js'
import { actionIconMap } from '../../../system/resourcePageConstants.js'
import {
  asOpenVpnArray,
  downloadOpenVpnTextFile,
  emptyOpenVpnPagination,
  formatOpenVpnDate,
  openVpnPageEnd,
  openVpnPageSizeOptions,
  openVpnPageStart,
  openVpnPaginationTotal,
  resetOpenVpnPagination,
  resetOpenVpnReactive,
  sliceOpenVpnPageRows,
} from '../shared/openVpnConfig.js'

export default {
  setup() {
    const loading = ref(false)
    const servers = ref([])
    const logs = ref([])
    const logQuery = reactive({ user_id: '', department_id: '', server_id: '', action: '', result: '' })
    const pagination = reactive(emptyOpenVpnPagination())
    const pageCursors = reactive({ 1: null })
    const can = (permission) => hasPermission(permission)
    const formatDate = formatOpenVpnDate

    function serverName(id) {
      return servers.value.find((item) => item.id === id)?.name || '-'
    }

    async function loadServers() {
      servers.value = asOpenVpnArray(await openvpnAPI.listServers(token.value, { include_disabled: true }))
    }

    async function loadLogs() {
      loading.value = true
      try {
        const cursorId = pageCursors[pagination.page] || null
        const rows = await openvpnAPI.listLogs(token.value, {
          ...logQuery,
          limit: pagination.pageSize + 1,
          cursor_id: cursorId,
        })
        logs.value = sliceOpenVpnPageRows(rows, pagination)
        if (pagination.hasNext && logs.value.length > 0) {
          pageCursors[pagination.page + 1] = logs.value[logs.value.length - 1].id
        }
      } finally {
        loading.value = false
      }
    }

    function resetLogPagination() {
      resetOpenVpnPagination(pagination)
      Object.keys(pageCursors).forEach((key) => delete pageCursors[key])
      pageCursors[1] = null
    }

    function changePageSize() {
      resetLogPagination()
      loadLogs()
    }

    function searchLogs() {
      resetLogPagination()
      loadLogs()
    }

    function resetQuery() {
      resetOpenVpnReactive(logQuery, { user_id: '', department_id: '', server_id: '', action: '', result: '' })
      searchLogs()
    }

    function changePage(page) {
      if (page > 1 && !(page in pageCursors)) return
      pagination.page = page
      loadLogs()
    }

    async function exportLogs() {
      const result = await openvpnAPI.exportLogs(token.value, logQuery)
      downloadOpenVpnTextFile(result.filename, result.content, 'text/csv;charset=utf-8')
    }

    onMounted(async () => {
      await Promise.all([loadServers(), loadLogs()])
    })

    return {
      actionIconMap,
      can,
      changePage,
      changePageSize,
      exportLogs,
      formatDate,
      logQuery,
      loading,
      logs,
      openVpnPageEnd,
      openVpnPageSizeOptions,
      openVpnPageStart,
      openVpnPaginationTotal,
      pagination,
      resetQuery,
      searchLogs,
      serverName,
    }
  },
}
