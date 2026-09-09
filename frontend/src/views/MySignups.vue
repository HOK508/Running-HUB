<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { mySignups } from '../api/signups'

const router = useRouter()
const loading = ref(false)
const items = ref([])

const statusText = { pending: '待确认', confirmed: '已确认', rejected: '已拒绝' }
const statusType = { pending: 'warning', confirmed: 'success', rejected: 'danger' }

function fmtTime(t) {
  return t ? t.replace('T', ' ').slice(0, 16) : ''
}

onMounted(async () => {
  loading.value = true
  try {
    items.value = await mySignups()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading">
    <h2 class="page-title">我的报名</h2>
    <el-empty v-if="!loading && items.length === 0" description="还没有报名任何活动" />
    <el-card v-for="s in items" :key="s.id" class="item-card">
      <div class="item-head">
        <h3 class="item-title" @click="router.push(`/activities/${s.activity.id}`)">
          {{ s.activity.title }}
        </h3>
        <el-tag :type="statusType[s.status]">{{ statusText[s.status] }}</el-tag>
        <el-tag v-if="s.checked_in" type="success" effect="plain">已签到</el-tag>
      </div>
      <div class="item-meta">
        <span>📍 {{ s.activity.location }}</span>
        <span>🕐 {{ fmtTime(s.activity.start_time) }}</span>
        <span>报名于 {{ fmtTime(s.created_at) }}</span>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.page-title {
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
  flex: 1;
}
.item-title:hover {
  color: #409eff;
}
.item-meta {
  margin-top: 10px;
  display: flex;
  gap: 24px;
  color: #606266;
  font-size: 13px;
}
</style>
