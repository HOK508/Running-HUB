import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  { path: '/', name: 'activities', component: () => import('../views/Activities.vue') },
  { path: '/activities/:id', name: 'activity-detail', component: () => import('../views/ActivityDetail.vue') },
  { path: '/activities/create', name: 'activity-create', component: () => import('../views/ActivityCreate.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/my/activities', name: 'my-activities', component: () => import('../views/MyActivities.vue'), meta: { requiresAuth: true } },
  { path: '/my/signups', name: 'my-signups', component: () => import('../views/MySignups.vue'), meta: { requiresAuth: true } },
  { path: '/profile', name: 'profile', component: () => import('../views/Profile.vue'), meta: { requiresAuth: true } },
  { path: '/admin', name: 'admin', component: () => import('../views/Admin.vue'), meta: { requiresAuth: true, requiresAdmin: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：前端第一道防线（真正的安全由后端保证，这里只是体验）
router.beforeEach((to) => {
  const { isLoggedIn, isAdmin } = useAuth()
  if (to.meta.requiresAuth && !isLoggedIn.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !isAdmin.value) {
    return { path: '/' }
  }
  if (to.path === '/login' && isLoggedIn.value) {
    return { path: '/' }
  }
})

export default router
