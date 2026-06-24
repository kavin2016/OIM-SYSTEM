import '../../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { token, hasPermission } from '../../../../composables/useAuth.js'
import { openvpnAPI } from '../../../../api/openvpn.js'
import { actionIconMap } from '../../../system/resourcePageConstants.js'
import EnableUserTreeNode from '../shared/EnableUserTreeNode.vue'
import {
  asOpenVpnArray,
  downloadOpenVpnTextFile,
  emptyOpenVpnPagination,
  formatOpenVpnDate,
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
  components: {
    EnableUserTreeNode,
  },
  setup() {
    const loading = ref(false)
    const servers = ref([])
    const accounts = ref([])
    const users = ref([])
    const departments = ref([])
    const selectedRowIds = ref([])
    const accountQuery = reactive({ username: '', status: '', server_id: '' })
    const pagination = reactive(emptyOpenVpnPagination())
    const enableLayer = reactive({ visible: false, user_id: '', server_id: '', vpn_username: '', remark: '' })
    const enableUserKeyword = ref('')
    const enableUserDropdownVisible = ref(false)
    const assignLayer = reactive({ visible: false, account_id: null, server_id: '' })
    const revokeCertificateLayer = reactive({
      visible: false,
      submitting: false,
      row: null,
    })
    const revokeAccountLayer = reactive({
      visible: false,
      submitting: false,
      row: null,
    })

    const selectedRows = computed(() => accounts.value.filter((row) => selectedRowIds.value.includes(row.id)))
    const selectedRow = computed(() => selectedRows.value[0] || null)
    const isAllRowsSelected = computed(
      () => accounts.value.length > 0 && selectedRows.value.length === accounts.value.length,
    )
    const enableUserTree = computed(() => buildEnableUserTree())
    const can = (permission) => hasPermission(permission)
    const formatDate = formatOpenVpnDate
    const statusText = openVpnStatusText

    async function loadServers() {
      servers.value = asOpenVpnArray(await openvpnAPI.listServers(token.value, { include_disabled: true }))
    }

    async function loadAccounts() {
      loading.value = true
      try {
        const rows = await openvpnAPI.listAccounts(token.value, { ...accountQuery, ...openVpnPageParams(pagination) })
        accounts.value = sliceOpenVpnPageRows(rows, pagination)
        selectedRowIds.value = selectedRowIds.value.filter((id) => accounts.value.some((row) => row.id === id))
      } finally {
        loading.value = false
      }
    }

    async function loadCertificates() {
      await openvpnAPI.listCertificates(token.value)
    }

    async function loadEnableAccountOptions() {
      const options = await openvpnAPI.listOptions(token.value) || {}
      users.value = asOpenVpnArray(options.users)
      departments.value = asOpenVpnArray(options.departments)
    }

    function resetQuery() {
      resetOpenVpnReactive(accountQuery, { username: '', status: '', server_id: '' })
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadAccounts()
    }

    function searchAccounts() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadAccounts()
    }

    function changePageSize() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadAccounts()
    }

    function changePage(page) {
      pagination.page = page
      selectedRowIds.value = []
      loadAccounts()
    }

    function userLabel(user) {
      return `${user.username}${user.nickname ? ` / ${user.nickname}` : ''}`
    }

    function buildEnableUserTree() {
      const keyword = enableUserKeyword.value.trim().toLowerCase()
      const departmentMap = new Map(
        departments.value.map((department) => [
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

      users.value.forEach((user) => {
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
        const departmentId = asOpenVpnArray(user.department_ids)[0]
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

    function openEnableUserDropdown() {
      enableUserDropdownVisible.value = true
    }

    function closeEnableUserDropdown(event) {
      if (event.currentTarget.contains(event.relatedTarget)) return
      enableUserDropdownVisible.value = false
    }

    function toggleRowSelection(row) {
      if (selectedRowIds.value.includes(row.id)) {
        selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
        return
      }
      selectedRowIds.value = [...selectedRowIds.value, row.id]
    }

    function toggleAllRows() {
      selectedRowIds.value = isAllRowsSelected.value ? [] : accounts.value.map((row) => row.id)
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

    function isCancelAction(error) {
      return error === 'cancel' || error === 'close' || error?.action === 'cancel' || error?.action === 'close'
    }

    async function openEnableAccount() {
      Object.assign(enableLayer, { visible: true, user_id: '', server_id: '', vpn_username: '', remark: '' })
      enableUserKeyword.value = ''
      enableUserDropdownVisible.value = false
      try {
        await loadEnableAccountOptions()
      } catch (error) {
        ElMessage.error(error.message || '用户数据加载失败')
      }
    }

    async function enableAccount() {
      if (!enableLayer.user_id) {
        ElMessage.warning('请选择用户')
        return
      }
      if (!enableLayer.server_id) {
        ElMessage.warning('请选择服务器')
        return
      }
      await openvpnAPI.enableAccount(token.value, enableLayer.user_id, {
        server_id: Number(enableLayer.server_id),
      })
      enableLayer.visible = false
      ElMessage.success('VPN账号已开通')
      await loadAccounts()
    }

    function openAssignServer(row) {
      Object.assign(assignLayer, { visible: true, account_id: row.id, server_id: row.server_id || '' })
    }

    function assignSelectedAccountServer() {
      const row = requireSingleSelection('分配服务器')
      if (row) openAssignServer(row)
    }

    async function assignServer() {
      await openvpnAPI.assignAccountServer(token.value, assignLayer.account_id, assignLayer.server_id)
      assignLayer.visible = false
      ElMessage.success('服务器分配已更新')
      await loadAccounts()
    }

    async function issueCertificate(row) {
      try {
        await openvpnAPI.issueCertificate(token.value, row.id, { valid_days: 365 })
        ElMessage.success('凭据已签发')
        await Promise.all([loadAccounts(), loadCertificates()])
      } catch (error) {
        ElMessageBox.alert(error.message || '凭据签发失败', '凭据签发失败', {
          type: 'error',
          confirmButtonText: '确定',
        }).catch(() => {})
      }
    }

    async function issueSelectedAccountCertificate() {
      const row = requireSingleSelection('签发凭据')
      if (row) await issueCertificate(row)
    }

    function revokeAccountCertificate(row) {
      if (!row.certificate_id) {
        ElMessage.warning('该用户没有可吊销的凭据')
        return
      }
      if (row.certificate_status !== 'issued') {
        ElMessage.warning('只有已签发的有效凭据才能吊销')
        return
      }
      Object.assign(revokeCertificateLayer, {
        visible: true,
        submitting: false,
        row,
      })
    }

    function closeRevokeCertificateLayer() {
      if (revokeCertificateLayer.submitting) return
      Object.assign(revokeCertificateLayer, {
        visible: false,
        submitting: false,
        row: null,
      })
    }

    async function confirmRevokeCertificate() {
      const row = revokeCertificateLayer.row
      if (!row?.certificate_id || revokeCertificateLayer.submitting) return
      revokeCertificateLayer.submitting = true
      try {
        await openvpnAPI.revokeCertificate(token.value, row.certificate_id, '管理员手动吊销')
        Object.assign(revokeCertificateLayer, {
          visible: false,
          submitting: false,
          row: null,
        })
        ElMessage.success('凭据已吊销')
        await Promise.all([loadAccounts(), loadCertificates()])
      } catch (error) {
        revokeCertificateLayer.submitting = false
        if (!isCancelAction(error)) ElMessage.error(error.message || '凭据吊销失败')
      }
    }

    async function revokeSelectedCertificate() {
      const row = requireSingleSelection('吊销')
      if (row) await revokeAccountCertificate(row)
    }

    function revokeAccount(row) {
      if (row.status === 'revoked') {
        ElMessage.warning('该VPN账号已吊销')
        return
      }
      Object.assign(revokeAccountLayer, {
        visible: true,
        submitting: false,
        row,
      })
    }

    function closeRevokeAccountLayer() {
      if (revokeAccountLayer.submitting) return
      Object.assign(revokeAccountLayer, {
        visible: false,
        submitting: false,
        row: null,
      })
    }

    async function confirmRevokeAccount() {
      const row = revokeAccountLayer.row
      if (!row?.id || revokeAccountLayer.submitting) return
      revokeAccountLayer.submitting = true
      try {
        await openvpnAPI.revokeAccount(token.value, row.id, '管理员手动吊销账号')
        selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
        Object.assign(revokeAccountLayer, {
          visible: false,
          submitting: false,
          row: null,
        })
        ElMessage.success('VPN账号已吊销')
        await Promise.all([loadAccounts(), loadCertificates()])
      } catch (error) {
        revokeAccountLayer.submitting = false
        if (!isCancelAction(error)) ElMessage.error(error.message || 'VPN账号吊销失败')
      }
    }

    async function revokeSelectedAccount() {
      const row = requireSingleSelection('吊销账号')
      if (row) await revokeAccount(row)
    }

    async function renewAccountCertificate(row) {
      if (!row.certificate_id) {
        ElMessage.warning('该用户没有可续期的凭据')
        return
      }
      try {
        await openvpnAPI.renewCertificate(token.value, row.certificate_id, { valid_days: 365 })
        ElMessage.success('凭据已续期')
        await Promise.all([loadAccounts(), loadCertificates()])
      } catch (error) {
        ElMessage.error(error.message || '凭据续期失败')
      }
    }

    async function renewSelectedCertificate() {
      const row = requireSingleSelection('续期')
      if (row) await renewAccountCertificate(row)
    }

    async function downloadConfig(row) {
      try {
        const result = await openvpnAPI.downloadConfig(token.value, row.id)
        downloadOpenVpnTextFile(result.filename, result.content, 'application/x-openvpn-profile')
      } catch (error) {
        ElMessage.error(error.message || '配置下载失败')
      }
    }

    async function downloadSelectedAccountConfig() {
      const row = requireSingleSelection('下载配置')
      if (row) await downloadConfig(row)
    }

    async function disableAccount(row) {
      await ElMessageBox.confirm(`确认禁用 ${row.username} 的VPN账号？`, '禁用确认', { type: 'warning' })
      await openvpnAPI.disableAccount(token.value, row.user_id)
      ElMessage.success('VPN账号已禁用')
      await loadAccounts()
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

    onMounted(async () => {
      await Promise.all([loadServers(), loadAccounts()])
    })

    return {
      accountQuery,
      accounts,
      actionIconMap,
      assignLayer,
      assignSelectedAccountServer,
      assignServer,
      can,
      changePage,
      changePageSize,
      closeEnableUserDropdown,
      closeRevokeAccountLayer,
      closeRevokeCertificateLayer,
      confirmRevokeAccount,
      confirmRevokeCertificate,
      disableAccount,
      disableSelectedAccounts,
      downloadConfig,
      downloadSelectedAccountConfig,
      enableAccount,
      enableLayer,
      enableUserDropdownVisible,
      enableUserKeyword,
      enableUserTree,
      formatDate,
      issueCertificate,
      issueSelectedAccountCertificate,
      isAllRowsSelected,
      loadAccounts,
      loading,
      openAssignServer,
      openEnableAccount,
      openEnableUserDropdown,
      openVpnPageEnd,
      openVpnPageSizeOptions,
      openVpnPageStart,
      openVpnPaginationTotal,
      pagination,
      renewAccountCertificate,
      renewSelectedCertificate,
      resetQuery,
      revokeAccount,
      revokeAccountLayer,
      revokeAccountCertificate,
      revokeCertificateLayer,
      revokeSelectedAccount,
      revokeSelectedCertificate,
      searchAccounts,
      selectedRow,
      selectedRowIds,
      selectedRows,
      selectEnableUser,
      servers,
      statusText,
      toggleAllRows,
      toggleRowSelection,
    }
  },
}
