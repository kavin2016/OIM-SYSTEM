<template>
  <div
    :class="[
      isAuthenticated ? 'app-shell' : 'guest-shell',
      { 'sidebar-collapsed': isAuthenticated && sidebarCollapsed },
    ]"
    :style="isAuthenticated ? { '--system-font-size': selectedFontSize.size } : null"
  >
    <aside v-if="isAuthenticated" class="sidebar">
      <div class="sidebar-brand">
        <img src="/logo.jpg" alt="OIM Logo" class="sidebar-logo" />
        <div class="sidebar-brand-text">
          <strong>OIM System</strong>
          <span>后台管理</span>
        </div>
        <button
          type="button"
          class="sidebar-toggle"
          :aria-label="sidebarCollapsed ? '展开主菜单' : '收起主菜单'"
          @click="toggleSidebar"
        >
          {{ sidebarCollapsed ? '›' : '‹' }}
        </button>
      </div>

      <nav class="sidebar-nav" aria-label="后台导航">
        <el-menu
          class="sidebar-el-menu"
          :default-active="route.path"
          :collapse="sidebarCollapsed"
          :collapse-transition="false"
          router
        >
          <el-menu-item index="/dashboard">
            <el-icon><component :is="iconFor('dashboard')" /></el-icon>
            <template #title>仪表盘</template>
          </el-menu-item>

          <template v-for="menu in menus" :key="menu.id">
            <el-menu-item v-if="menu.path && !menu.children?.length" :index="menu.path">
              <el-icon><component :is="iconFor(menu.icon)" /></el-icon>
              <template #title>{{ menu.name }}</template>
            </el-menu-item>
            <el-sub-menu v-else :index="menu.path || `menu-${menu.id}`">
              <template #title>
                <el-icon><component :is="iconFor(menu.icon)" /></el-icon>
                <span>{{ menu.name }}</span>
              </template>
              <el-menu-item
                v-for="child in menu.children"
                :key="child.id"
                :index="child.path || '/dashboard'"
              >
                <el-icon><component :is="iconFor(child.icon)" /></el-icon>
                <template #title>{{ child.name }}</template>
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </nav>
    </aside>

    <section v-if="isAuthenticated" class="main-shell">
      <header class="topbar">
        <div>
          <h1>{{ pageTitle }}</h1>
          <p>{{ pageSubtitle }}</p>
        </div>
        <div class="topbar-actions">
          <div class="font-size-control" @click.stop>
            <button
              type="button"
              class="font-size-trigger"
              :aria-expanded="fontSizeMenuVisible"
              aria-label="选择系统字体大小"
              @click="toggleFontSizeMenu"
            >
              <span class="font-size-icon" aria-hidden="true">A</span>
              <span>{{ selectedFontSize.shortLabel }}</span>
            </button>
            <div v-if="fontSizeMenuVisible" class="font-size-menu">
              <button
                v-for="option in fontSizeOptions"
                :key="option.key"
                type="button"
                class="font-size-option"
                :class="{ active: option.key === selectedFontSizeKey }"
                @click="selectFontSize(option.key)"
              >
                <span
                  class="font-size-option-icon"
                  :style="{ fontSize: option.iconSize }"
                  aria-hidden="true"
                >A</span>
                <span>{{ option.shortLabel }}</span>
              </button>
            </div>
          </div>
          <el-dropdown
            trigger="click"
            popper-class="user-menu-dropdown"
            @command="handleUserMenuCommand"
          >
            <button type="button" class="user-menu-trigger">
              <el-icon class="user-menu-avatar"><UserFilled /></el-icon>
              <span class="user-menu-text">
                <span>{{ user?.username || '未命名用户' }}</span>
                <small>{{ user?.is_admin ? '系统管理员' : '普通用户' }}</small>
              </span>
              <el-icon class="user-menu-arrow"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><UserFilled /></el-icon>
                  <span>个人资料</span>
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  <span>登出</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <div class="tabs-bar" @contextmenu.prevent>
        <button
          v-for="tab in tabs"
          :key="tab.fullPath"
          type="button"
          class="page-tab"
          :class="{ active: tab.fullPath === route.fullPath }"
          @click="goTab(tab)"
          @contextmenu.prevent="openTabMenu($event, tab)"
        >
          <el-icon class="tab-icon"><component :is="tabIconFor(tab)" /></el-icon>
          <span>{{ tab.title }}</span>
          <span
            v-if="!tab.fixed"
            class="tab-close"
            role="button"
            tabindex="0"
            @click.stop="closeTab(tab)"
            @keydown.enter.stop.prevent="closeTab(tab)"
          >×</span>
        </button>

        <div
          v-if="tabMenu.visible"
          class="tab-context-menu"
          :style="{ left: `${tabMenu.x}px`, top: `${tabMenu.y}px` }"
        >
          <button type="button" @click="refreshTab">刷新</button>
          <button type="button" @click="closeCurrentTab" :disabled="selectedTabIsFixed">关闭当前</button>
          <button type="button" @click="closeOtherTabs">关闭其他</button>
          <button type="button" @click="closeAllTabs">关闭所有</button>
        </div>
      </div>

      <main class="content-area">
        <Transition name="fade" mode="out-in">
          <router-view v-if="showAuthenticatedRoute" :key="contentViewKey" />
        </Transition>
      </main>
    </section>

    <Transition v-else name="fade" mode="out-in">
      <router-view :key="$route.path" />
    </Transition>

    <Transition name="fade">
      <div v-if="globalLoading" class="global-loading-layer" role="status" aria-live="polite">
        <div class="global-loading-box">
          <span class="global-loading-spinner" aria-hidden="true"></span>
          <span>加载中...</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, Transition, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  DataBoard,
  Briefcase,
  Connection,
  Link,
  Lock,
  Menu as MenuIcon,
  Monitor,
  OfficeBuilding,
  Setting,
  SwitchButton,
  User as UserIcon,
  UserFilled,
} from '@element-plus/icons-vue'
import { user, menus, isAuthenticated, logout } from './composables/useAuth.js'
import { globalLoading } from './composables/useGlobalLoading.js'

