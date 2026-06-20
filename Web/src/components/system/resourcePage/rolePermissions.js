import { nextTick } from 'vue'
import { collectTreeValues, normalizeIdList } from '../resourcePageUtils.js'

export function createRolePermissionActions(ctx) {
  const {
    form,
    permissionTreeOptions,
    resourceKey,
    rolePermissionCheckAll,
    rolePermissionExpanded,
    rolePermissionLinkParents,
    rolePermissionTreeRef,
  } = ctx

  async function syncRolePermissionTree() {
    if (resourceKey !== 'roles') return
    await nextTick()
    const tree = rolePermissionTreeRef.value
    if (!tree?.setCheckedKeys) return
    tree.setCheckedKeys(normalizeIdList(form.permission_ids))
    setRolePermissionExpanded(rolePermissionExpanded.value)
    updateRolePermissionCheckAll()
  }

  function updateRolePermissionCheckAll() {
    const selectedIds = normalizeIdList(form.permission_ids)
    const allIds = collectTreeValues(permissionTreeOptions.value)
    rolePermissionCheckAll.value = allIds.length > 0 && allIds.every((id) => selectedIds.includes(id))
  }

  function handleRolePermissionCheck(_node, checkedState) {
    form.permission_ids = normalizeIdList(checkedState.checkedKeys)
    updateRolePermissionCheckAll()
  }

  function toggleRolePermissionCheckAll() {
    const checkedIds = rolePermissionCheckAll.value ? collectTreeValues(permissionTreeOptions.value) : []
    form.permission_ids = checkedIds
    if (rolePermissionTreeRef.value?.setCheckedKeys) {
      rolePermissionTreeRef.value.setCheckedKeys(checkedIds)
    }
  }

  function setRolePermissionExpanded(expanded = rolePermissionExpanded.value) {
    rolePermissionExpanded.value = expanded
    const nodesMap = rolePermissionTreeRef.value?.store?.nodesMap
    if (!nodesMap) return
    Object.values(nodesMap).forEach((node) => {
      node.expanded = expanded
    })
  }

  async function toggleRolePermissionLinkParents() {
    await syncRolePermissionTree()
  }

  return {
    handleRolePermissionCheck,
    setRolePermissionExpanded,
    syncRolePermissionTree,
    toggleRolePermissionCheckAll,
    toggleRolePermissionLinkParents,
    updateRolePermissionCheckAll,
  }
}
