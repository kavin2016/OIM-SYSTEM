import '../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { token, hasPermission } from '../../../composables/useAuth.js'
import { openvpnAPI } from '../../../api/openvpn.js'
import { actionIconMap } from '../../system/resourcePageConstants.js'

const tabs = [
  { key: 'servers', label: '服务器管理', permission: 'ops:openvpn:server:query' },
  { key: 'accounts', label: '用户管理', permission: 'ops:openvpn:account:query' },
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
    max_clients: 0,
    current_clients: 0,
    status: 'disabled',
    is_default: false,
    is_active: true,
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

function asArray(value) {
  return Array.isArray(value) ? value : []
}

const EnableUserTreeNode = {
  name: 'EnableUserTreeNode',
  props: {
    node: { type: Object, required: true },
    level: { type: Number, default: 0 },
    selectedId: { type: [Number, String], default: '' },
  },
  emits: ['select'],
  computed: {
    isUser() {
      return this.node.type === 'user'
    },
    isSelected() {
      return this.isUser && Number(this.selectedId) === Number(this.node.id)
    },
  },
  template: `
    <div class="vpn-user-tree-node">
      <button
        type="button"
        class="vpn-user-tree-item"
        :class="{ department: !isUser, user: isUser, selected: isSelected }"
        :style="{ paddingLeft: (12 + level * 16) + 'px' }"
        @click="$emit('select', node)"
      >
        <span class="vpn-user-tree-marker">{{ isUser ? '•' : '▸' }}</span>
        <span class="vpn-user-tree-text">{{ node.label }}</span>
      </button>
      <EnableUserTreeNode
        v-for="child in node.children"
        :key="child.key"
        :node="child"
        :level="level + 1"
        :selected-id="selectedId"
        @select="$emit('select', $event)"
      />
    </div>
  `,
}

export default {
  components: {
    EnableUserTreeNode,
  },
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
    const enableUserKeyword = ref('')
    const enableUserDropdownVisible = ref(false)
    const assignLayer = reactive({ visible: false, account_id: null, server_id: '' })
    const selectedRowIds = ref([])

    const visibleTabs = computed(() => tabs.filter((tab) => hasPermission(tab.permission)))
    const can = (permission) => hasPermission(permission)
    const activeRows = computed(() => {
      const map = {
        servers: servers.value,
        accounts: accounts.value,
        sessions: sessions.value,
        logs: logs.value,
        rules: rules.value,
      }
      return asArray(map[activeTab.value])
    })
    const selectedRows = computed(() => asArray(activeRows.value).filter((row) => selectedRowIds.value.includes(row.id)))
    const selectedRow = computed(() => selectedRows.value[0] || null)
    const isAllRowsSelected = computed(
      () => activeRows.value.length > 0 && selectedRows.value.length === activeRows.value.length,
    )
    const dashboard = computed(() => ({
      serverTotal: asArray(servers.value).length,
      onlineServers: asArray(servers.value).filter((item) => item.status === 'online').length,
      onlineSessions: asArray(sessions.value).filter((item) => item.status === 'online').length,
      expiringCerts: asArray(certificates.value).filter((item) => {
        if (!item.expires_at || item.status !== 'issued') return false
        return new Date(item.expires_at).getTime() - Date.now() < 1000 * 60 * 60 * 24 * 30
      }).length,
    }))

    const targetOptions = computed(() => {
      if (ruleForm.target_type === 'user') return asArray(users.value).map((item) => ({ id: item.id, name: `${item.username}${item.nickname ? ` / ${item.nickname}` : ''}` }))
      if (ruleForm.target_type === 'role') return asArray(roles.value).map((item) => ({ id: item.id, name: item.name }))
      if (ruleForm.target_type === 'position') return asArray(positions.value).map((item) => ({ id: item.id, name: item.name }))
      return asArray(departments.value).map((item) => ({ id: item.id, name: item.name }))
    })
    const enableUserTree = computed(() => buildEnableUserTree())

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
      return asArray(servers.value).find((item) => item.id === id)?.name || '-'
    }

    function resetReactive(target, source) {
      Object.keys(target).forEach((key) => delete target[key])
      Object.assign(target, source)
    }

    function userLabel(user) {
      return `${user.username}${user.nickname ? ` / ${user.nickname}` : ''}`
    }

    function buildEnableUserTree() {
      const keyword = enableUserKeyword.value.trim().toLowerCase()
      const departmentMap = new Map(
        asArray(departments.value).map((department) => [
          department.id,
          {
            key: `department-${department.id}`,
            type: 'department',
            id: department.id,
            parentId: department.parent_id || null,
            label: `${department.name}${department.code ? `（${department.code}）` : ''}`,
            children: [],
          },
        ]),
      )
      const roots = []
      departmentMap.forEach((department) => {
        const parent = departmentMap.get(department.parentId)
        if (parent) parent.children.push(department)
        else roots.push(department)
      })

      const unassigned = {
        key: 'department-unassigned',
        type: 'department',
        id: null,
        parentId: null,
        label: '未分配部门',
        children: [],
      }

      asArray(users.value).forEach((user) => {
        const label = userLabel(user)
        const searchable = `${label} ${user.username || ''} ${user.nickname || ''}`.toLowerCase()
        if (keyword && !searchable.includes(keyword)) return
        const node = {
          key: `user-${user.id}`,
          type: 'user',
          id: user.id,
          label,
          children: [],
        }
        const departmentId = asArray(user.department_ids)[0]
        const department = departmentMap.get(departmentId)
        if (department) department.children.push(node)
        else unassigned.children.push(node)
      })

      if (unassigned.children.length > 0) roots.push(unassigned)
      return pruneEmptyDepartments(roots)
    }

    function pruneEmptyDepartments(nodes) {
      return nodes
        .map((node) => {
          if (node.type === 'user') return node
          const children = pruneEmptyDepartments(node.children || [])
          return children.length > 0 ? { ...node, children } : null
        })
        .filter(Boolean)
    }

    function selectEnableUser(node) {
      if (node.type !== 'user' || node.children?.length) {
        ElMessage.warning('请选择最后一级用户节点')
        return
      }
      enableLayer.user_id = node.id
      enableLayer.vpn_username = users.value.find((item) => item.id === node.id)?.username || ''
      enableUserKeyword.value = node.label
      enableUserDropdownVisible.value = false
    }

    function isEnableUserSelected(node) {
      return node.type === 'user' && Number(enableLayer.user_id) === Number(node.id)
    }

    function openEnableUserDropdown() {
      enableUserDropdownVisible.value = true
    }

    function closeEnableUserDropdown(event) {
      if (event.currentTarget.contains(event.relatedTarget)) return
      enableUserDropdownVisible.value = false
    }

    async function loadServers() {
      servers.value = asArray(await openvpnAPI.listServers(token.value, serverQuery))
    }

    async function loadAccounts() {
      accounts.value = asArray(await openvpnAPI.listAccounts(token.value, accountQuery))
    }

    async function loadCertificates() {
      certificates.value = asArray(await openvpnAPI.listCertificates(token.value))
    }

    async function loadSessions() {
      sessions.value = asArray(await openvpnAPI.listSessions(token.value))
    }

    async function loadLogs() {
      logs.value = asArray(await openvpnAPI.listLogs(token.value))
    }

    async function loadRules() {
      rules.value = asArray(await openvpnAPI.listRules(token.value, ruleQuery))
    }

    async function loadOptions() {
      const options = await openvpnAPI.listOptions(token.value) || {}
      users.value = asArray(options.users)
      departments.value = asArray(options.departments)
      roles.value = asArray(options.roles)
      positions.value = asArray(options.positions)
    }

    async function loadActiveTab() {
      loading.value = true
      try {
        if (activeTab.value === 'servers') await loadServers()
        if (activeTab.value === 'accounts') await loadAccounts()
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
      selectedRowIds.value = []
      loadActiveTab()
    }

    function resetQuery(query, source) {
      resetReactive(query, source)
      selectedRowIds.value = []
      loadActiveTab()
    }

    function toggleRowSelection(row) {
      if (selectedRowIds.value.includes(row.id)) {
        selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
        return
      }
      selectedRowIds.value = [...selectedRowIds.value, row.id]
    }

    function toggleAllRows() {
      selectedRowIds.value = isAllRowsSelected.value ? [] : activeRows.value.map((row) => row.id)
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

    function editSelectedServer() {
      const row = requireSingleSelection('修改')
      if (row) openEditServer(row)
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

    async function setDefaultSelectedServer() {
      const row = requireSingleSelection('设为默认')
      if (row) await setDefaultServer(row)
    }

    function assignSelectedAccountServer() {
      const row = requireSingleSelection('分配服务器')
      if (row) openAssignServer(row)
    }

    async function issueSelectedAccountCertificate() {
      const row = requireSingleSelection('签发证书')
      if (row) await issueCertificate(row)
    }

    async function downloadSelectedAccountConfig() {
      const row = requireSingleSelection('下载配置')
      if (row) await downloadConfig(row)
    }

    async function disableSelectedAccounts() {
      const rows = requireAnySelection('禁用')
      if (rows.length === 0) return
      await ElMessageBox.confirm(`确认禁用选中的 ${rows.length} 个 VPN 账号？`, '禁用确认', { type: 'warning' })
      await Promise.all(rows.map((row) => openvpnAPI.disableAccount(token.value, row.user_id)))
      selectedRowIds.value = []
      ElMessage.success('VPN账号已禁用')
      await loadAccounts()
    }

    async function renewSelectedCertificate() {
      const row = requireSingleSelection('续期')
      if (row) await renewAccountCertificate(row)
    }

    async function revokeSelectedCertificate() {
      const row = requireSingleSelection('吊销')
      if (row) await revokeAccountCertificate(row)
    }

    async function kickSelectedSession() {
      const row = requireSingleSelection('强制下线')
      if (row) await kickSession(row)
    }

    function editSelectedRule() {
      const row = requireSingleSelection('修改')
      if (row) openEditRule(row)
    }

    async function deleteSelectedRules() {
      const rows = requireAnySelection('删除')
      if (rows.length === 0) return
      await ElMessageBox.confirm(`确认删除选中的 ${rows.length} 条分配规则？`, '删除确认', { type: 'warning' })
      await Promise.all(rows.map((row) => openvpnAPI.deleteRule(token.value, row.id)))
      selectedRowIds.value = []
      ElMessage.success('分配规则已删除')
      await loadRules()
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
        remark: row.remark || '',
      })
      serverDialogVisible.value = true
    }

    async function saveServer() {
      const payload = {
        ...serverForm,
        port: Number(serverForm.port) || 1194,
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

    async function openEnableAccount() {
      Object.assign(enableLayer, { visible: true, user_id: '', server_id: '', vpn_username: '', remark: '' })
      enableUserKeyword.value = ''
      enableUserDropdownVisible.value = false
      try {
        await loadOptions()
      } catch (error) {
        ElMessage.error(error.message || '用户数据加载失败')
      }
    }

    async function enableAccount() {
      await openvpnAPI.enableAccount(token.value, enableLayer.user_id, {
        server_id: enableLayer.server_id || null,
        vpn_username: enableLayer.vpn_username || null,
        remark: enableLayer.remark || null,
      })
      enableLayer.visible = false
      ElMessage.success('VPN账号已开通')
      await Promise.all([loadAccounts(), loadOptions()])
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

    async function revokeAccountCertificate(row) {
      if (!row.certificate_id) {
        ElMessage.warning('该用户没有可吊销的证书')
        return
      }
      await ElMessageBox.confirm(`确认吊销 ${row.username} 的OpenVPN证书？`, '吊销确认', { type: 'warning' })
      await openvpnAPI.revokeCertificate(token.value, row.certificate_id, '管理员手动吊销')
      ElMessage.success('证书已吊销')
      await Promise.all([loadAccounts(), loadCertificates()])
    }

    async function renewAccountCertificate(row) {
      if (!row.certificate_id) {
        ElMessage.warning('该用户没有可续期的证书')
        return
      }
      await openvpnAPI.renewCertificate(token.value, row.certificate_id, { valid_days: 365 })
      ElMessage.success('证书已续期')
      await Promise.all([loadAccounts(), loadCertificates()])
    }

    async function downloadConfig(row) {
      const result = await openvpnAPI.downloadConfig(token.value, row.id)
      downloadTextFile(result.filename, result.content, 'application/x-openvpn-profile')
    }

    function downloadTextFile(filename, content, type = 'text/plain;charset=utf-8') {
      const blob = new Blob([content], { type })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    }

    async function exportLogs() {
      const result = await openvpnAPI.exportLogs(token.value)
      downloadTextFile(result.filename, result.content, 'text/csv;charset=utf-8')
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
      actionIconMap,
      activeTab,
      activeRows,
      assignLayer,
      assignSelectedAccountServer,
      can,
      certificates,
      dashboard,
      departments,
      deleteRule,
      deleteSelectedRules,
      deleteSelectedServers,
      deleteServer,
      disableAccount,
      disableSelectedAccounts,
      downloadConfig,
      downloadSelectedAccountConfig,
      editingRuleId,
      editingServerId,
      editSelectedRule,
      editSelectedServer,
      enableAccount,
      enableLayer,
      enableUserKeyword,
      enableUserDropdownVisible,
      enableUserTree,
      exportLogs,
      formatDate,
      issueCertificate,
      issueSelectedAccountCertificate,
      isAllRowsSelected,
      isEnableUserSelected,
      kickSession,
      kickSelectedSession,
      loadAccounts,
      loadActiveTab,
      loadRules,
      loadServers,
      loading,
      logs,
      openAssignServer,
      openCreateRule,
      openCreateServer,
      openEnableUserDropdown,
      openEditRule,
      openEditServer,
      openEnableAccount,
      positions,
      renewAccountCertificate,
      renewSelectedCertificate,
      resetQuery,
      revokeAccountCertificate,
      revokeSelectedCertificate,
      roleOptions: roles,
      ruleDialogVisible,
      ruleForm,
      ruleQuery,
      rules,
      saveRule,
      saveServer,
      selectedRow,
      selectedRowIds,
      selectedRows,
      serverDialogVisible,
      serverForm,
      serverName,
      selectEnableUser,
      closeEnableUserDropdown,
      serverQuery,
      servers,
      sessions,
      setDefaultServer,
      setDefaultSelectedServer,
      statusText,
      switchTab,
      targetOptions,
      toggleAllRows,
      toggleRowSelection,
      users,
      visibleTabs,
    }
  },
}
