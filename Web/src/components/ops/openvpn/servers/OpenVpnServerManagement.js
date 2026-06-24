import '../../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref, watch } from 'vue'
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
    const lastAutoServerCode = ref('')
    const lastAutoServerName = ref('')
    const serverQuery = reactive({ name: '', code: '', status: '', region: '', include_disabled: true })
    const pagination = reactive(emptyOpenVpnPagination())
    const serverForm = reactive(emptyOpenVpnServerForm())

    const selectedRows = computed(() => servers.value.filter((row) => selectedRowIds.value.includes(row.id)))
    const selectedRow = computed(() => selectedRows.value[0] || null)
    const isAllRowsSelected = computed(
      () => servers.value.length > 0 && selectedRows.value.length === servers.value.length,
    )
    const isWireGuardMode = computed(() => serverForm.vpn_type === 'wireguard')
    const expectedSshKeyPath = computed(() => {
      if (serverForm.ssh_key_path) return serverForm.ssh_key_path
      if (!serverForm.code) return '/data/oim/ssh/<服务器编码>.key'
      return `/data/oim/ssh/${serverForm.code}.key`
    })
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
      lastAutoServerCode.value = ''
      lastAutoServerName.value = ''
      resetOpenVpnReactive(serverForm, emptyOpenVpnServerForm())
      serverDialogVisible.value = true
    }

    function openEditServer(row) {
      editingServerId.value = row.id
      lastAutoServerCode.value = ''
      lastAutoServerName.value = ''
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

    function normalizeServerCode(value) {
      return String(value || '')
        .trim()
        .replace(/[^a-zA-Z0-9_-]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .toUpperCase()
    }

    function inferServerCode(region, host) {
      const regionPart = normalizeServerCode(region || 'VPN')
      const typePart = serverForm.vpn_type === 'wireguard' ? 'WG' : regionPart
      const hostPart = String(host || '')
        .trim()
        .split('.')
        .filter(Boolean)
        .pop()
      return normalizeServerCode(`${typePart}-${hostPart || 'SERVER'}`)
    }

    function applySmartServerDefaults() {
      if (serverForm.vpn_type === 'wireguard') {
        serverForm.port = Number(serverForm.port) === 1194 ? 51820 : serverForm.port || 51820
        serverForm.protocol = 'udp'
        serverForm.certificate_backend = 'wireguard'
        serverForm.wg_interface = serverForm.wg_interface || 'wg0'
        serverForm.wg_network_cidr = serverForm.wg_network_cidr || '10.66.0.0/24'
        serverForm.wg_dns = serverForm.wg_dns || '1.1.1.1,1.0.0.1'
        serverForm.wg_allowed_ips = serverForm.wg_allowed_ips || '0.0.0.0/0,::/0'
        serverForm.wg_persistent_keepalive = serverForm.wg_persistent_keepalive ?? 25
      } else if (serverForm.certificate_backend === 'wireguard') {
        serverForm.port = Number(serverForm.port) === 51820 ? 1194 : serverForm.port || 1194
        serverForm.certificate_backend = 'ssh_easyrsa'
      }
      if (!serverForm.host) return
      if (!serverForm.ssh_host) serverForm.ssh_host = serverForm.host
      const inferredCode = inferServerCode(serverForm.region, serverForm.host)
      if (!serverForm.code || serverForm.code === lastAutoServerCode.value) {
        serverForm.code = inferredCode
        lastAutoServerCode.value = inferredCode
      }
      const inferredName = `OpenVPN-${serverForm.code}`
      if (!serverForm.name || serverForm.name === lastAutoServerName.value) {
        serverForm.name = inferredName
        lastAutoServerName.value = inferredName
      }
      if (!serverForm.ssh_user) serverForm.ssh_user = 'root'
    }

    async function saveServer() {
      applySmartServerDefaults()
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
        ssh_private_key_content: serverForm.ssh_private_key_content || null,
        easy_rsa_dir: serverForm.easy_rsa_dir || null,
        pki_dir: serverForm.pki_dir || null,
        ca_cert_path: serverForm.ca_cert_path || null,
        tls_crypt_key_path: serverForm.tls_crypt_key_path || null,
        crl_path: serverForm.crl_path || null,
        client_config_dir: serverForm.client_config_dir || null,
        config_template: serverForm.config_template || null,
        wg_interface: serverForm.wg_interface || null,
        wg_network_cidr: serverForm.wg_network_cidr || null,
        wg_dns: serverForm.wg_dns || null,
        wg_allowed_ips: serverForm.wg_allowed_ips || null,
        wg_persistent_keepalive: serverForm.wg_persistent_keepalive !== '' ? Number(serverForm.wg_persistent_keepalive) : null,
        wg_public_key: serverForm.wg_public_key || null,
      }
      let savedServer = null
      if (editingServerId.value) {
        savedServer = await openvpnAPI.updateServer(token.value, editingServerId.value, payload)
      } else {
        savedServer = await openvpnAPI.createServer(token.value, payload)
      }
      serverForm.ssh_private_key_content = ''
      serverDialogVisible.value = false
      ElMessage.success('服务器已保存')
      await loadServers()
      if (can('ops:openvpn:server:test') && savedServer?.id && ['ssh_easyrsa', 'wireguard'].includes(savedServer.certificate_backend)) {
        try {
          await testServer(savedServer, { silentSuccess: true })
        } catch (error) {
          ElMessage.warning(error?.message || '服务器已保存，但自动测试未通过')
        }
      }
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
      try {
        await testServer(row)
      } catch (error) {
        ElMessage.error(error?.message || '服务器配置不可用')
      }
    }

    async function testServer(row, options = {}) {
      const result = await openvpnAPI.testServer(token.value, row.id)
      if (result?.ok) {
        if (!options.silentSuccess) ElMessage.success(result.message || '服务器配置可用')
      } else {
        ElMessage.error(result?.message || '服务器配置不可用')
      }
    }

    watch(
      () => [serverForm.host, serverForm.region],
      () => {
        if (!serverDialogVisible.value || editingServerId.value) return
        applySmartServerDefaults()
      },
    )

    watch(
      () => serverForm.vpn_type,
      () => {
        if (!serverDialogVisible.value || editingServerId.value) return
        lastAutoServerCode.value = ''
        lastAutoServerName.value = ''
        applySmartServerDefaults()
      },
    )

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
      expectedSshKeyPath,
      isAllRowsSelected,
      isWireGuardMode,
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