const route = useRoute()
const router = useRouter()
const tabs = ref([])
const refreshSeed = ref(0)
const selectedFontSizeKey = ref('small')
const fontSizeMenuVisible = ref(false)
const sidebarCollapsed = ref(false)
const inactivityTimer = ref(null)
const tabMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  fullPath: '',
})

const INACTIVITY_TIMEOUT = 30 * 60 * 1000
const activityEvents = ['click', 'keydown', 'mousemove', 'mousedown', 'scroll', 'touchstart', 'wheel']

const fontSizeOptions = [
  { key: 'large', label: '大号字体', shortLabel: '大号', size: '16px', iconSize: '19px' },
  { key: 'medium', label: '中号字体', shortLabel: '中号', size: '15px', iconSize: '17px' },
  { key: 'small', label: '小号字体', shortLabel: '小号', size: '12px', iconSize: '13px' },
  { key: 'extra-small', label: '极小号字体', shortLabel: '极小', size: '11px', iconSize: '12px' },
]

const pageMeta = {
  Dashboard: {
    title: '仪表盘',
    subtitle: '查看当前账号与系统概览',
  },
  Profile: {
    title: '个人资料',
    subtitle: '维护当前登录用户资料',
  },
  AdminUsers: {
    title: '用户管理',
    subtitle: '系统管理 / 用户信息维护',
  },
  AdminDepartments: {
    title: '部门管理',
    subtitle: '系统管理 / 部门信息维护',
  },
  AdminRoles: {
    title: '角色管理',
    subtitle: '系统管理 / 角色信息维护',
  },
}

