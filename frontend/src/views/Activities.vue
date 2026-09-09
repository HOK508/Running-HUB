<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listActivities, listAllActivities } from '../api/activities'
import { listReviews } from '../api/posts'
import { useAuth } from '../composables/useAuth'
import ReviewPublishDialog from '../components/ReviewPublishDialog.vue'

const router = useRouter()
const route = useRoute()
const { isAdmin } = useAuth()
const loading = ref(false)
// Tab 状态记录在 URL query：从详情返回时保持"回顾"Tab 不丢
const activeTab = ref(route.query.tab === 'ended' ? 'ended' : 'ongoing')
const activities = ref([])
const reviews = ref([])
// 管理员：已结束但未发布回顾的活动（回顾 Tab 顶部显示发布按钮）
const unpublished = ref([])
const reviewPublishVisible = ref(false)
const reviewPublishId = ref(0)

const phaseText = {
  signup_open: '报名中',
  signup_closed: '报名已截止',
  ongoing: '进行中',
  ended: '已结束'
}
const phaseType = { signup_open: 'success', signup_closed: 'warning', ongoing: 'primary', ended: 'info' }

function fmtTime(t) {
  return t ? t.replace('T', ' ').slice(0, 16) : ''
}

async function load() {
  loading.value = true
  try {
    if (activeTab.value === 'ongoing') {
      activities.value = await listActivities()
    } else {
      reviews.value = await listReviews()
      // 管理员额外加载"已结束未发布"的活动，提供发布回顾入口
      if (isAdmin.value) {
        const all = await listAllActivities()
        unpublished.value = all.filter((a) => a.phase === 'ended' && !a.review)
      }
    }
  } finally {
    loading.value = false
  }
}

function openReviewPublish(a) {
  reviewPublishId.value = a.id
  reviewPublishVisible.value = true
}

