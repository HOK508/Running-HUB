<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getActivity } from '../api/activities'
import { signup, cancelSignup } from '../api/signups'
import { checkin } from '../api/checkins'
import { likeActivity, unlikeActivity, listComments, createComment } from '../api/posts'
import { useAuth } from '../composables/useAuth'
import ReviewPublishDialog from '../components/ReviewPublishDialog.vue'

const route = useRoute()
const router = useRouter()
const { isLoggedIn, user: currentUser, isAdmin } = useAuth()

const activity = ref(null)
const loading = ref(false)
const signupLoading = ref(false)
// 报名成功弹窗（展示加群方式）
const groupDialogVisible = ref(false)
const groupData = ref(null)
// 帖子互动（已结束活动）
const comments = ref([])
const commentInput = ref('')
const likeLoading = ref(false)
const commentLoading = ref(false)
// 发布回顾帖（弹窗为公共组件 ReviewPublishDialog）
const reviewDialogVisible = ref(false)

const canPublishReview = computed(() => {
  if (!activity.value || activity.value.phase !== 'ended') return false
  if (activity.value.review) return false
  // 管理员的发布入口在「管理 → 回顾发布」Tab，详情页不再显示
  if (isAdmin.value) return false
  return activity.value.creator_id === currentUser.value?.id
})

const phaseText = {
  signup_open: '报名中',
  signup_closed: '报名已截止',
  ongoing: '进行中',
  ended: '已结束'
}
const signupStatusText = { pending: '待确认', confirmed: '已确认', rejected: '已拒绝' }
const signupStatusType = { pending: 'warning', confirmed: 'success', rejected: 'danger' }

const mySignup = computed(() => activity.value?.my_signup || null)
// 注意：JS 环境里 useAuth().user 是 ref，必须 .value 取值（模板里才会自动解包）
const isCreator = computed(() => activity.value && activity.value.creator_id === currentUser.value?.id)
const canSignup = computed(
  () => activity.value && activity.value.phase === 'signup_open' && !mySignup.value
)
const canCancel = computed(
  () => mySignup.value && mySignup.value.status !== 'rejected' && activity.value?.phase === 'signup_open'
)
const canCheckin = computed(
  () => mySignup.value?.status === 'confirmed' && activity.value && !activity.value.checked_in
)
const showGroupCard = computed(() => {
  if (!activity.value) return false
  // 报名已确认（详情接口已按权限返回群信息）或创建者
  return !!activity.value.group_info || !!activity.value.group_qr_code
})

async function load() {
  loading.value = true
  try {
    activity.value = await getActivity(route.params.id)
    // 已结束且已发布回顾帖的活动加载评论区
    if (activity.value.phase === 'ended' && activity.value.review) {
      comments.value = await listComments(activity.value.id)
    }
  } catch (e) {
    // 20001 活动不存在：拦截器已提示，返回列表
    router.push('/')
  } finally {
    loading.value = false
  }
}


// 点赞/取消点赞（幂等接口，直接以返回值为准）+ 心动动画
const likeAnim = ref(false)

async function toggleLike() {
  likeLoading.value = true
  try {
    const data = activity.value.my_liked
      ? await unlikeActivity(activity.value.id)
      : await likeActivity(activity.value.id)
    activity.value.my_liked = data.liked
    activity.value.like_count = data.like_count
    // 点赞成功触发一次心跳动画
    if (data.liked) {
      likeAnim.value = true
      setTimeout(() => (likeAnim.value = false), 450)
    }
  } catch (e) {
    // 已提示
  } finally {
    likeLoading.value = false
  }
}

async function handleComment() {
  const content = commentInput.value.trim()
  if (!content) return
  commentLoading.value = true
  try {
    const c = await createComment(activity.value.id, { content })
    comments.value.push(c)
    activity.value.comment_count += 1
    commentInput.value = ''
  } catch (e) {
    // 已提示
  } finally {
    commentLoading.value = false
  }
}

async function handleSignup() {
  signupLoading.value = true
  try {
    const data = await signup(activity.value.id)
    // 报名成功弹窗：确认后展示加群方式；待确认时提示等待管理员审核
    groupData.value = {
      status: data.status,
      group_info: data.group_info,
      group_qr_code: data.group_qr_code
    }
    groupDialogVisible.value = true
    await load()
  } finally {
    signupLoading.value = false
  }
}

async function handleCancel() {
  let reason
  try {
    // 退出报名必须填写原因（管理员可标记恶意退出）
    const res = await ElMessageBox.prompt('请填写退出报名的原因', '退出报名', {
      confirmButtonText: '确认退出',
      cancelButtonText: '再想想',
      inputPlaceholder: '退出原因（必填，如：临时有事）',
      inputValidator: (v) => (v && v.trim() ? true : '原因不能为空')
    })
    reason = res.value.trim()
  } catch {
    return
  }
  await cancelSignup(activity.value.id, { reason })
  ElMessage.success('已退出报名')
  await load()
}

