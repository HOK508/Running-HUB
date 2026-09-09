import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { useAuth } from '../composables/useAuth'

// axios 统一封装：
// 请求：自动附带 token
// 响应：code=0 直接返回 data（组件少一层 .data.data）；出错统一弹提示；401 清登录态跳登录页
const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

request.interceptors.request.use((config) => {
  const { token } = useAuth()
  if (token.value) {
    config.headers.Authorization = `Bearer ${token.value}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 0) return res.data
    ElMessage.error(res.message || '请求失败')
    return Promise.reject(new Error(res.message))
  },
  (error) => {
    const res = error.response?.data
    const status = error.response?.status
    if (status === 401) {
      // token 无效/过期：清除登录态，跳登录页
      const { clearAuth } = useAuth()
      clearAuth()
      ElMessage.warning(res?.message || '请先登录')
      router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    } else if (res?.message) {
      ElMessage.error(res.message)
    } else {
      ElMessage.error('网络错误，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export default request
