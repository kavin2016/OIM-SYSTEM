import { formatContacts, normalizeIdList, parseContacts } from './resourcePageUtils.js'

export const RESOURCE_CONFIG = {
  users: {
    title: '用户管理',
    subtitle: '系统管理 / 用户信息维护',
    entityName: '用户',
    apiKey: 'users',
    emptyForm: () => ({
      username: '',
      nickname: '',
      gender: '',
      email: '',
      phone: '',
      position: '',
      position_ids: [],
      remark: '',
      contacts_text: '',
      password: '',
      is_admin: false,
      is_active: true,
      department_id: null,
      role_id: null,
    }),
    toPayload(form, editing) {
      const payload = {
        username: form.username.trim(),
        nickname: form.nickname.trim() || null,
        gender: form.gender || null,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        position: form.position.trim() || null,
        remark: form.remark.trim() || null,
        contacts: parseContacts(form.contacts_text),
        is_admin: form.is_admin,
        is_active: form.is_active,
      }
      if (!editing || form.password) {
        payload.password = form.password
      }
      payload.department_ids = normalizeIdList(form.department_id ? [form.department_id] : [])
      payload.role_ids = normalizeIdList(form.role_id ? [form.role_id] : [])
      payload.position_ids = normalizeIdList(form.position_ids)
      return payload
    },
    fillForm(form, row) {
      Object.assign(form, {
        username: row.username || '',
        nickname: row.nickname || '',
        gender: row.gender || '',
        email: row.email || '',
        phone: row.phone || '',
        position: row.position || '',
        position_ids: [],
        remark: row.remark || '',
        contacts_text: formatContacts(row.contacts),
        password: '',
        is_admin: row.is_admin === true,
        is_active: row.is_active === true,
        department_id: null,
        role_id: null,
      })
    },
  },
  departments: {
    title: '部门管理',
    subtitle: '系统管理 / 部门信息维护',
    entityName: '部门',
    apiKey: 'departments',
    emptyForm: () => ({
      name: '',
      code: '',
      parent_id: '',
      description: '',
      is_active: true,
      is_deleted: false,
    }),
    toPayload(form, editing) {
      const payload = {
        name: form.name.trim(),
        code: form.code.trim(),
        parent_id: form.parent_id || null,
        description: form.description.trim() || null,
        is_active: form.is_active,
      }
      if (editing) {
        payload.is_deleted = form.is_deleted === true
      }
      return payload
    },
    fillForm(form, row) {
      Object.assign(form, {
        name: row.name || '',
        code: row.code || '',
        parent_id: row.parent_id || '',
        description: row.description || '',
        is_active: row.is_active === true,
        is_deleted: row.is_deleted === true,
      })
    },
  },
  roles: {
    title: '角色管理',
    subtitle: '系统管理 / 角色信息维护',
    entityName: '角色',
    apiKey: 'roles',
    emptyForm: () => ({
      name: '',
      code: '',
      sort_order: 0,
      description: '',
      is_active: true,
      permission_ids: [],
    }),
    toPayload(form) {
      return {
        name: form.name.trim(),
        code: form.code.trim(),
        sort_order: Number(form.sort_order) || 0,
        description: form.description.trim() || null,
        is_active: form.is_active,
        permission_ids: normalizeIdList(form.permission_ids),
      }
    },
    fillForm(form, row) {
      Object.assign(form, {
        name: row.name || '',
        code: row.code || '',
        sort_order: Number(row.sort_order) || 0,
        description: row.description || '',
        is_active: row.is_active === true,
        permission_ids: [],
      })
    },
  },
  positions: {
    title: '岗位管理',
    subtitle: '系统管理 / 岗位信息维护',
    entityName: '岗位',
    apiKey: 'positions',
    emptyForm: () => ({
      code: '',
      name: '',
      sort_order: 0,
      status: 0,
      is_deleted: false,
      remark: '',
    }),
    toPayload(form, editing) {
      const payload = {
        code: form.code.trim(),
        name: form.name.trim(),
        sort_order: Number(form.sort_order) || 0,
        status: Number(form.status) === 1 ? 1 : 0,
        remark: form.remark.trim() || null,
      }
      if (editing) {
        payload.is_deleted = form.is_deleted === true
      }
      return payload
    },
    fillForm(form, row) {
      Object.assign(form, {
        code: row.code || '',
        name: row.name || '',
        sort_order: Number(row.sort_order) || 0,
        status: Number(row.status) === 1 ? 1 : 0,
        is_deleted: row.is_deleted === true,
        remark: row.remark || '',
      })
    },
  },
  domains: {
    title: '域名管理',
    subtitle: '系统管理 / 域名信息维护',
    entityName: '域名',
    apiKey: 'domains',
    emptyForm: () => ({
      code: '',
      name: '',
      registrar: '',
      expiry_date: '',
      sort_order: 0,
      status: 0,
      is_deleted: false,
      remark: '',
    }),
    toPayload(form, editing) {
      const payload = {
        code: form.code.trim(),
        name: form.name.trim(),
        registrar: form.registrar.trim() || null,
        expiry_date: form.expiry_date || null,
        sort_order: Number(form.sort_order) || 0,
        status: Number(form.status) === 1 ? 1 : 0,
        remark: form.remark.trim() || null,
      }
      if (editing) {
        payload.is_deleted = form.is_deleted === true
      }
      return payload
    },
    fillForm(form, row) {
      Object.assign(form, {
        code: row.code || '',
        name: row.name || '',
        registrar: row.registrar || '',
        expiry_date: row.expiry_date || '',
        sort_order: Number(row.sort_order) || 0,
        status: Number(row.status) === 1 ? 1 : 0,
        is_deleted: row.is_deleted === true,
        remark: row.remark || '',
      })
    },
  },
}
