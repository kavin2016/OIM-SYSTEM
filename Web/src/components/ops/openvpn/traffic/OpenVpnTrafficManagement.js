import '../../../../styles/components/resource-page.css'
import './OpenVpnTrafficManagement.css'
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { token, hasPermission } from '../../../../composables/useAuth.js'
import { openvpnAPI } from '../../../../api/openvpn.js'
import { actionIconMap } from '../../../system/resourcePageConstants.js'
import { asOpenVpnArray, formatOpenVpnDate, resetOpenVpnReactive } from '../shared/openVpnConfig.js'

const ACTION_TEXT = {
  notify: '仅提醒',
  disable_certificate: '禁用证书',
  manual_review: '人工处理',
}

const PERIOD_TEXT = {
  day: '按日',
  month: '按月',
}

const DIMENSION_TEXT = {
  server: '服务器',
  department: '部门',
  certificate: '证书',
}

function todayText() {
  return new Date().toISOString().slice(0, 10)
}

function monthStartText() {
  const value = new Date()
  value.setDate(1)
  return value.toISOString().slice(0, 10)
}

function emptyRuleForm() {
  return {
    id: null,
    name: '',
    target_type: 'server',
    target_id: '',
    period_type: 'day',
    threshold_gb: 10,
    action: 'notify',
    is_active: true,
    remark: '',
  }
}

