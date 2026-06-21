import { createApp } from 'vue'
import {
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElIcon,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElPagination,
  ElSelect,
  ElSubMenu,
  ElTree,
  ElTreeSelect,
} from 'element-plus'
import 'element-plus/theme-chalk/el-popper.css'
import 'element-plus/theme-chalk/el-dropdown.css'
import 'element-plus/theme-chalk/el-dropdown-menu.css'
import 'element-plus/theme-chalk/el-dropdown-item.css'
import 'element-plus/theme-chalk/el-icon.css'
import 'element-plus/theme-chalk/el-menu.css'
import 'element-plus/theme-chalk/el-menu-item.css'
import 'element-plus/theme-chalk/el-option.css'
import 'element-plus/theme-chalk/el-pagination.css'
import 'element-plus/theme-chalk/el-select.css'
import 'element-plus/theme-chalk/el-sub-menu.css'
import 'element-plus/theme-chalk/el-tree.css'
import 'element-plus/theme-chalk/el-tree-select.css'
import App from './App.vue'
import router from './router/index.js'
import './styles/base.css'
import './styles/layout.css'

createApp(App)
  .use(router)
  .component('ElDropdown', ElDropdown)
  .component('ElDropdownItem', ElDropdownItem)
  .component('ElDropdownMenu', ElDropdownMenu)
  .component('ElIcon', ElIcon)
  .component('ElMenu', ElMenu)
  .component('ElMenuItem', ElMenuItem)
  .component('ElOption', ElOption)
  .component('ElPagination', ElPagination)
  .component('ElSelect', ElSelect)
  .component('ElSubMenu', ElSubMenu)
  .component('ElTree', ElTree)
  .component('ElTreeSelect', ElTreeSelect)
  .mount('#app')
