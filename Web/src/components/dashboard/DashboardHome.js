import { user } from '../../composables/useAuth.js'

export default {
  setup() {
    function formatDate(dateString) {
      if (!dateString) return '未知'
      const date = new Date(dateString)
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      })
    }

    return {
      user,
      formatDate,
    }
  },
}
