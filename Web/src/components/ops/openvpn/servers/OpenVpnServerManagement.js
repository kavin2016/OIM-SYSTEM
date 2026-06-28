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
    const isRemoteSshMode = computed(
      () => serverForm.vpn_type === 'wireguard' || serverForm.certificate_backend === 'ssh_easyrsa',
    )
    const currentVpnTypeGuide = computed(() => {
      if (serverForm.vpn_type === 'wireguard') {
        return {
          title: 'WireGuard 服务器端配置说明',
          summary: '适合新服务器快速接入。系统会通过 SSH 初始化 wg0、读取服务器公钥，并在签发凭据时自动追加 Peer。',
          sections: [
            {
              title: '服务器要求',
              lines: [
                'Linux 主机需要开放 SSH 登录，推荐使用 root 或具备 sudo 权限的运维账号。',
                'UDP 51820 需要在云安全组和系统防火墙中放行。',
                'CentOS 8.2 等内核不支持 WireGuard 模块时，系统可使用 wireguard-go 用户态方式运行。',
              ],
            },
            {
              title: '系统默认配置',
              lines: [
                '接口：wg0；端口：51820/udp；客户端网段：10.66.0.0/24。',
                '客户端 DNS：1.1.1.1,1.0.0.1；允许访问：0.0.0.0/0,::/0；Keepalive：25。',
                '服务器私钥保存在 VPN 服务器 /etc/wireguard/server_private.key。',
              ],
            },
            {
              title: '添加服务器时需要填写',
              lines: [
                '公网 IP / 域名、区域、服务器编码、SSH 用户、SSH 私钥内容。',
                '高级参数可以保持默认，系统会在保存服务器时自动检测 WireGuard 配置。',
              ],
            },
          ],
        }
      }
      return {
        title: 'OpenVPN 服务器端配置说明',
        summary: '适合已有 OpenVPN + Easy-RSA 的服务器接入。系统通过 SSH 调用 Easy-RSA 签发、吊销证书，并生成客户端 ovpn 文件。',
        sections: [
          {
            title: '服务器要求',
            lines: [
              'Linux 主机需要开放 SSH 登录，推荐使用 root 或具备 sudo 权限的运维账号。',
              'UDP 1194 需要在云安全组和系统防火墙中放行。',
              '服务器上需要存在可用的 Easy-RSA、PKI、CA 证书、CRL 和 tls-crypt/tls-auth 密钥。',
            ],
          },
          {
            title: '系统默认路径',
            lines: [
              'Easy-RSA目录：/etc/openvpn/easy-rsa；PKI目录：/etc/openvpn/easy-rsa/pki。',
              'CA证书：/etc/openvpn/easy-rsa/pki/ca.crt；CRL：/etc/openvpn/easy-rsa/pki/crl.pem。',
              'TLS密钥：优先使用服务器记录配置，未填写时按系统默认路径处理。',
            ],
          },
          {
            title: '添加服务器时需要填写',
            lines: [
              '公网 IP / 域名、区域、服务器编码、SSH 用户、SSH 私钥内容。',
              '如服务器使用标准路径，高级配置可以不填写；非标准安装时再展开高级配置维护路径。',
            ],
          },
        ],
      }
    })
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
      if (!editingServerId.value && isRemoteSshMode.value && !serverForm.ssh_private_key_content?.trim()) {
        ElMessage.warning('请填写SSH私钥内容，系统会自动写入后端容器路径并完成连接检测')
        return
      }
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
      currentVpnTypeGuide,
      isAllRowsSelected,
      isWireGuardMode,
      isRemoteSshMode,
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
