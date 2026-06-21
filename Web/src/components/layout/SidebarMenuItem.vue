<template>
  <el-menu-item v-if="menu.path && !menu.children?.length" :index="menu.path">
    <el-icon><component :is="iconFor(menu.icon)" /></el-icon>
    <template #title>{{ menu.name }}</template>
  </el-menu-item>
  <el-sub-menu v-else :index="menu.path || `menu-${menu.id}`">
    <template #title>
      <el-icon><component :is="iconFor(menu.icon)" /></el-icon>
      <span>{{ menu.name }}</span>
    </template>
    <SidebarMenuItem
      v-for="child in menu.children"
      :key="child.id"
      :menu="child"
      :icon-for="iconFor"
    />
  </el-sub-menu>
</template>

<script>
export default {
  name: 'SidebarMenuItem',
  props: {
    menu: { type: Object, required: true },
    iconFor: { type: Function, required: true },
  },
}
</script>