function switchTab(tab) {
  activeTab.value = tab
  router.replace({ query: tab === 'ended' ? { tab: 'ended' } : {} })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <!-- 顶部切换：活动 / 回顾 -->
    <div class="tab-switch">
      <div class="switch-item" :class="{ active: activeTab === 'ongoing' }" @click="switchTab('ongoing')">
        🔥 活动
      </div>
      <div class="switch-item" :class="{ active: activeTab === 'ended' }" @click="switchTab('ended')">
        📖 回顾
      </div>
    </div>

    <Transition name="tab-fade" mode="out-in">
    <div v-if="activeTab === 'ongoing'" key="ongoing">
      <el-empty
        v-if="!loading && activities.length === 0"
        :description="isAdmin ? '暂无活动，点击右下角「+」发起活动' : '暂无活动，敬请期待'"
      />
      <el-card
        v-for="a in activities"
        :key="a.id"
        class="activity-card"
        shadow="hover"
        @click="router.push(`/activities/${a.id}`)"
      >
        <div class="card-body">
          <img v-if="a.image_urls.length" :src="a.image_urls[0]" class="cover" alt="封面" />
          <div v-else class="cover cover-empty">RUNhub</div>
          <div class="card-info">
            <h3 class="title">{{ a.title }}</h3>
            <div class="meta">📍 {{ a.location }}</div>
            <div class="meta">🕐 {{ fmtTime(a.start_time) }}</div>
            <div class="meta-row">
              <el-tag :type="phaseType[a.phase]" size="small">{{ phaseText[a.phase] }}</el-tag>
              <span class="count">👥 {{ a.signup_count }}/{{ a.max_participants }}</span>
              <span class="count">👁 {{ a.view_count }}</span>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <div v-else key="ended">
      <!-- 管理员：已结束未发布的活动（点击卡片看详情，发布回顾单独入口） -->
      <el-card
        v-for="a in unpublished"
        :key="a.id"
        class="activity-card pending-card"
        @click="router.push(`/activities/${a.id}`)"
      >
        <div class="pending-head">
          <h3 class="pending-title">🏁 {{ a.title }}</h3>
          <el-tag type="warning" size="small">待发布回顾</el-tag>
        </div>
        <div class="meta">📍 {{ a.location }} · 🕐 {{ fmtTime(a.end_time) }} 结束 · 👥 {{ a.signup_count }} 人参加</div>
        <div class="pending-actions">
          <el-button size="small" type="primary" @click.stop="openReviewPublish(a)">✍️ 发布回顾</el-button>
        </div>
      </el-card>

      <el-empty
        v-if="!loading && reviews.length === 0 && unpublished.length === 0"
        description="还没有回顾帖"
      />
      <el-card
        v-for="r in reviews"
        :key="r.id"
        class="activity-card post-card"
        shadow="hover"
        @click="router.push(`/activities/${r.activity.id}`)"
      >
        <div class="post-head">
          <span class="post-activity">🏁 {{ r.activity.title }}</span>
          <span class="post-author">by {{ r.author.nickname }}</span>
        </div>
        <div class="post-content">{{ r.content }}</div>
        <div v-if="r.image_urls.length" class="post-images">
          <img v-for="(img, i) in r.image_urls.slice(0, 3)" :key="i" :src="img" class="post-img" />
        </div>
        <div class="meta-row">
          <span class="count">❤️ {{ r.like_count }}</span>
          <span class="count">💬 {{ r.comment_count }}</span>
          <span class="count">👁 {{ r.activity.view_count }}</span>
          <span class="post-time">{{ fmtTime(r.created_at) }}</span>
        </div>
      </el-card>
    </div>
    </Transition>

    <!-- 管理员：发起活动悬浮按钮（原发布 Tab 并入活动页） -->
    <button v-if="isAdmin" class="fab" @click="router.push('/activities/create')">＋</button>

    <!-- 发布回顾帖弹窗（公共组件） -->
    <ReviewPublishDialog
      v-model="reviewPublishVisible"
      :activity-id="reviewPublishId"
      @published="load"
    />
  </div>
</template>

<style scoped>
.tab-switch {
  display: flex;
  background: #fff;
  padding: 6px 12px;
  /* 吸顶并紧贴顶栏（48px），负外边距让切换条左右满宽，滚动时内容不会从缝隙透出 */
  position: sticky;
  top: 48px;
  z-index: 5;
  margin: -12px -12px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.switch-item {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  border-radius: 8px;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
}
.switch-item.active {
  background: #409eff;
  color: #fff;
  font-weight: 600;
}
.activity-card {
  margin-bottom: 12px;
  cursor: pointer;
  border-radius: 12px;
  transition: transform 0.15s ease, box-shadow 0.2s ease;
}
.activity-card:hover {
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.18);
}
.activity-card:active {
  transform: scale(0.98);
}
/* Tab 切换淡入过渡 */
.tab-fade-enter-active,
.tab-fade-leave-active {
  transition: opacity 0.18s ease;
}
.tab-fade-enter-from,
.tab-fade-leave-to {
  opacity: 0;
}
.card-body {
  display: flex;
  gap: 12px;
}
.cover {
  width: 110px;
  height: 84px;
  object-fit: cover;
  border-radius: 8px;
  flex-shrink: 0;
}
.cover-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff, #79bbff);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}
.card-info {
  flex: 1;
  min-width: 0;
}
.title {
  font-size: 17px;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  color: #909399;
  font-size: 13px;
  margin-bottom: 3px;
  /* 连体内容不换行：图标+文字是一个整体，放不下就整行省略 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.count {
  color: #606266;
  font-size: 13px;
  /* 数字+单位是连体单元，整体换行不拆开 */
  white-space: nowrap;
}
.post-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.post-activity {
  font-weight: 600;
  color: #409eff;
  font-size: 15px;
  white-space: nowrap;
}
.post-author {
  color: #909399;
  font-size: 12px;
  white-space: nowrap;
}
.post-content {
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.post-images {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}
.post-img {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 6px;
}
.post-time {
  margin-left: auto;
  color: #c0c4cc;
  font-size: 12px;
}
.fab {
  position: fixed;
  bottom: 76px;
  right: max(16px, calc(50% - 224px));
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: #409eff;
  color: #fff;
  font-size: 26px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  z-index: 9;
  transition: transform 0.2s ease, background 0.2s ease;
}
.fab:hover {
  transform: scale(1.1) rotate(90deg);
}
.fab:active {
  background: #337ecc;
  transform: scale(0.95) rotate(90deg);
}
.pending-card {
  border-left: 3px solid #e6a23c;
}
.pending-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.pending-title {
  font-size: 15px;
  white-space: nowrap;
}
.pending-actions {
  margin-top: 8px;
}
</style>
