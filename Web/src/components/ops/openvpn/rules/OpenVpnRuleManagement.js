import '../../../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { token, hasPermission } from '../../../../composables/useAuth.js'
import { adminAPI } from '../../../../api/admin.js'
import { openvpnAPI } from '../../../../api/openvpn.js'
import { actionIconMap } from '../../../system/resourcePageConstants.js'
import {
  asOpenVpnArray,
  emptyOpenVpnPagination,
  emptyOpenVpnRuleForm,
  openVpnPageEnd,
  openVpnPageParams,
  openVpnPageSizeOptions,
  openVpnPageStart,
  openVpnPaginationTotal,
  resetOpenVpnReactive,
  resetOpenVpnPagination,
  sliceOpenVpnPageRows,
} from '../shared/openVpnConfig.js'

export default {
  setup() {
    const loading = ref(false)
    const servers = ref([])
    const rules = ref([])
    const users = ref([])
    const departments = ref([])
    const roles = ref([])
    const positions = ref([])
    const selectedRowIds = ref([])
    const ruleDialogVisible = ref(false)
    const editingRuleId = ref(null)
    const ruleQuery = reactive({ target_type: '', server_id: '' })
    const pagination = reactive(emptyOpenVpnPagination())
    const ruleForm = reactive(emptyOpenVpnRuleForm())

    const selectedRows = computed(() => rules.value.filter((row) => selectedRowIds.value.includes(row.id)))
    const selectedRow = computed(() => selectedRows.value[0] || null)
    const isAllRowsSelected = computed(
      () => rules.value.length > 0 && selectedRows.value.length === rules.value.length,
    )
    const targetOptions = computed(() => {
      if (ruleForm.target_type === 'user') return users.value.map((item) => ({ id: item.id, name: `${item.username}${item.nickname ? ` / ${item.nickname}` : ''}` }))
      if (ruleForm.target_type === 'role') return roles.value.map((item) => ({ id: item.id, name: item.name }))
      if (ruleForm.target_type === 'position') return positions.value.map((item) => ({ id: item.id, name: item.name }))
      return departments.value.map((item) => ({ id: item.id, name: item.name }))
    })
    const can = (permission) => hasPermission(permission)

    function serverName(id) {
      return servers.value.find((item) => item.id === id)?.name || '-'
    }

    async function loadServers() {
      servers.value = asOpenVpnArray(await openvpnAPI.listServers(token.value, { include_disabled: true }))
    }

    async function loadRules() {
      loading.value = true
      try {
        const rows = await openvpnAPI.listRules(token.value, { ...ruleQuery, ...openVpnPageParams(pagination) })
        rules.value = sliceOpenVpnPageRows(rows, pagination)
        selectedRowIds.value = selectedRowIds.value.filter((id) => rules.value.some((row) => row.id === id))
      } finally {
        loading.value = false
      }
    }

    async function loadOpenVpnOptions() {
      const options = await openvpnAPI.listOptions(token.value) || {}
      users.value = asOpenVpnArray(options.users)
      departments.value = asOpenVpnArray(options.departments)
      roles.value = asOpenVpnArray(options.roles)
      positions.value = asOpenVpnArray(options.positions)
    }

    async function loadSystemUserOptions() {
      const [systemUsers, systemDepartments] = await Promise.all([
        adminAPI.users.list(token.value, { limit: 1000, includeDisabled: false, includeDeleted: false }),
        adminAPI.departments.list(token.value, { limit: 1000, includeDisabled: true, includeDeleted: false }),
      ])
      const [systemRolesResult, systemPositionsResult] = await Promise.allSettled([
        adminAPI.roles.list(token.value, { limit: 1000, includeDisabled: true, includeDeleted: false }),
        adminAPI.positions.list(token.value, { limit: 1000, includeDisabled: true, includeDeleted: false }),
      ])
      users.value = asOpenVpnArray(systemUsers).map((user) => ({
        id: user.id,
        username: user.username,
        nickname: user.nickname,
      }))
      departments.value = asOpenVpnArray(systemDepartments).map((department) => ({
        id: department.id,
        name: department.name,
      }))
      if (systemRolesResult.status === 'fulfilled') roles.value = asOpenVpnArray(systemRolesResult.value)
      if (systemPositionsResult.status === 'fulfilled') positions.value = asOpenVpnArray(systemPositionsResult.value)
    }

    async function loadOptions() {
      try {
        await loadSystemUserOptions()
      } catch (error) {
        await loadOpenVpnOptions()
      }
    }

    function resetQuery() {
      resetOpenVpnReactive(ruleQuery, { target_type: '', server_id: '' })
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadRules()
    }

    function searchRules() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadRules()
    }

    function changePageSize() {
      resetOpenVpnPagination(pagination)
      selectedRowIds.value = []
      loadRules()
    }

    function changePage(page) {
      pagination.page = page
      selectedRowIds.value = []
      loadRules()
    }

    function toggleRowSelection(row) {
      if (selectedRowIds.value.includes(row.id)) {
        selectedRowIds.value = selectedRowIds.value.filter((id) => id !== row.id)
        return
      }
      selectedRowIds.value = [...selectedRowIds.value, row.id]
    }

    function toggleAllRows() {
      selectedRowIds.value = isAllRowsSelected.value ? [] : rules.value.map((row) => row.id)
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

    async function openCreateRule() {
      editingRuleId.value = null
      resetOpenVpnReactive(ruleForm, emptyOpenVpnRuleForm())
      try {
        await loadOptions()
      } catch (error) {
        ElMessage.error(error.message || '选项数据加载失败')
      }
      ruleDialogVisible.value = true
    }

    async function openEditRule(row) {
      editingRuleId.value = row.id
      resetOpenVpnReactive(ruleForm, { ...emptyOpenVpnRuleForm(), ...row })
      try {
        await loadOptions()
      } catch (error) {
        ElMessage.error(error.message || '选项数据加载失败')
      }
      ruleDialogVisible.value = true
    }

    function editSelectedRule() {
      const row = requireSingleSelection('修改')
      if (row) openEditRule(row)
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

    async function deleteSelectedRules() {
      const rows = requireAnySelection('删除')
      if (rows.length === 0) return
      await ElMessageBox.confirm(`确认删除选中的 ${rows.length} 条分配规则？`, '删除确认', { type: 'warning' })
      await Promise.all(rows.map((row) => openvpnAPI.deleteRule(token.value, row.id)))
      selectedRowIds.value = []
      ElMessage.success('分配规则已删除')
      await loadRules()
    }

    onMounted(async () => {
      await Promise.all([loadServers(), loadRules()])
    })

    return {
      actionIconMap,
      can,
      changePage,
      changePageSize,
      deleteRule,
      deleteSelectedRules,
      editingRuleId,
      editSelectedRule,
      isAllRowsSelected,
      loadRules,
      loading,
      openCreateRule,
      openEditRule,
      openVpnPageEnd,
      openVpnPageSizeOptions,
      openVpnPageStart,
      openVpnPaginationTotal,
      pagination,
      resetQuery,
      ruleDialogVisible,
      ruleForm,
      ruleQuery,
      rules,
      saveRule,
      searchRules,
      selectedRowIds,
      selectedRows,
      serverName,
      servers,
      targetOptions,
      toggleAllRows,
      toggleRowSelection,
    }
  },
}
