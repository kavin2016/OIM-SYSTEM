import '../../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { token, hasPermission } from '../../../../composables/useAuth.js'
import { openvpnAPI } from '../../../../api/openvpn.js'
import { actionIconMap } from '../../../system/resourcePageConstants.js'
import {
  asOpenVpnArray,
  emptyOpenVpnServerForm,
  emptyOpenVpnPagination,
  openVpnPageEnd,
  openVpnPageParams,
  openVpnPageSizeOptions,
  openVpnPageStart,
  openVpnPaginationTotal,
  openVpnStatusText,
  resetOpenVpnReactive,
  resetOpenVpnPagination,
  sliceOpenVpnPageRows,
} from '../shared/openVpnConfig.js'

export default {
  setup() {
    const loading = ref(false)
    const servers = ref([])
    const selectedRowIds = ref([])
    const serverDialogVisible = ref(false)
    const editingServerId = ref(null)
    const serverQuery = reactive({ name: '', code: '', status: '', region: '', include_disabled: true })
    const pagination = reactive(emptyOpenVpnPagination())
    const serverForm = reactive(emptyOpenVpnServerForm())

    const selectedRows = computed(() => servers.value.filter((row) => selectedRowIds.value.includes(row.id)))
    const selectedRow = computed(() => selectedRows.value[0] || null)
    const isAllRowsSelected = computed(
      () => servers.value.length > 0 && selectedRows.value.length === servers.value.length,
    )
    const can = (permission) => hasPermission(permission)
    const statusText = openVpnStatusText

    async function loadServers() {
      loading.value = true
      try {
        const rows = await openvpnAPI.listServers(token.value, { ...serverQuery, ...openVpnPageParams(pagination) })
        servers.value = sliceOpenVpnPageRows(rows, pagination)
        selectedRowIds.value = selectedRowIds.value.filter((id) => servers.value.some((row) => row.id === id))
      } finally {
        loading.value = false
      }
    }

    function searchServers() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadServers()
    }

    function resetQuery() {
      resetOpenVpnReactive(serverQuery, { name: '', code: '', status: '', region: '', include_disabled: true })
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadServers()
    }

    function changePageSize() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadServers()
    }

    function changePage(page) {
      pagination.page = page
      selectedRowIds.value = []
      loadServers()
    }

    function toggleRowSelection(row) {
      if (selectedRowIds.value.includes(row.id)) {
        selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
        return
      }
      selectedRowIds.value = [...selectedRowIds.value, row.id]
    }

    function toggleAllRows() {
      selectedRowIds.value = isAllRowsSelected.value ? [] : servers.value.map((row) => row.id)
    }

    function requireSingleSelection(actionName) {
      if (selectedRows.value.length !== 1) {
        ElMessage.warning(`请选择一条数据进行${actionName}`)
        return null
      }
      return selectedRow.value
    }

    function requireAnySelection(actionName) {
      if (selectedRows.value.length === 0) {
        ElMessage.warning(`请选择需要${actionName}的数据`)
        return []
      }
      return selectedRows.value
    }

    function openCreateServer() {
      editingServerId.value = null
      resetOpenVpnReactive(serverForm, emptyOpenVpnServerForm())
      serverDialogVisible.value = true
    }

    function openEditServer(row) {
      editingServerId.value = row.id
      resetOpenVpnReactive(serverForm, {
        ...emptyOpenVpnServerForm(),
        ...row,
        remark: row.remark || '',
      })
      serverDialogVisible.value = true
    }

    function editSelectedServer() {
      const row = requireSingleSelection('修改')
      if (row) openEditServer(row)
    }

    async function saveServer() {
      const payload = {
        ...serverForm,
        port: Number(serverForm.port) || 1194,
        max_clients: Number(serverForm.max_clients) || 0,
        current_clients: Number(serverForm.current_clients) || 0,
        management_port: serverForm.management_port ? Number(serverForm.management_port) : null,
        ssh_host: serverForm.ssh_host || null,
        ssh_port: serverForm.ssh_port ? Number(serverForm.ssh_port) : null,
        ssh_user: serverForm.ssh_user || null,
        ssh_key_path: serverForm.ssh_key_path || null,
        easy_rsa_dir: serverForm.easy_rsa_dir || null,
        pki_dir: serverForm.pki_dir || null,
        ca_cert_path: serverForm.ca_cert_path || null,
        tls_crypt_key_path: serverForm.tls_crypt_key_path || null,
        crl_path: serverForm.crl_path || null,
        client_config_dir: serverForm.client_config_dir || null,
        config_template: serverForm.config_template || null,
      }
      if (editingServerId.value) {
        await openvpnAPI.updateServer(token.value, editingServerId.value, payload)
      } else {
        await openvpnAPI.createServer(token.value, payload)
      }
      serverDialogVisible.value = false
      ElMessage.success('服务器已保存')
      await loadServers()
    }

    async function deleteServer(row) {
      await ElMessageBox.confirm(`确认删除服务器 ${row.name}？`, '删除确认', { type: 'warning' })
      await openvpnAPI.deleteServer(token.value, row.id)
      ElMessage.success('服务器已删除')
      await loadServers()
    }

    async function deleteSelectedServers() {
      const rows = requireAnySelection('删除')
      if (rows.length === 0) return
      await ElMessageBox.confirm(`确认删除选中的 ${rows.length} 台服务器？`, '删除确认', { type: 'warning' })
      await Promise.all(rows.map((row) => openvpnAPI.deleteServer(token.value, row.id)))
      selectedRowIds.value = []
      ElMessage.success('服务器已删除')
      await loadServers()
    }

    async function setDefaultServer(row) {
      await openvpnAPI.setDefaultServer(token.value, row.id)
      ElMessage.success('默认服务器已更新')
      await loadServers()
    }

    async function setDefaultSelectedServer() {
      const row = requireSingleSelection('设为默认')
      if (row) await setDefaultServer(row)
    }

    async function testSelectedServer() {
      const row = requireSingleSelection('测试')
      if (!row) return
      const result = await openvpnAPI.testServer(token.value, row.id)
      if (result?.ok) {
        ElMessage.success(result.message || '服务器配置可用')
      } else {
        ElMessage.error(result?.message || '服务器配置不可用')
      }
    }

    onMounted(loadServers)

    return {
      actionIconMap,
      can,
      changePage,
      changePageSize,
      deleteSelectedServers,
      deleteServer,
      editingServerId,
      editSelectedServer,
      isAllRowsSelected,
      loadServers,
      loading,
      openCreateServer,
      openEditServer,
      openVpnPageEnd,
      openVpnPageSizeOptions,
      openVpnPageStart,
      openVpnPaginationTotal,
      pagination,
      resetQuery,
      saveServer,
      searchServers,
      selectedRow,
      selectedRowIds,
      selectedRows,
      serverDialogVisible,
      serverForm,
      serverQuery,
      servers,
      setDefaultSelectedServer,
      setDefaultServer,
      statusText,
      testSelectedServer,
      toggleAllRows,
      toggleRowSelection,
    }
  },
}