export default {
  setup() {
    const loading = ref(false)
    const ruleLoading = ref(false)
    const alertLoading = ref(false)
    const servers = ref([])
    const certificates = ref([])
    const overview = ref({})
    const distribution = ref([])
    const trend = ref([])
    const ranking = ref([])
    const rules = ref([])
    const alerts = ref([])
    const showRuleModal = ref(false)
    const editingRuleId = ref(null)
    const ruleForm = reactive(emptyRuleForm())
    const trafficQuery = reactive({
      period_type: 'day',
      dimension: 'server',
      date_from: monthStartText(),
      date_to: todayText(),
    })
    const alertQuery = reactive({ status: 'open' })

    const can = (permission) => hasPermission(permission)
    const maxDistributionBytes = computed(() => Math.max(...distribution.value.map((item) => Number(item.bytes_total) || 0), 1))
    const maxRankingBytes = computed(() => Math.max(...ranking.value.map((item) => Number(item.bytes_total) || 0), 1))
    const ruleTargetOptions = computed(() => {
      if (ruleForm.target_type === 'certificate') {
        return certificates.value.map((item) => ({
          id: item.id,
          label: `${item.username || item.common_name || '-'} / ${item.common_name || '-'}`,
        }))
      }
      return servers.value.map((item) => ({ id: item.id, label: item.name }))
    })

    function formatBytes(value) {
      const bytes = Number(value) || 0
      if (bytes < 1024) return `${bytes} B`
      const units = ['KB', 'MB', 'GB', 'TB', 'PB']
      let size = bytes / 1024
      let unitIndex = 0
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024
        unitIndex += 1
      }
      return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unitIndex]}`
    }

    function barWidth(value, maxValue) {
      return `${Math.max(3, Math.round(((Number(value) || 0) / maxValue) * 100))}%`
    }

    function periodText(value) {
      return PERIOD_TEXT[value] || value || '-'
    }

    function dimensionText(value) {
      return DIMENSION_TEXT[value] || value || '-'
    }

    function actionText(value) {
      return ACTION_TEXT[value] || value || '-'
    }

    function alertStatusText(value) {
      return value === 'processed' ? '已处理' : '待处理'
    }

    async function loadOptions() {
      const [serverRows, certificateRows] = await Promise.all([
        openvpnAPI.listServers(token.value, { include_disabled: true, limit: 1000 }),
        openvpnAPI.listCertificates(token.value, { limit: 1000 }),
      ])
      servers.value = asOpenVpnArray(serverRows)
      certificates.value = asOpenVpnArray(certificateRows)
    }

    async function loadTraffic() {
      loading.value = true
      try {
        const baseParams = {
          period_type: trafficQuery.period_type,
          date_from: trafficQuery.date_from,
          date_to: trafficQuery.date_to,
        }
        const [overviewData, distributionData, trendData, rankingData] = await Promise.all([
          openvpnAPI.getTrafficOverview(token.value, baseParams),
          openvpnAPI.getTrafficDistribution(token.value, { ...baseParams, dimension: trafficQuery.dimension }),
          openvpnAPI.getTrafficTrend(token.value, baseParams),
          openvpnAPI.getTrafficRanking(token.value, { ...baseParams, dimension: 'certificate', limit: 10 }),
        ])
        overview.value = overviewData || {}
        distribution.value = asOpenVpnArray(distributionData)
        trend.value = asOpenVpnArray(trendData)
        ranking.value = asOpenVpnArray(rankingData)
      } finally {
        loading.value = false
      }
    }

    async function loadRules() {
      ruleLoading.value = true
      try {
        rules.value = asOpenVpnArray(await openvpnAPI.listTrafficThresholdRules(token.value, { limit: 1000 }))
      } finally {
        ruleLoading.value = false
      }
    }

    async function loadAlerts() {
      alertLoading.value = true
      try {
        alerts.value = asOpenVpnArray(await openvpnAPI.listTrafficAlerts(token.value, alertQuery))
      } finally {
        alertLoading.value = false
      }
    }

    async function refreshAll() {
      await Promise.all([loadTraffic(), loadRules(), loadAlerts()])
    }

    function resetTrafficQuery() {
      resetOpenVpnReactive(trafficQuery, {
        period_type: 'day',
        dimension: 'server',
        date_from: monthStartText(),
        date_to: todayText(),
      })
      loadTraffic()
    }

    function openCreateRule() {
      resetOpenVpnReactive(ruleForm, emptyRuleForm())
      editingRuleId.value = null
      showRuleModal.value = true
    }

    function openEditRule(row) {
      resetOpenVpnReactive(ruleForm, {
        id: row.id,
        name: row.name,
        target_type: row.target_type,
        target_id: row.target_id,
        period_type: row.period_type,
        threshold_gb: Number(((Number(row.threshold_bytes) || 0) / 1024 / 1024 / 1024).toFixed(2)),
        action: row.action,
        is_active: row.is_active,
        remark: row.remark || '',
      })
      editingRuleId.value = row.id
      showRuleModal.value = true
    }

    function closeRuleModal() {
      showRuleModal.value = false
      editingRuleId.value = null
    }

    function onRuleTargetTypeChange() {
      ruleForm.target_id = ''
    }

    function buildRulePayload() {
      return {
        name: ruleForm.name.trim(),
        target_type: ruleForm.target_type,
        target_id: Number(ruleForm.target_id),
        period_type: ruleForm.period_type,
        threshold_bytes: Math.max(1, Math.round((Number(ruleForm.threshold_gb) || 0) * 1024 * 1024 * 1024)),
        action: ruleForm.action,
        is_active: ruleForm.is_active,
        remark: ruleForm.remark?.trim() || null,
      }
    }

    async function saveRule() {
      if (!ruleForm.name.trim()) {
        ElMessage.warning('请输入规则名称')
        return
      }
      if (!ruleForm.target_id) {
        ElMessage.warning('请选择阈值对象')
        return
      }
      const payload = buildRulePayload()
      if (payload.threshold_bytes <= 0) {
        ElMessage.warning('阈值必须大于0')
        return
      }
      try {
        let savedRule = null
        if (editingRuleId.value) {
          savedRule = await openvpnAPI.updateTrafficThresholdRule(token.value, editingRuleId.value, payload)
          ElMessage.success('阈值规则已更新')
        } else {
          savedRule = await openvpnAPI.createTrafficThresholdRule(token.value, payload)
          editingRuleId.value = savedRule?.id || null
          ruleForm.id = savedRule?.id || null
          ElMessage.success('阈值规则已创建')
        }
        await loadRules()
      } catch (error) {
        ElMessage.error(error.message || '阈值规则保存失败')
      }
    }

    async function deleteRule(row) {
      try {
        await ElMessageBox.confirm(`确认删除阈值规则「${row.name}」？`, '删除确认', { type: 'warning' })
        await openvpnAPI.deleteTrafficThresholdRule(token.value, row.id)
        ElMessage.success('阈值规则已删除')
        await loadRules()
      } catch (error) {
        if (error !== 'cancel' && error !== 'close' && error?.action !== 'cancel' && error?.action !== 'close') {
          ElMessage.error(error.message || '阈值规则删除失败')
        }
      }
    }

    async function processAlert(row) {
      try {
        await ElMessageBox.confirm(`确认标记告警「${row.target_name || row.target_id}」为已处理？`, '告警处理确认', { type: 'warning' })
        await openvpnAPI.processTrafficAlert(token.value, row.id, '已确认处理')
        ElMessage.success('告警已处理')
        await Promise.all([loadAlerts(), loadTraffic()])
      } catch (error) {
        if (error !== 'cancel' && error !== 'close' && error?.action !== 'cancel' && error?.action !== 'close') {
          ElMessage.error(error.message || '告警处理失败')
        }
      }
    }

    onMounted(async () => {
      await loadOptions()
      await refreshAll()
    })

    return {
      actionIconMap,
      actionText,
      alertLoading,
      alertQuery,
      alertStatusText,
      alerts,
      barWidth,
      can,
      certificates,
      closeRuleModal,
      deleteRule,
      dimensionText,
      distribution,
      editingRuleId,
      formatBytes,
      formatDate: formatOpenVpnDate,
      loadAlerts,
      loadTraffic,
      loading,
      maxDistributionBytes,
      maxRankingBytes,
      onRuleTargetTypeChange,
      openCreateRule,
      openEditRule,
      overview,
      periodText,
      processAlert,
      ranking,
      refreshAll,
      resetTrafficQuery,
      ruleForm,
      ruleLoading,
      rules,
      ruleTargetOptions,
      saveRule,
      servers,
      showRuleModal,
      trafficQuery,
      trend,
    }
  },
}