const currentMeta = computed(() => {
  const staticMeta = pageMeta[route.name]
  return {
    title: route.meta.title || staticMeta?.title || '运营综合管理系统',
    subtitle: route.meta.subtitle || staticMeta?.subtitle || '',
  }
})
const pageTitle = computed(() => currentMeta.value.title)
const pageSubtitle = computed(() => currentMeta.value.subtitle)
const contentViewKey = computed(() => `${route.fullPath}:${refreshSeed.value}`)
const showAuthenticatedRoute = computed(() => !(isAuthenticated.value && route.meta.guest))
const selectedFontSize = computed(() => {
  return fontSizeOptions.find((option) => option.key === selectedFontSizeKey.value) || fontSizeOptions[2]
})
const selectedTabIsFixed = computed(() => {
  return tabs.value.some((tab) => tab.fullPath === tabMenu.fullPath && tab.fixed)
})
const iconMap = {
  settings: Setting,
  users: UserIcon,
  building: OfficeBuilding,
  shield: Lock,
  briefcase: Briefcase,
  link: Link,
  monitor: Monitor,
  connection: Connection,
  dashboard: DataBoard,
  profile: UserFilled,
}

function iconFor(icon) {
  return iconMap[icon] || MenuIcon
}

function titleForRoute(targetRoute) {
  const staticMeta = pageMeta[targetRoute.name]
  return targetRoute.meta.title || staticMeta?.title || '未命名页面'
}

function tabIconFor(tab) {
  if (tab.fullPath === '/dashboard') return DataBoard
  if (tab.fullPath.includes('/users') || tab.title.includes('用户')) return UserIcon
  if (tab.fullPath.includes('/roles') || tab.title.includes('角色')) return Lock
  if (tab.fullPath.includes('/departments') || tab.title.includes('部门')) return OfficeBuilding
  if (tab.fullPath.includes('/positions') || tab.title.includes('岗位')) return Briefcase
  if (tab.fullPath.includes('/domains') || tab.title.includes('域名')) return Link
  if (tab.fullPath.includes('/openvpn') || tab.title.includes('OpenVPN')) return Connection
  if (tab.title.includes('代码')) return Setting
  return MenuIcon
}

function canCreateTab(targetRoute) {
  return isAuthenticated.value && targetRoute.meta.requiresAuth && !targetRoute.meta.guest
}

function currentUserId() {
  return user.value?.id ?? user.value?.user_id ?? user.value?.username ?? ''
}

function storageKey(name) {
  const id = currentUserId()
  return id ? `oim:${id}:${name}` : ''
}

function readCachedValue(name, fallback) {
  const key = storageKey(name)
  if (!key) return fallback
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch (error) {
    return fallback
  }
}

function writeCachedValue(name, value) {
  const key = storageKey(name)
  if (!key) return
  localStorage.setItem(key, JSON.stringify(value))
}

function isKnownFontSizeKey(key) {
  return fontSizeOptions.some((option) => option.key === key)
}

function dashboardTab() {
  return {
    fullPath: '/dashboard',
    title: pageMeta.Dashboard.title,
    fixed: true,
  }
}

function ensureDashboardTab() {
  const exists = tabs.value.some((tab) => tab.fullPath === '/dashboard')
  if (!exists) {
    tabs.value = [dashboardTab(), ...tabs.value]
  } else {
    tabs.value = tabs.value.map((tab) => {
      if (tab.fullPath !== '/dashboard') return tab
      return {
        ...tab,
        title: pageMeta.Dashboard.title,
        fixed: true,
      }
    })
  }
}

function normalizeCachedTabs(cachedTabs) {
  if (!Array.isArray(cachedTabs)) return [dashboardTab()]

  const seen = new Set()
  const normalized = []
  cachedTabs.forEach((tab) => {
    if (!tab?.fullPath || seen.has(tab.fullPath)) return
    seen.add(tab.fullPath)
    normalized.push({
      fullPath: tab.fullPath,
      title: tab.fullPath === '/dashboard' ? pageMeta.Dashboard.title : tab.title || '未命名页面',
      fixed: tab.fullPath === '/dashboard' ? true : tab.fixed === true,
    })
  })

  const hasDashboard = normalized.some((tab) => tab.fullPath === '/dashboard')
  return hasDashboard ? normalized : [dashboardTab(), ...normalized]
}

