import '../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { token, hasPermission } from '../../../composables/useAuth.js'
import { adminAPI } from '../../../api/admin.js'
import { openvpnAPI } from '../../../api/openvpn.js'

const tabs = [
  { key: 'servers', label: '服务器管理', permission: 'ops:openvpn:server:query' },
  { key: 'accounts', label: '账号管理', permission: 'ops:openvpn:account:query' },
  { key: 'certificates', label: '证书管理', permission: 'ops:openvpn:cert:query' },
  { key: 'sessions', label: '在线会话', permission: 'ops:openvpn:session:query' },
  { key: 'logs', label: '连接日志', permission: 'ops:openvpn:log:query' },
  { key: 'rules', label: '分配策略', permission: 'ops:openvpn:rule:query' },
]

function emptyServerForm() {
  return {
    name: '',
    code: '',
    region: '',
    host: '',
    port: 1194,
    protocol: 'udp',
    management_host: '',
    management_port: '',
    max_clients: 0,
    current_clients: 0,
    status: 'disabled',
    is_default: false,
    is_active: true,
    config_template: '',
    remark: '',
  }
}

function emptyRuleForm() {
  return {
    name: '',
    server_id: '',
    target_type: 'department',
    target_id: '',
    priority: 100,
    fallback_enabled: false,
    is_active: true,
    remark: '',
  }
}

