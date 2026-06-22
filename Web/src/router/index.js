import { createRouter, createWebHistory } from 'vue-router'
import { token, user, menus, getMe } from '../composables/useAuth.js'

const componentMap = {
  AttendanceApprovalList: () => import('../components/attendance/modules/approvals/AttendanceApprovalList.vue'),
  AttendanceDailyReport: () => import('../components/attendance/modules/dailyReports/AttendanceDailyReport.vue'),
  AttendanceMonthlyReport: () => import('../components/attendance/modules/monthlyReports/AttendanceMonthlyReport.vue'),
  AttendanceRecordList: () => import('../components/attendance/modules/records/AttendanceRecordList.vue'),
  AttendanceRequestList: () => import('../components/attendance/modules/requests/AttendanceRequestList.vue'),
  AttendanceRestRuleList: () => import('../components/attendance/modules/restRules/AttendanceRestRuleList.vue'),
  AttendanceScheduleCalendar: () => import('../components/attendance/modules/schedules/AttendanceScheduleCalendar.vue'),
  AttendanceShiftList: () => import('../components/attendance/modules/shifts/AttendanceShiftList.vue'),
  UserList: () => import('../components/system/user/UserList.vue'),
  DepartmentList: () => import('../components/system/department/DepartmentList.vue'),
  RoleList: () => import('../components/system/role/RoleList.vue'),
  PositionList: () => import('../components/system/position/PositionList.vue'),
  DomainList: () => import('../components/system/domain/DomainList.vue'),
  OpenVpnManagement: () => import('../components/ops/openvpn/OpenVpnManagement.vue'),
  OpenVpnServerManagement: () => import('../components/ops/openvpn/servers/OpenVpnServerManagement.vue'),
  OpenVpnAccountManagement: () => import('../components/ops/openvpn/accounts/OpenVpnAccountManagement.vue'),
  OpenVpnSessionManagement: () => import('../components/ops/openvpn/sessions/OpenVpnSessionManagement.vue'),
  OpenVpnLogManagement: () => import('../components/ops/openvpn/logs/OpenVpnLogManagement.vue'),
  OpenVpnRuleManagement: () => import('../components/ops/openvpn/rules/OpenVpnRuleManagement.vue'),
  OpenVpnTrafficManagement: () => import('../components/ops/openvpn/traffic/OpenVpnTrafficManagement.vue'),
  OperationLogManagement: () => import('../components/ops/operationLogs/OperationLogManagement.vue'),
  LoginLogManagement: () => import('../components/ops/loginLogs/LoginLogManagement.vue'),
}

function routeNameFromCode(code) {
  return code
    .split(':')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('')
}

function resourceFromPath(path) {
  return path?.split('/').filter(Boolean).at(-1) || ''
}

function flattenMenus(items = []) {
  return items.flatMap((item) => [item, ...flattenMenus(item.children || [])])
}

function firstMenuPath(items = []) {
  for (const item of items) {
    if (item.path && item.children?.length) {
      const childPath = firstMenuPath(item.children)
      if (childPath) return childPath
    }
    if (item.path) return item.path
  }
  return '/dashboard'
}

function registerMenuRoutes(menuItems = []) {
  const flatMenus = flattenMenus(menuItems)
  const rootMenus = menuItems.filter((item) => item.path && item.children?.length)
  let added = false

  rootMenus.forEach((menu) => {
    const name = routeNameFromCode(menu.code)
    if (router.hasRoute(name)) return
    router.addRoute({
      path: menu.path,
      name,
      redirect: firstMenuPath(menu.children),
      meta: {
        requiresAuth: true,
        requiresAdmin: true,
        title: menu.name,
        subtitle: '数据库菜单',
      },
    })
    added = true
  })

  flatMenus
    .filter((menu) => menu.path && !menu.children?.length)
    .forEach((menu) => {
      const name = routeNameFromCode(menu.code)
      if (router.hasRoute(name)) return
      router.addRoute({
        path: menu.path,
        name,
        component: componentMap[menu.component] || componentMap.UserList,
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          resource: resourceFromPath(menu.path),
          title: menu.name,
          subtitle: `系统管理 / ${menu.name}`,
        },
      })
      added = true
    })

  return added
}

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../components/auth/LoginForm.vue'),
    meta: { guest: true },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../components/dashboard/DashboardHome.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../components/user/ProfilePage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/ops/openvpn',
    redirect: '/ops/openvpn/servers',
    meta: { requiresAuth: true },
  },
  {
    path: '/401',
    name: 'Error401',
    component: () => import('../components/errors/Error401.vue'),
  },
  {
    path: '/403',
    name: 'Error403',
    component: () => import('../components/errors/Error403.vue'),
  },
  {
    path: '/404',
    name: 'Error404',
    component: () => import('../components/errors/Error404.vue'),
  },
  {
    path: '/',
    redirect: () => {
      return token.value ? '/dashboard' : '/login'
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const requestedPath = to.redirectedFrom?.path || to.path

  if (token.value && !user.value) {
    try {
      await getMe()
      const addedRoutes = registerMenuRoutes(menus.value)
      if (to.name === 'Error404' && to.redirectedFrom?.path) {
        return next({ path: to.redirectedFrom.path, replace: true })
      }
      if (addedRoutes && (requestedPath.startsWith('/admin') || requestedPath.startsWith('/ops'))) {
        return next({ path: requestedPath, replace: true })
      }
    } catch (error) {
      // token 可能无效，getMe 已清理
    }
  } else if (token.value && menus.value.length > 0) {
    registerMenuRoutes(menus.value)
  }

  if (!token.value && (requestedPath.startsWith('/admin') || requestedPath.startsWith('/ops'))) {
    return next('/401')
  }

  if (to.meta.requiresAuth && !token.value) {
    return next('/401')
  }

  if (to.meta.requiresAdmin && token.value && !user.value?.is_admin) {
    return next('/403')
  }

  if (to.meta.guest && token.value) {
    return next('/dashboard')
  }

  return next()
})

export default router