async function restoreUserPreferences() {
  const fontSizeKey = readCachedValue('font-size', 'small')
  selectedFontSizeKey.value = isKnownFontSizeKey(fontSizeKey) ? fontSizeKey : 'small'
  sidebarCollapsed.value = readCachedValue('sidebar-collapsed', false) === true

  tabs.value = normalizeCachedTabs(readCachedValue('tabs', [dashboardTab()]))

  const cachedActivePath = readCachedValue('active-tab', '')
  const canRestorePath =
    cachedActivePath &&
    cachedActivePath !== route.fullPath &&
    tabs.value.some((tab) => tab.fullPath === cachedActivePath)

  if (canRestorePath) {
    try {
      await router.push(cachedActivePath)
    } catch (error) {
      await router.push('/dashboard')
    }
  } else {
    addCurrentTab()
  }
}

function addCurrentTab() {
  if (!canCreateTab(route)) return
  ensureDashboardTab()
  const exists = tabs.value.find((tab) => tab.fullPath === route.fullPath)
  if (exists) {
    exists.title = titleForRoute(route)
    if (exists.fullPath === '/dashboard') {
      exists.fixed = true
    }
    return
  }
  tabs.value.push({
    fullPath: route.fullPath,
    title: titleForRoute(route),
  })
}

function hideTabMenu() {
  tabMenu.visible = false
}

function hideFontSizeMenu() {
  fontSizeMenuVisible.value = false
}

function hideFloatingMenus() {
  hideTabMenu()
  hideFontSizeMenu()
}

function toggleFontSizeMenu() {
  hideTabMenu()
  fontSizeMenuVisible.value = !fontSizeMenuVisible.value
}

function selectFontSize(key) {
  if (isKnownFontSizeKey(key)) {
    selectedFontSizeKey.value = key
  }
  hideFontSizeMenu()
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  hideFloatingMenus()
}

async function handleUserMenuCommand(command) {
  hideFloatingMenus()
  if (command === 'profile') {
    if (route.fullPath !== '/profile') {
      await router.push('/profile')
    }
    return
  }
  if (command === 'logout') {
    await handleLogout()
  }
}

function openTabMenu(event, tab) {
  hideFontSizeMenu()
  tabMenu.visible = true
  tabMenu.fullPath = tab.fullPath
  tabMenu.x = Math.min(event.clientX, window.innerWidth - 150)
  tabMenu.y = Math.min(event.clientY, window.innerHeight - 160)
}

async function goTab(tab) {
  hideTabMenu()
  if (tab.fullPath !== route.fullPath) {
    await router.push(tab.fullPath)
  }
}

function selectFallbackPath(closedTab) {
  const currentIndex = tabs.value.findIndex((tab) => tab.fullPath === closedTab.fullPath)
  const nextTab = tabs.value[currentIndex + 1] || tabs.value[currentIndex - 1]
  return nextTab?.fullPath || '/dashboard'
}

async function closeTab(tab) {
  hideTabMenu()
  if (tab.fixed) {
    if (route.fullPath !== tab.fullPath) {
      await router.push(tab.fullPath)
    }
    return
  }

  const removableTabs = tabs.value.filter((item) => !item.fixed)
  if (removableTabs.length === 1) {
    tabs.value = [dashboardTab()]
    await router.push('/dashboard')
    return
  }

  const nextPath = selectFallbackPath(tab)
  tabs.value = tabs.value.filter((item) => item.fullPath !== tab.fullPath)
  ensureDashboardTab()
  if (tab.fullPath === route.fullPath) {
    await router.push(nextPath)
  }
}

