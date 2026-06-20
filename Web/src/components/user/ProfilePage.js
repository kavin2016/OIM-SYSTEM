import { ref, watchEffect } from 'vue'
import { api } from '../../api/request.js'
import { token, user, getMe } from '../../composables/useAuth.js'

export default {
  setup() {
    const username = ref('')
    const nickname = ref('')
    const gender = ref('')
    const email = ref('')
    const contactsText = ref('')
    const password = ref('')
    const updating = ref(false)
    const message = ref('')

    watchEffect(() => {
      username.value = user.value?.username || ''
      nickname.value = user.value?.nickname || ''
      gender.value = user.value?.gender || ''
      email.value = user.value?.email || ''
      contactsText.value = Array.isArray(user.value?.contacts) ? user.value.contacts.join('\n') : ''
    })

    async function handleUpdate() {
      updating.value = true
      message.value = ''
      try {
        const payload = {
          username: username.value,
          nickname: nickname.value.trim() || null,
          gender: gender.value || null,
          email: email.value,
          contacts: contactsText.value
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
        }
        if (password.value) {
          payload.password = password.value
        }
        await api.user.updateCurrentUser(token.value, payload)
        await getMe()
        password.value = ''
        message.value = '资料已更新'
      } catch (err) {
        message.value = err.message || '更新失败'
      } finally {
        updating.value = false
      }
    }

    return {
      username,
      nickname,
      gender,
      email,
      contactsText,
      password,
      updating,
      message,
      user,
      handleUpdate,
    }
  },
}