async function handleCheckin() {
  await checkin(activity.value.id)
  ElMessage.success('签到成功')
  await load()
}

function fmtTime(t) {
  return t ? t.replace('T', ' ').slice(0, 16) : ''
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <template v-if="activity">
      <el-card class="detail-card">
        <!-- 图片轮播 -->
        <el-carousel v-if="activity.image_urls.length" height="320px" class="carousel">
          <el-carousel-item v-for="(img, i) in activity.image_urls" :key="i">
            <img :src="img" class="carousel-img" />
          </el-carousel-item>
        </el-carousel>

        <h2 class="title">{{ activity.title }}</h2>
        <div class="tags">
          <el-tag>{{ phaseText[activity.phase] }}</el-tag>
          <el-tag type="info">👥 {{ activity.signup_count }}/{{ activity.max_participants }}</el-tag>
          <el-tag type="info">👁 {{ activity.view_count }} 人看过</el-tag>
          <el-tag v-if="mySignup" :type="signupStatusType[mySignup.status]">
            我的报名：{{ signupStatusText[mySignup.status] }}
          </el-tag>
          <el-tag v-if="activity.checked_in" type="success">已签到</el-tag>
        </div>

        <el-descriptions :column="2" border class="descriptions">
          <el-descriptions-item label="地点">📍 {{ activity.location }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">🕐 {{ fmtTime(activity.start_time) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ fmtTime(activity.end_time) }}</el-descriptions-item>
          <el-descriptions-item label="报名截止">{{ fmtTime(activity.signup_deadline) }}</el-descriptions-item>
          <el-descriptions-item label="活动介绍" :span="2">{{ activity.description || '暂无介绍' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 群信息（仅报名已确认者/创建者可见，详情接口已按权限过滤；已结束活动不显示） -->
        <template v-if="activity.phase !== 'ended'">
          <el-card v-if="showGroupCard" class="group-card">
            <template #header><b>活动群信息</b></template>
            <p v-if="activity.group_info">{{ activity.group_info }}</p>
            <img v-if="activity.group_qr_code" :src="activity.group_qr_code" class="qr-img" />
          </el-card>
          <el-alert
            v-else-if="mySignup && mySignup.status !== 'confirmed'"
            type="info"
            :closable="false"
            title="报名确认后可查看加群方式"
          />
          <el-alert
            v-else-if="!isCreator"
            type="info"
            :closable="false"
            title="报名成功后可查看加群方式"
          />
        </template>

        <!-- 操作区：管理员只显示管理入口，不显示报名/取消/签到 -->
        <div class="actions">
          <el-button v-if="!isLoggedIn" type="primary" @click="router.push({ path: '/login', query: { redirect: route.fullPath } })">
            登录后报名
          </el-button>
          <template v-else-if="isAdmin || isCreator">
            <el-button @click="router.push(isAdmin ? '/admin' : '/my/activities')">
              {{ isAdmin ? '🛠 管理入口' : '管理我的活动' }}
            </el-button>
          </template>
          <template v-else>
            <el-button
              v-if="canSignup"
              type="primary"
              :loading="signupLoading"
              :disabled="activity.signup_count >= activity.max_participants"
              @click="handleSignup"
            >
              {{ activity.signup_count >= activity.max_participants ? '名额已满' : '立即报名' }}
            </el-button>
            <el-button v-if="canCancel" @click="handleCancel">取消报名</el-button>
            <el-button v-if="canCheckin" type="success" @click="handleCheckin">签到</el-button>
            <el-tag v-if="activity.phase === 'signup_closed' && !mySignup" type="warning">报名已截止</el-tag>
          </template>
        </div>

        <!-- 已结束活动：回顾帖 + 互动区 -->
        <template v-if="activity.phase === 'ended'">
          <el-divider>活动回顾</el-divider>

          <!-- 回顾帖内容（管理员/发起人发布） -->
          <div v-if="activity.review" class="review-post">
            <div class="review-head">
              <span class="review-author">{{ activity.review.author_nickname }} 发布的总结</span>
              <span class="review-time">{{ fmtTime(activity.review.created_at) }}</span>
            </div>
            <div class="review-content">{{ activity.review.content }}</div>
            <div v-if="activity.review.image_urls.length" class="review-images">
              <el-image
                v-for="(img, i) in activity.review.image_urls"
                :key="i"
                :src="img"
                :preview-src-list="activity.review.image_urls"
                :initial-index="i"
                fit="cover"
                class="review-img"
              />
            </div>
          </div>
          <el-empty
            v-else
            description="活动发起人还没有发布回顾总结"
            :image-size="60"
          />

          <!-- 发起人/管理员可发布回顾 -->
          <div v-if="canPublishReview" class="publish-bar">
            <el-button type="primary" plain size="small" @click="reviewDialogVisible = true">
              ✍️ 发布活动回顾
            </el-button>
          </div>

          <!-- 互动区：仅发布回顾后开放 -->
          <template v-if="activity.review">
            <el-divider />
            <div class="post-actions">
              <el-button
                :type="activity.my_liked ? 'danger' : 'default'"
                plain
                :loading="likeLoading"
                :class="{ 'like-anim': likeAnim }"
                @click="toggleLike"
              >
                {{ activity.my_liked ? '❤️ 已点赞' : '🤍 点赞' }} {{ activity.like_count }}
              </el-button>
            </div>
            <div class="comments">
              <h4 class="comments-title">评论（{{ activity.comment_count }}）</h4>
              <div v-for="c in comments" :key="c.id" class="comment-item">
                <div class="comment-head">
                  <span class="comment-name">{{ c.nickname }}</span>
                  <span class="comment-time">{{ fmtTime(c.created_at) }}</span>
                </div>
                <div class="comment-content">{{ c.content }}</div>
              </div>
              <el-empty v-if="comments.length === 0" description="还没有评论，来抢沙发" :image-size="50" />
              <div class="comment-input">
                <template v-if="isLoggedIn">
                  <el-input
                    v-model="commentInput"
                    placeholder="说点什么..."
                    maxlength="200"
                    @keyup.enter="handleComment"
                  />
                  <el-button type="primary" size="small" :loading="commentLoading" @click="handleComment">
                    发送
                  </el-button>
                </template>
                <el-button
                  v-else
                  type="primary"
                  plain
                  size="small"
                  @click="router.push({ path: '/login', query: { redirect: route.fullPath } })"
                >
                  登录后参与评论
                </el-button>
              </div>
            </div>
          </template>
        </template>
      </el-card>

      <!-- 发布回顾帖弹窗（公共组件） -->
      <ReviewPublishDialog v-if="activity" v-model="reviewDialogVisible" :activity-id="activity.id" @published="load" />

      <!-- 报名成功弹窗：已确认展示加群方式，待确认提示等待审核 -->
      <el-dialog v-model="groupDialogVisible" :title="groupData?.status === 'confirmed' ? '报名成功 🎉' : '报名已提交'" width="360px">
        <template v-if="groupData?.status === 'confirmed'">
          <p class="dialog-tip">快加入活动群和大家联系吧：</p>
          <div v-if="groupData?.group_info" class="group-info">{{ groupData.group_info }}</div>
          <img v-if="groupData?.group_qr_code" :src="groupData.group_qr_code" class="dialog-qr" />
          <p v-if="!groupData?.group_info && !groupData?.group_qr_code" class="dialog-tip">
            活动暂时没有提供加群方式，稍后在活动详情页查看
          </p>
        </template>
        <template v-else>
          <p class="dialog-tip">报名已提交，等待管理员确认。确认通过后可在活动详情页查看加群方式。</p>
        </template>
        <template #footer>
          <el-button type="primary" @click="groupDialogVisible = false">知道了</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<style scoped>
.carousel {
  margin-bottom: 16px;
  border-radius: 6px;
  overflow: hidden;
}
.carousel-img {
  width: 100%;
  height: 320px;
  object-fit: cover;
}
.title {
  margin-bottom: 12px;
}
.tags {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.descriptions {
  margin-bottom: 16px;
}
.group-card {
  margin-bottom: 16px;
  border-color: #67c23a;
}
.qr-img {
  width: 180px;
  margin-top: 8px;
}
.actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}
.dialog-tip {
  color: #606266;
  margin-bottom: 12px;
}
.group-info {
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 12px;
  word-break: break-all;
}
.dialog-qr {
  width: 180px;
  display: block;
}
.post-actions {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}
/* 点赞心跳动画 */
.like-anim {
  animation: heartbeat 0.45s ease;
}
@keyframes heartbeat {
  0% {
    transform: scale(1);
  }
  30% {
    transform: scale(1.3);
  }
  60% {
    transform: scale(0.95);
  }
  100% {
    transform: scale(1);
  }
}
.review-post {
  background: #fafbfc;
  border-radius: 8px;
  padding: 12px;
}
.review-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.review-author {
  font-weight: 600;
  font-size: 13px;
  color: #409eff;
  white-space: nowrap;
}
.review-time {
  color: #c0c4cc;
  font-size: 12px;
  white-space: nowrap;
}
.review-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.7;
  word-break: break-all;
}
.review-images {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.review-img {
  width: 96px;
  height: 96px;
  border-radius: 6px;
}
.publish-bar {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.thumb {
  position: relative;
}
.thumb img {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}
.thumb-del {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 18px;
  height: 18px;
  padding: 0;
  font-size: 10px;
}
.comments-title {
  margin-bottom: 12px;
}
.comment-item {
  padding: 10px 0;
  border-bottom: 1px solid #f5f7fa;
}
.comment-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}
.comment-name {
  font-weight: 600;
  font-size: 14px;
  color: #409eff;
  white-space: nowrap;
}
.comment-time {
  color: #c0c4cc;
  font-size: 12px;
  white-space: nowrap;
}
.comment-content {
  font-size: 14px;
  color: #303133;
  word-break: break-all;
}
.comment-input {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
