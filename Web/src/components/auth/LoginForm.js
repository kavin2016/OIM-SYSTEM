import '../../styles/components/login-form.css'
import 'element-plus/theme-chalk/el-message.css'
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, isAuthenticated, getMe } from '../../composables/useAuth.js'
import { api } from '../../api/request.js'

export default {
  setup() {
    const router = useRouter()
    const username = ref('')
    const password = ref('')
    const captcha = ref('')
    const captchaImage = ref('')
    const captchaToken = ref('')
    const captchaVersion = ref(0)
    const errorMessage = ref('')
    const loading = ref(false)
    const captchaLoading = ref(false)

    const showError = (message) => {
      errorMessage.value = message
      ElMessage.error(message)
    }

    const refreshCaptcha = async () => {
      errorMessage.value = ''
      captchaLoading.value = true
      try {
        const data = await api.auth.getCaptcha()
        captchaImage.value = data.captcha_image
        captchaToken.value = data.captcha_token
        captchaVersion.value += 1
        captcha.value = ''
      } catch (err) {
        showError(err.message || '验证码加载失败')
        captchaImage.value = ''
        captchaToken.value = ''
      } finally {
        captchaLoading.value = false
      }
    }

    const handleLogin = async () => {
      if (loading.value || captchaLoading.value) return
      if (!captchaToken.value) {
        showError('验证码未加载，请刷新验证码后重试')
        await refreshCaptcha()
        return
      }

      loading.value = true
      errorMessage.value = ''
      try {
        await login({
          username: username.value.trim(),
          password: password.value,
          captcha: captcha.value.trim(),
          captchaToken: captchaToken.value,
        })
        await router.replace('/dashboard')
      } catch (err) {
        showError(err.message || '登录失败')
        await refreshCaptcha()
      } finally {
        loading.value = false
      }
    }

    const handlePageShow = async (event) => {
      if (event.persisted) {
        await refreshCaptcha()
      }
    }

    onMounted(async () => {
      window.addEventListener('pageshow', handlePageShow)
      if (isAuthenticated.value) {
        try {
          await getMe()
          await router.replace('/dashboard')
          return
        } catch (err) {
          showError(err.message || '登录状态已失效，请重新登录')
        }
      }
      await refreshCaptcha()
    })

    onBeforeUnmount(() => {
      window.removeEventListener('pageshow', handlePageShow)
    })

    return {
      username,
      password,
      captcha,
      captchaImage,
      captchaToken,
      captchaVersion,
      errorMessage,
      loading,
      captchaLoading,
      refreshCaptcha,
      handleLogin,
    }
  },
}
