// 登录状态管理：token + 用户信息存 localStorage，刷新页面不丢
// 状态简单，用一个组合式函数即可，不需要引入 Pinia
import { ref, computed } from 'vue'

const token = ref(localStorage.getItem('token') || '')
const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

function setAuth(data) {
  token.value = data.token
  user.value = data.user
  localStorage.setItem('token', data.token)
  localStorage.setItem('user', JSON.stringify(data.user))
}

function clearAuth() {
  token.value = ''
  user.value = null
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

const isLoggedIn = computed(() => !!token.value)
const isAdmin = computed(() => !!user.value?.is_admin)

export function useAuth() {
  return { token, user, setAuth, clearAuth, isLoggedIn, isAdmin }
}
