import '../../styles/components/resource-page.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { user } from '../../composables/useAuth.js'
import { actionIconMap } from './resourcePageConstants.js'
import { RESOURCE_CONFIG } from './resourcePageConfig.js'
import {
  buildDepartmentTree,
  buildPermissionTree,
  collectDescendantIds,
  displayContacts,
  flattenDepartmentRows,
  flattenPermissionRows,
  formatDate,
} from './resourcePageUtils.js'
import { createFormActions } from './resourcePage/formActions.js'
import { createOptionActions } from './resourcePage/options.js'
import { createPermissionActions } from './resourcePage/permissions.js'
import { createQueryActions } from './resourcePage/query.js'
import { createRolePermissionActions } from './resourcePage/rolePermissions.js'
import { createSelectionActions } from './resourcePage/selection.js'
import { createUserImportExportActions } from './resourcePage/userImportExport.js'
import { createUserRelationActions } from './resourcePage/userRelations.js'

export function createResourcePage(resourceKey) {
  return {
    setup() {
      const config = RESOURCE_CONFIG[resourceKey]
      const rows = ref([])
      const loading = ref(false)
      const saving = ref(false)
      const relationLoading = ref(false)
      const message = ref('')
      const editingId = ref(null)
      const originalParentId = ref(null)
      const formVisible = ref(false)
      const departmentOptions = ref([])
      const roleOptions = ref([])
      const positionOptions = ref([])
      const permissionOptions = ref([])
      const departmentOrgTreeRef = ref(null)
      const departmentFilterText = ref('')
      const rolePermissionTreeRef = ref(null)
      const rolePermissionExpanded = ref(true)
      const rolePermissionCheckAll = ref(false)
      const rolePermissionLinkParents = ref(true)
      const selectedRowIds = ref([])
      const importFileInput = ref(null)
      const includeDisabled = ref(false)
      const includeDeleted = ref(false)
      const queryAdvancedVisible = ref(false)
      const passwordLayer = reactive({
        visible: false,
        userId: null,
        username: '',
        password: '',
        confirmPassword: '',
      })
      const roleLayer = reactive({
        visible: false,
        userId: null,
        username: '',
        roleIds: [],
      })
      const relationPanel = reactive({
        visible: false,
        title: '',
        type: '',
        rows: [],
      })
      const form = reactive(config.emptyForm())
      const queryForm = reactive({
        name: '',
        code: '',
        nickname: '',
        username: '',
        status: '',
        deletedStatus: '',
        departmentId: '',
        roleId: '',
        createdAtStart: '',
        createdAtEnd: '',
      })

      const { canOperate, hasPermission } = createPermissionActions(resourceKey)
      const isAdmin = computed(() => user.value?.is_admin === true)
      const isEditing = computed(() => editingId.value !== null)
      const canAccessPage = computed(() => canOperate('list'))
      const isPageLoading = computed(() => false)
      const selectableRows = computed(() =>
        rows.value.filter((row) => !row.is_deleted && !(resourceKey === 'users' && row.username === 'admin')),
      )
      const selectedRows = computed(() =>
        selectableRows.value.filter((row) => selectedRowIds.value.includes(row.id)),
      )
      const selectedRow = computed(() => selectedRows.value[0] || null)
      const departmentNameMap = computed(() => {
        return new Map(departmentOptions.value.map((department) => [department.id, department.name]))
      })
      const departmentTreeOptions = computed(() => buildDepartmentTree(departmentOptions.value))
      const permissionTreeOptions = computed(() => buildPermissionTree(permissionOptions.value))
      const parentDepartmentTreeOptions = computed(() => {
        const excludedIds = collectDescendantIds(departmentOptions.value, editingId.value)
        if (editingId.value) excludedIds.add(editingId.value)
        return buildDepartmentTree(departmentOptions.value, excludedIds)
      })
      const departmentDisplayRows = computed(() => flattenDepartmentRows(rows.value))
      const relationDisplayRows = computed(() =>
        relationPanel.type === 'permissions' ? flattenPermissionRows(relationPanel.rows) : relationPanel.rows,
      )
      const activeQueryCount = computed(() => {
        const values =
          resourceKey === 'users'
            ? [
                queryForm.nickname.trim(),
                queryForm.username.trim(),
                queryForm.status,
                queryForm.departmentId,
                queryForm.roleId,
                queryForm.createdAtStart,
                queryForm.createdAtEnd,
              ]
            : [
                queryForm.name.trim(),
                queryForm.code.trim(),
                queryForm.status,
                queryForm.deletedStatus,
              ]
        return values.filter((value) => value !== '' && value !== false && value !== null && value !== undefined).length
      })
      const isAllRowsSelected = computed(
        () => selectableRows.value.length > 0 && selectedRows.value.length === selectableRows.value.length,
      )
      const loadingText = computed(() => {
        if (saving.value) return '保存中...'
        if (relationLoading.value) return '查询关联数据...'
        return '加载数据...'
      })

      const ctx = {
        apiKey: config.apiKey,
        canAccessPage,
        canOperate,
        config,
        departmentFilterText,
        departmentNameMap,
        departmentOptions,
        departmentOrgTreeRef,
        editingId,
        form,
        formVisible,
        importFileInput,
        includeDeleted,
        message,
        originalParentId,
        passwordLayer,
        permissionOptions,
        permissionTreeOptions,
        positionOptions,
        queryAdvancedVisible,
        queryForm,
        relationLoading,
        relationPanel,
        resourceKey,
        roleLayer,
        roleOptions,
        rolePermissionCheckAll,
        rolePermissionExpanded,
        rolePermissionLinkParents,
        rolePermissionTreeRef,
        rows,
        saving,
        selectableRows,
        selectedRowIds,
        selectedRows,
        loading,
      }

      const relationActions = createUserRelationActions(ctx, {
        loadFormOptions: (...args) => optionActions.loadFormOptions(...args),
      })
      ctx.closeRelationPanel = relationActions.closeRelationPanel
      const queryActions = createQueryActions(ctx)
      const optionActions = createOptionActions({
        ...ctx,
        filterDepartmentTree: queryActions.filterDepartmentTree,
      })
      const rolePermissionActions = createRolePermissionActions(ctx)
      const formActions = createFormActions(ctx, {
        loadFormOptions: optionActions.loadFormOptions,
        syncRolePermissionTree: rolePermissionActions.syncRolePermissionTree,
        upsertRows: queryActions.upsertRows,
      })
      const selectionActions = createSelectionActions(ctx, {
        cancelForm: formActions.cancelForm,
        editRow: formActions.editRow,
        loadFormOptions: optionActions.loadFormOptions,
        upsertRows: queryActions.upsertRows,
      })
      const importExportActions = createUserImportExportActions(ctx, {
        loadRows: queryActions.loadRows,
      })

      onMounted(() => {
        queryActions.loadRows()
        optionActions.loadFormOptions()
      })

      return {
        actionIconMap,
        activeQueryCount,
        canAccessPage,
        canOperate,
        departmentDisplayRows,
        departmentFilterText,
        departmentOrgTreeRef,
        departmentOptions,
        parentDepartmentTreeOptions,
        departmentTreeOptions,
        entityName: config.entityName,
        form,
        formVisible,
        displayContacts,
        formatDate,
        hasPermission,
        importFileInput,
        includeDeleted,
        includeDisabled,
        isAdmin,
        isAllRowsSelected,
        isEditing,
        isPageLoading,
        loading,
        loadingText,
        message,
        passwordLayer,
        permissionTreeOptions,
        queryForm,
        queryAdvancedVisible,
        relationLoading,
        relationPanel,
        relationDisplayRows,
        roleLayer,
        roleOptions,
        positionOptions,
        rolePermissionCheckAll,
        rolePermissionExpanded,
        rolePermissionLinkParents,
        rolePermissionTreeRef,
        rows,
        saving,
        selectableRows,
        selectedRowIds,
        selectedRow,
        selectedRows,
        subtitle: config.subtitle,
        title: config.title,
        ...formActions,
        ...importExportActions,
        ...optionActions,
        ...queryActions,
        ...relationActions,
        ...rolePermissionActions,
        ...selectionActions,
      }
    },
  }
}
