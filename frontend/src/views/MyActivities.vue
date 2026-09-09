<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { myActivities, deleteActivity } from '../api/activities'
import { listSignups } from '../api/signups'
import { getAttendance } from '../api/checkins'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { isAdmin } = useAuth()
const loading = ref(false)
const activities = ref([])

// 报名/签到列表弹窗
const dialogVisible = ref(false)
const dialogMode = ref('signups') // signups | checkins
const dialogTitle = ref('')
const dialogItems = ref([])

const signupStatusText = { pending: '待确认', confirmed: '已确认', rejected: '已拒绝' }

async function load() {
  loading.value = true
  try {
    activities.value = await myActivities()
  } finally {
    loading.value = false
  }
}

async function handleDelete(a) {
  try {
    await ElMessageBox.confirm(`确定删除活动「${a.title}」吗？`, '删除活动', { type: 'warning' })
  } catch {
    return
  }
  await deleteActivity(a.id)
  ElMessage.success('已删除')
  await load()
}

async function showSignups(a) {
  dialogMode.value = 'signups'
  dialogTitle.value = `「${a.title}」报名列表`
  const data = await listSignups(a.id)
  dialogItems.value = data.items
  dialogVisible.value = true
}

async function showCheckins(a) {
  dialogMode.value = 'checkins'
  const data = await getAttendance(a.id)
  dialogTitle.value = `「${a.title}」签到清单（${data.checked_in_count}/${data.total} 已签到）`
  dialogItems.value = data.items
  dialogVisible.value = true
}

function fmtTime(t) {
  return t ? t.replace('T', ' ').slice(0, 16) : ''
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <div class="page-head">
      <h2>我创建的活动</h2>
      <el-button type="primary" @click="router.push('/activities/create')">发起活动</el-button>
    </div>
    <el-empty v-if="!loading && activities.length === 0" description="还没有创建过活动" />
    <el-card v-for="a in activities" :key="a.id" class="item-card">
      <div class="item-head">
        <h3 class="item-title" @click="router.push(`/activities/${a.id}`)">{{ a.title }}</h3>
      </div>
      <div class="item-meta">
        <span>📍 {{ a.location }}</span>
        <span>🕐 {{ fmtTime(a.start_time) }}</span>
        <span>👥 {{ a.signup_count }}/{{ a.max_participants }}</span>
      </div>
      <div class="item-actions">
        <el-button size="small" @click="showSignups(a)">报名列表</el-button>
        <el-button size="small" @click="showCheckins(a)">签到列表</el-button>
        <el-button size="small" type="danger" plain @click="handleDelete(a)">删除</el-button>
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px">
      <el-table v-if="dialogMode === 'signups'" :data="dialogItems" size="small">
        <el-table-column prop="nickname" label="昵称" />
        <!-- 具体身份信息仅管理员可见 -->
        <template v-if="isAdmin">
          <el-table-column prop="real_name" label="姓名" />
          <el-table-column prop="student_id" label="学号" />
          <el-table-column prop="college" label="学院" />
          <el-table-column prop="phone" label="手机号" />
        </template>
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag size="small">{{ signupStatusText[row.status] }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-else :data="dialogItems" size="small">
        <el-table-column prop="nickname" label="昵称" />
        <template v-if="isAdmin">
          <el-table-column prop="real_name" label="姓名" />
          <el-table-column prop="student_id" label="学号" />
          <el-table-column prop="college" label="学院" />
        </template>
        <el-table-column label="签到状态">
          <template #default="{ row }">
            <template v-if="row.checked_in">
              <el-tag type="success" size="small">已签到</el-tag>
              <div class="checkin-time">{{ fmtTime(row.checkin_time) }}</div>
            </template>
            <el-tag v-else type="danger" size="small" effect="dark">未签到</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="dialogItems.length === 0" description="暂无数据" :image-size="60" />
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.item-card {
  margin-bottom: 12px;
}
.item-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.item-title {
  cursor: pointer;
}
.item-title:hover {
  color: #409eff;
}
.item-meta {
  margin-top: 10px;
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  color: #606266;
  font-size: 13px;
}
/* 连体单元整体换行 */
.item-meta span {
  white-space: nowrap;
}
.item-actions {
  margin-top: 12px;
}
.checkin-time {
  font-size: 11px;
  color: #909399;
}
</style>
