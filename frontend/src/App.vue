<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'

const route = useRoute()
const router = useRouter()
const { isAdmin } = useAuth()

// 登录页全屏展示，不显示底部导航
const showTabbar = computed(() => route.path !== '/login')

// 根页面（TabBar 页 + 登录页）不显示返回键，其余子页面显示
const rootPaths = ['/', '/my/signups', '/profile', '/admin']
const showBack = computed(() => !rootPaths.includes(route.path) && route.path !== '/login')

// 返回：优先浏览器历史（保留来源页状态，如回顾 Tab），直接打开时回退首页
function goBack() {
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push('/')
  }
}

// 底部 TabBar：
// 普通用户：活动 / 我的报名 / 我的
// 管理员：  活动 / 管理 / 我的（发起活动已并入活动页的悬浮按钮）
const tabs = computed(() => {
  if (isAdmin.value) {
    return [
      { path: '/', label: '活动', icon: '🏃' },
      { path: '/admin', label: '管理', icon: '🛠' },
      { path: '/profile', label: '我的', icon: '👤' }
    ]
  }
  return [
    { path: '/', label: '活动', icon: '🏃' },
    { path: '/my/signups', label: '我的报名', icon: '📋' },
    { path: '/profile', label: '我的', icon: '👤' }
  ]
})

function isActive(tab) {
  if (tab.path === '/') {
    return route.path === '/' || route.path.startsWith('/activities/')
  }
  return route.path === tab.path
}
</script>

<template>
  <div class="app-shell">
    <header class="app-bar">
      <span v-if="showBack" class="back-btn" @click="goBack">‹</span>
      <span class="app-title">🏃 RUNing HUB</span>
    </header>
    <main class="app-content">
      <router-view />
    </main>
    <nav v-if="showTabbar" class="tabbar">
      <div
        v-for="tab in tabs"
        :key="tab.path"
        class="tab"
        :class="{ active: isActive(tab) }"
        @click="router.push(tab.path)"
      >
        <span class="tab-icon" :class="{ big: tab.highlight }">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
      </div>
    </nav>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #eef1f5;
}
/* 手机 App 外壳：桌面端居中显示为手机宽度，移动端全宽 */
.app-shell {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  background: #f5f7fa;
  box-shadow: 0 0 16px rgba(0, 0, 0, 0.06);
}
.app-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  /* 固定高度：页面内吸顶元素（如活动/回顾切换条）以此对齐，滚动无空隙 */
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.back-btn {
  position: absolute;
  left: 8px;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
  color: #606266;
  padding: 0 8px;
  user-select: none;
}
.app-title {
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
}
.app-content {
  padding: 12px 12px 76px;
}
.tabbar {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
  display: flex;
  z-index: 10;
}
.tab {
  flex: 1;
  text-align: center;
  padding: 8px 0 6px;
  cursor: pointer;
  color: #909399;
}
.tab.active {
  color: #409eff;
}
.tab-icon {
  font-size: 20px;
  display: block;
  line-height: 1.2;
}
.tab-icon.big {
  font-size: 26px;
}
.tab-label {
  font-size: 11px;
}
</style>
