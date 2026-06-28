import '../../../styles/components/resource-page.css'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { hasPermission } from '../../../composables/useAuth.js'
import { openVpnTabPaths, openVpnTabs } from './shared/openVpnConfig.js'

export default {
  setup() {
    const router = useRouter()
    const visibleTabs = computed(() => openVpnTabs.filter((tab) => hasPermission(tab.permission)))

    function openModule(tab) {
      router.push(openVpnTabPaths[tab.key] || '/ops/vpn/servers')
    }

    return {
      openModule,
      visibleTabs,
    }
  },
}
