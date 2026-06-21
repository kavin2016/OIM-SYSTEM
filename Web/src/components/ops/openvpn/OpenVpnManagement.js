import '../../../styles/components/resource-page.css'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { hasPermission } from '../../../composables/useAuth.js'
import { openVpnTabs } from './shared/openVpnConfig.js'

const openVpnTabPaths = {
  servers: '/ops/openvpn/servers',
  accounts: '/ops/openvpn/accounts',
  sessions: '/ops/openvpn/sessions',
  logs: '/ops/openvpn/logs',
  rules: '/ops/openvpn/rules',
  traffic: '/ops/openvpn/traffic',
}

export default {
  setup() {
    const router = useRouter()
    const visibleTabs = computed(() => openVpnTabs.filter((tab) => hasPermission(tab.permission)))

    function openModule(tab) {
      router.push(openVpnTabPaths[tab.key] || '/ops/openvpn/servers')
    }

    return {
      openModule,
      visibleTabs,
    }
  },
}
