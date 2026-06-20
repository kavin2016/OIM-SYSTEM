export function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

export function parseContacts(value) {
  return String(value || '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function formatContacts(value) {
  return Array.isArray(value) ? value.filter(Boolean).join('\n') : ''
}

export function displayContacts(value) {
  const contacts = Array.isArray(value) ? value.filter(Boolean) : []
  return contacts.length ? contacts.join('、') : '-'
}

export function normalizeIdList(value) {
  return (Array.isArray(value) ? value : [])
    .map((item) => Number(item))
    .filter((item) => Number.isInteger(item) && item > 0)
}

export function buildDepartmentTree(departments = [], excludedIds = new Set()) {
  const nodeMap = new Map()
  departments
    .filter((department) => !excludedIds.has(department.id))
    .forEach((department) => {
      nodeMap.set(department.id, {
        value: department.id,
        label: `${department.name}${department.code ? `（${department.code}）` : ''}`,
        children: [],
      })
    })

  const roots = []
  departments.forEach((department) => {
    const node = nodeMap.get(department.id)
    if (!node) return
    const parent = department.parent_id ? nodeMap.get(department.parent_id) : null
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
}

export function buildPermissionTree(permissions = []) {
  const nodeMap = new Map()
  const sortedPermissions = [...permissions].sort((left, right) => {
    const sortResult = (Number(left.sort_order) || 0) - (Number(right.sort_order) || 0)
    return sortResult === 0 ? left.id - right.id : sortResult
  })
  sortedPermissions.forEach((permission) => {
    nodeMap.set(permission.id, {
      value: permission.id,
      label: permission.name || permission.code,
      type: permission.type,
      children: [],
    })
  })

  const roots = []
  sortedPermissions.forEach((permission) => {
    const node = nodeMap.get(permission.id)
    if (!node) return
    const parent = permission.parent_id ? nodeMap.get(permission.parent_id) : null
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
}

export function collectTreeValues(nodes = []) {
  const values = []
  const appendValues = (items) => {
    items.forEach((item) => {
      values.push(item.value)
      if (item.children?.length) appendValues(item.children)
    })
  }
  appendValues(nodes)
  return values
}

export function collectDescendantIds(departments = [], departmentId = null) {
  if (!departmentId) return new Set()
  const descendantIds = new Set()
  const pendingIds = [departmentId]
  while (pendingIds.length > 0) {
    const currentId = pendingIds.shift()
    departments
      .filter((department) => department.parent_id === currentId)
      .forEach((department) => {
        if (!descendantIds.has(department.id)) {
          descendantIds.add(department.id)
          pendingIds.push(department.id)
        }
      })
  }
  return descendantIds
}

export function flattenDepartmentRows(departments = []) {
  const nodeMap = new Map()
  const orderMap = new Map()
  departments.forEach((department, index) => {
    nodeMap.set(department.id, { item: department, children: [] })
    orderMap.set(department.id, index)
  })

  const roots = []
  departments.forEach((department) => {
    const node = nodeMap.get(department.id)
    const parent = department.parent_id ? nodeMap.get(department.parent_id) : null
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  })

  const sortNodes = (items) => {
    items.sort((left, right) => (orderMap.get(left.item.id) ?? 0) - (orderMap.get(right.item.id) ?? 0))
    items.forEach((item) => sortNodes(item.children))
  }
  sortNodes(roots)

  const flattened = []
  const appendNode = (node, depth) => {
    flattened.push({
      ...node.item,
      treeDepth: depth,
    })
    node.children.forEach((child) => appendNode(child, depth + 1))
  }
  roots.forEach((node) => appendNode(node, 0))
  return flattened
}

export function flattenPermissionRows(permissions = []) {
  const nodeMap = new Map()
  permissions.forEach((permission) => {
    nodeMap.set(permission.id, { item: permission, children: [] })
  })

  const roots = []
  permissions.forEach((permission) => {
    const node = nodeMap.get(permission.id)
    const parent = permission.parent_id ? nodeMap.get(permission.parent_id) : null
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  })

  const sortNodes = (items) => {
    items.sort((left, right) => {
      const sortResult = (Number(left.item.sort_order) || 0) - (Number(right.item.sort_order) || 0)
      return sortResult === 0 ? left.item.id - right.item.id : sortResult
    })
    items.forEach((item) => sortNodes(item.children))
  }
  sortNodes(roots)

  const flattened = []
  const appendNode = (node, depth) => {
    flattened.push({
      ...node.item,
      treeDepth: depth,
    })
    node.children.forEach((child) => appendNode(child, depth + 1))
  }
  roots.forEach((node) => appendNode(node, 0))
  return flattened
}