export default {
  setup() {
    const activeTab = ref('servers')
    const loading = ref(false)
    const servers = ref([])
    const accounts = ref([])
    const certificates = ref([])
    const sessions = ref([])
    const logs = ref([])
    const rules = ref([])
    const users = ref([])
    const departments = ref([])
    const roles = ref([])
    const positions = ref([])
    const serverDialogVisible = ref(false)
    const ruleDialogVisible = ref(false)
    const editingServerId = ref(null)
    const editingRuleId = ref(null)
    const serverForm = reactive(emptyServerForm())
    const ruleForm = reactive(emptyRuleForm())
    const accountQuery = reactive({ username: '', status: '', server_id: '' })
    const serverQuery = reactive({ name: '', code: '', status: '', region: '', include_disabled: true })
    const ruleQuery = reactive({ target_type: '', server_id: '' })
    const enableLayer = reactive({ visible: false, user_id: '', server_id: '', vpn_username: '', remark: '' })
    const assignLayer = reactive({ visible: false, account_id: null, server_id: '' })

    const visibleTabs = computed(() => tabs.filter((tab) => hasPermission(tab.permission)))
    const can = (permission) => hasPermission(permission)
    const dashboard = computed(() => ({
      serverTotal: servers.value.length,
      onlineServers: servers.value.filter((item) => item.status === 'online').length,
      onlineSessions: sessions.value.filter((item) => item.status === 'online').length,
      expiringCerts: certificates.value.filter((item) => {
        if (!item.expires_at || item.status !== 'issued') return false
        return new Date(item.expires_at).getTime() - Date.now() < 1000 * 60 * 60 * 24 * 30
      }).length,
    }))

    const targetOptions = computed(() => {
      if (ruleForm.target_type === 'user') return users.value.map((item) => ({ id: item.id, name: `${item.username}${item.nickname ? ` / ${item.nickname}` : ''}` }))
      if (ruleForm.target_type === 'role') return roles.value.map((item) => ({ id: item.id, name: item.name }))
      if (ruleForm.target_type === 'position') return positions.value.map((item) => ({ id: item.id, name: item.name }))
      return departments.value.map((item) => ({ id: item.id, name: item.name }))
    })

    function formatDate(value) {
      if (!value) return '-'
      return new Date(value).toLocaleString()
    }

    function statusText(value) {
      const map = {
        online: '在线',
        offline: '离线',
        maintenance: '维护',
        disabled: '停用',
        pending: '待开通',
        enabled: '已启用',
        revoked: '已吊销',
        issued: '已签发',
        expired: '已过期',
      }
      return map[value] || value || '-'
    }

    function serverName(id) {
      return servers.value.find((item) => item.id === id)?.name || '-'
    }

    function resetReactive(target, source) {
      Object.keys(target).forEach((key) => delete target[key])
      Object.assign(target, source)
    }

    async function loadServers() {
      servers.value = await openvpnAPI.listServers(token.value, serverQuery)
    }

    async function loadAccounts() {
      accounts.value = await openvpnAPI.listAccounts(token.value, accountQuery)
    }

    async function loadCertificates() {
      certificates.value = await openvpnAPI.listCertificates(token.value)
    }

    async function loadSessions() {
      sessions.value = await openvpnAPI.listSessions(token.value)
    }

    async function loadLogs() {
      logs.value = await openvpnAPI.listLogs(token.value)
    }

    async function loadRules() {
      rules.value = await openvpnAPI.listRules(token.value, ruleQuery)
    }

    async function loadOptions() {
      const [userRows, departmentRows, roleRows, positionRows] = await Promise.all([
        adminAPI.users.list(token.value, { includeDisabled: true }),
        adminAPI.departments.list(token.value, { includeDisabled: true }),
        adminAPI.roles.list(token.value, { includeDisabled: true }),
        adminAPI.positions.list(token.value, { includeDisabled: true }),
      ])
      users.value = userRows
      departments.value = departmentRows
      roles.value = roleRows
      positions.value = positionRows
    }

    async function loadActiveTab() {
      loading.value = true
      try {
        if (activeTab.value === 'servers') await loadServers()
        if (activeTab.value === 'accounts') await loadAccounts()
        if (activeTab.value === 'certificates') await loadCertificates()
        if (activeTab.value === 'sessions') await loadSessions()
        if (activeTab.value === 'logs') await loadLogs()
        if (activeTab.value === 'rules') await loadRules()
      } finally {
        loading.value = false
      }
    }

    async function loadOverview() {
      await Promise.allSettled([loadServers(), loadSessions(), loadCertificates()])
    }

    function switchTab(key) {
      activeTab.value = key
      loadActiveTab()
    }

    function openCreateServer() {
      editingServerId.value = null
      resetReactive(serverForm, emptyServerForm())
      serverDialogVisible.value = true
    }

    function openEditServer(row) {
      editingServerId.value = row.id
      resetReactive(serverForm, {
        ...emptyServerForm(),
        ...row,
        management_port: row.management_port || '',
        config_template: row.config_template || '',
        remark: row.remark || '',
      })
      serverDialogVisible.value = true
    }

    async function saveServer() {
      const payload = {
        ...serverForm,
        port: Number(serverForm.port) || 1194,
        management_port: serverForm.management_port ? Number(serverForm.management_port) : null,
        max_clients: Number(serverForm.max_clients) || 0,
        current_clients: Number(serverForm.current_clients) || 0,
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

    async function setDefaultServer(row) {
      await openvpnAPI.setDefaultServer(token.value, row.id)
      ElMessage.success('默认服务器已更新')
      await loadServers()
    }

    async function testServer(row) {
      const result = await openvpnAPI.testServer(token.value, row.id)
      ElMessage[result.ok ? 'success' : 'warning'](result.message)
    }

    function openEnableAccount() {
      Object.assign(enableLayer, { visible: true, user_id: '', server_id: '', vpn_username: '', remark: '' })
    }

    async function enableAccount() {
      await openvpnAPI.enableAccount(token.value, enableLayer.user_id, {
        server_id: enableLayer.server_id || null,
        vpn_username: enableLayer.vpn_username || null,
        remark: enableLayer.remark || null,
      })
      enableLayer.visible = false
      ElMessage.success('VPN账号已开通')
      await loadAccounts()
    }

    async function disableAccount(row) {
      await ElMessageBox.confirm(`确认禁用 ${row.username} 的VPN账号？`, '禁用确认', { type: 'warning' })
      await openvpnAPI.disableAccount(token.value, row.user_id)
      ElMessage.success('VPN账号已禁用')
      await loadAccounts()
    }

    function openAssignServer(row) {
      Object.assign(assignLayer, { visible: true, account_id: row.id, server_id: row.server_id || '' })
    }

    async function assignServer() {
      await openvpnAPI.assignAccountServer(token.value, assignLayer.account_id, assignLayer.server_id)
      assignLayer.visible = false
      ElMessage.success('服务器分配已更新')
      await loadAccounts()
    }

    async function issueCertificate(row) {
      await openvpnAPI.issueCertificate(token.value, row.id, { valid_days: 365 })
      ElMessage.success('证书已签发')
      await Promise.all([loadAccounts(), loadCertificates()])
    }

    async function revokeCertificate(row) {
      await ElMessageBox.confirm(`确认吊销证书 ${row.serial_number}？`, '吊销确认', { type: 'warning' })
      await openvpnAPI.revokeCertificate(token.value, row.id, '管理员手动吊销')
      ElMessage.success('证书已吊销')
      await loadCertificates()
    }

    async function renewCertificate(row) {
      await openvpnAPI.renewCertificate(token.value, row.id, { valid_days: 365 })
      ElMessage.success('证书已续期')
      await loadCertificates()
    }

    async function downloadConfig(row) {
      const result = await openvpnAPI.downloadConfig(token.value, row.id)
      const blob = new Blob([result.content], { type: 'application/x-openvpn-profile' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = result.filename
      link.click()
      URL.revokeObjectURL(url)
    }

    async function kickSession(row) {
      await openvpnAPI.kickSession(token.value, row.id)
      ElMessage.success('会话已下线')
      await loadSessions()
    }

    function openCreateRule() {
      editingRuleId.value = null
      resetReactive(ruleForm, emptyRuleForm())
      ruleDialogVisible.value = true
    }

    function openEditRule(row) {
      editingRuleId.value = row.id
      resetReactive(ruleForm, { ...emptyRuleForm(), ...row })
      ruleDialogVisible.value = true
    }

    async function saveRule() {
      const payload = {
        ...ruleForm,
        server_id: Number(ruleForm.server_id),
        target_id: Number(ruleForm.target_id),
        priority: Number(ruleForm.priority) || 100,
      }
      if (editingRuleId.value) {
        await openvpnAPI.updateRule(token.value, editingRuleId.value, payload)
      } else {
        await openvpnAPI.createRule(token.value, payload)
      }
      ruleDialogVisible.value = false
      ElMessage.success('分配规则已保存')
      await loadRules()
    }

    async function deleteRule(row) {
      await ElMessageBox.confirm(`确认删除规则 ${row.name}？`, '删除确认', { type: 'warning' })
      await openvpnAPI.deleteRule(token.value, row.id)
      ElMessage.success('分配规则已删除')
      await loadRules()
    }

    onMounted(async () => {
      await Promise.allSettled([loadOptions(), loadOverview()])
      if (!visibleTabs.value.some((tab) => tab.key === activeTab.value) && visibleTabs.value[0]) {
        activeTab.value = visibleTabs.value[0].key
      }
      await loadActiveTab()
    })

    return {
      accountQuery,
      accounts,
      activeTab,
      assignLayer,
      can,
      certificates,
      dashboard,
      departments,
      deleteRule,
      deleteServer,
      disableAccount,
      downloadConfig,
      editingRuleId,
      editingServerId,
      enableAccount,
      enableLayer,
      formatDate,
      issueCertificate,
      kickSession,
      loadAccounts,
      loadActiveTab,
      loadRules,
      loadServers,
      loading,
      logs,
      openAssignServer,
      openCreateRule,
      openCreateServer,
      openEditRule,
      openEditServer,
      openEnableAccount,
      positions,
      renewCertificate,
      revokeCertificate,
      roleOptions: roles,
      ruleDialogVisible,
      ruleForm,
      ruleQuery,
      rules,
      saveRule,
      saveServer,
      serverDialogVisible,
      serverForm,
      serverName,
      serverQuery,
      servers,
      sessions,
      setDefaultServer,
      statusText,
      switchTab,
      targetOptions,
      testServer,
      users,
      visibleTabs,
    }
  },
}