async function refreshTab() {
  const targetPath = tabMenu.fullPath || route.fullPath
  hideTabMenu()
  if (targetPath !== route.fullPath) {
    await router.push(targetPath)
  }
  await nextTick()
  refreshSeed.value += 1
}

async function closeCurrentTab() {
  const target = tabs.value.find((tab) => tab.fullPath === (tabMenu.fullPath || route.fullPath))
  if (target) {
    await closeTab(target)
  } else {
    hideTabMenu()
  }
}

async function closeOtherTabs() {
  const targetPath = tabMenu.fullPath || route.fullPath
  const target = tabs.value.find((tab) => tab.fullPath === targetPath)
  hideTabMenu()
  if (!target) return
  tabs.value = target.fixed ? [dashboardTab()] : [dashboardTab(), target]
  if (route.fullPath !== target.fullPath) {
    await router.push(target.fullPath)
  }
}

async function closeAllTabs() {
  hideTabMenu()
  tabs.value = [dashboardTab()]
  if (route.fullPath !== '/dashboard') {
    await router.push('/dashboard')
  }
}

async function handleLogout() {
  hideFloatingMenus()
  clearInactivityTimer()
  logout()
  if (route.path !== '/login') {
    await router.replace('/login')
  }
}

function clearInactivityTimer() {
  if (inactivityTimer.value) {
    window.clearTimeout(inactivityTimer.value)
    inactivityTimer.value = null
  }
}

async function handleInactivityLogout() {
  clearInactivityTimer()
  if (!isAuthenticated.value) return
  logout()
  hideFloatingMenus()
  if (route.path !== '/login') {
    await router.replace('/login')
  }
}

function resetInactivityTimer() {
  if (!isAuthenticated.value) return
  clearInactivityTimer()
  inactivityTimer.value = window.setTimeout(handleInactivityLogout, INACTIVITY_TIMEOUT)
}

function startInactivityWatch() {
  activityEvents.forEach((eventName) => {
    window.addEventListener(eventName, resetInactivityTimer, { passive: true })
  })
  resetInactivityTimer()
}

function stopInactivityWatch() {
  activityEvents.forEach((eventName) => {
    window.removeEventListener(eventName, resetInactivityTimer)
  })
  clearInactivityTimer()
}

watch(selectedFontSizeKey, (value) => {
  if (!isAuthenticated.value || !currentUserId()) return
  writeCachedValue('font-size', isKnownFontSizeKey(value) ? value : 'small')
})

watch(sidebarCollapsed, (value) => {
  if (!isAuthenticated.value || !currentUserId()) return
  writeCachedValue('sidebar-collapsed', value === true)
})

watch(
  tabs,
  (value) => {
    if (!isAuthenticated.value || !currentUserId()) return
    writeCachedValue('tabs', value)
  },
  { deep: true },
)

watch(
  () => route.fullPath,
  () => {
    hideFloatingMenus()
    addCurrentTab()
    if (isAuthenticated.value && currentUserId() && canCreateTab(route)) {
      writeCachedValue('active-tab', route.fullPath)
    }
  },
  { immediate: true },
)

watch(
  () => user.value,
  async (currentUser) => {
    if (!currentUser) {
      tabs.value = []
      selectedFontSizeKey.value = 'small'
      sidebarCollapsed.value = false
      hideFloatingMenus()
      return
    }
    await restoreUserPreferences()
  },
  { immediate: true },
)

watch(isAuthenticated, (loggedIn) => {
  if (!loggedIn) {
    tabs.value = []
    hideFloatingMenus()
    stopInactivityWatch()
    return
  }
  startInactivityWatch()
})

onMounted(() => {
  window.addEventListener('click', hideFloatingMenus)
  if (isAuthenticated.value) {
    startInactivityWatch()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('click', hideFloatingMenus)
  stopInactivityWatch()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
