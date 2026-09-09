<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listAllActivities, deleteActivity, updateActivity, uploadActivityImage } from '../api/activities'
import { listSignups, allSignups, reviewSignup, listCancellations, markMalicious, noShowRecords } from '../api/signups'
import { getAttendance } from '../api/checkins'

const activeTab = ref('activities')
const loading = ref(false)

// 活动管理
const activities = ref([])
const dialogVisible = ref(false)
const dialogMode = ref('signups') // signups | checkins
const dialogTitle = ref('')
const dialogItems = ref([])

// 报名信息（含完整身份信息）
const signupRecords = ref([])
const signupFilter = ref(0) // 0 = 全部活动
const filteredSignups = computed(() =>
  signupFilter.value === 0
    ? signupRecords.value
    : signupRecords.value.filter((s) => s.activity.id === signupFilter.value)
)
const activityOptions = computed(() => {
  const seen = new Map()
  for (const s of signupRecords.value) {
    if (!seen.has(s.activity.id)) seen.set(s.activity.id, s.activity.title)
  }
  return [...seen.entries()].map(([id, title]) => ({ id, title }))
})

// 退出记录（含按用户统计的退出次数清单）
const cancellations = ref([])
const userStats = computed(() => {
  const map = new Map()
  for (const c of cancellations.value) {
    if (!map.has(c.user.id)) {
      map.set(c.user.id, {
        id: c.user.id,
        nickname: c.user.nickname,
        real_name: c.user.real_name,
        total: 0,
        malicious: 0
      })
    }
    const s = map.get(c.user.id)
    s.total += 1
    if (c.is_malicious) s.malicious += 1
  }
  // 恶意次数多的排前面
  return [...map.values()].sort((a, b) => b.malicious - a.malicious || b.total - a.total)
})

// 违约记录（已确认报名但活动结束后未签到，按人统计违约次数）
const noShows = ref([])
const noShowStats = computed(() => {
  const map = new Map()
  for (const n of noShows.value) {
    if (!map.has(n.user.id)) {
      map.set(n.user.id, {
        id: n.user.id,
        nickname: n.user.nickname,
        real_name: n.user.real_name,
        count: 0
      })
    }
    map.get(n.user.id).count += 1
  }
  return [...map.values()].sort((a, b) => b.count - a.count)
})

// 编辑活动弹窗（用 reactive + Object.assign：整体替换 ref 对象会导致表单不刷新）
const editDialogVisible = ref(false)
const editFormRef = ref()
const editLoading = ref(false)
const editingId = ref(0)
const editForm = reactive({
  title: '',
  description: '',
  image_urls: [],
  location: '',
  start_time: '',
  end_time: '',
  signup_deadline: '',
  max_participants: 20,
  group_info: '',
  group_qr_code: ''
})
const editRules = {
  title: [{ required: true, message: '请输入活动名称', trigger: 'blur' }],
  location: [{ required: true, message: '请输入活动地点', trigger: 'blur' }],
  start_time: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_time: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  signup_deadline: [{ required: true, message: '请选择报名截止时间', trigger: 'change' }]
}

function fmtForPicker(t) {
  // 后端时间 "2026-10-01T08:00:00" → 取前 19 位，与 picker 的 value-format 完全匹配
  // （之前用空格分隔 16 位格式，与 value-format 不匹配导致日期选择器显示空白）
  return t ? t.slice(0, 19) : ''
}

function openEdit(a) {
  editingId.value = a.id
  Object.assign(editForm, {
    title: a.title,
    description: a.description || '',
    image_urls: a.image_urls || [],
    location: a.location,
    start_time: fmtForPicker(a.start_time),
    end_time: fmtForPicker(a.end_time),
    signup_deadline: fmtForPicker(a.signup_deadline),
    max_participants: a.max_participants,
    group_info: a.group_info || '',
    group_qr_code: a.group_qr_code || ''
  })
  editDialogVisible.value = true
}

async function handleEditImageUpload(options) {
  const { file, onSuccess, onError } = options
  try {
    const data = await uploadActivityImage(file)
    editForm.image_urls.push(data.image_url)
    onSuccess(data)
  } catch (e) {
    onError(e)
  }
}

function removeEditImage(index) {
  editForm.image_urls.splice(index, 1)
}

async function handleEditQrUpload(options) {
  const { file, onSuccess, onError } = options
  try {
    const data = await uploadActivityImage(file)
    editForm.group_qr_code = data.image_url
    onSuccess(data)
  } catch (e) {
    onError(e)
  }
}

async function handleEditSubmit() {
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return
  editLoading.value = true
  try {
    await updateActivity(editingId.value, {
      title: editForm.title,
      description: editForm.description || undefined,
      image_urls: editForm.image_urls,
      location: editForm.location,
      start_time: editForm.start_time,
      end_time: editForm.end_time,
      signup_deadline: editForm.signup_deadline,
      max_participants: editForm.max_participants,
      group_info: editForm.group_info || undefined,
      group_qr_code: editForm.group_qr_code || undefined
    })
    ElMessage.success('活动已更新')
    editDialogVisible.value = false
    await load()
  } catch (e) {
    // 已提示
  } finally {
    editLoading.value = false
  }
}

const signupStatusText = { pending: '待确认', confirmed: '已确认', rejected: '已拒绝' }

async function load() {
  loading.value = true
  try {
    if (activeTab.value === 'activities') {
      activities.value = await listAllActivities()
    } else if (activeTab.value === 'signups') {
      signupRecords.value = await allSignups()
    } else if (activeTab.value === 'noshows') {
      noShows.value = await noShowRecords()
    } else {
      cancellations.value = await listCancellations()
    }
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
  dialogTitle.value = `「${a.title}」报名清单（${a.signup_count}/${a.max_participants}）`
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

// 报名审核：确认 / 拒绝（拒绝后用户不能再次报名）
async function reviewSignupItem(s, action) {
  try {
    await reviewSignup(s.id, { action })
    ElMessage.success(action === 'confirm' ? `已确认 ${s.user.real_name} 的报名` : `已拒绝 ${s.user.real_name} 的报名`)
    await load()
  } catch (e) {
    // 已提示
  }
}

async function toggleMalicious(c) {
  try {
    const data = await markMalicious(c.id, { is_malicious: !c.is_malicious })
    c.is_malicious = data.is_malicious
    ElMessage.success(data.is_malicious ? '已标记为恶意退出' : '已取消恶意标记')
  } catch (e) {
    // 已提示
  }
}

function fmtTime(t) {
  return t ? t.replace('T', ' ').slice(0, 16) : ''
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <el-tabs v-model="activeTab" @tab-change="load" stretch>
      <!-- Tab 1：活动管理 -->
      <el-tab-pane label="活动管理" name="activities">
        <el-card v-for="a in activities" :key="a.id" class="item-card">
          <div class="item-head">
            <h3>{{ a.title }}</h3>
          </div>
          <div class="item-meta">
            <div class="meta-line">
              <span>📍 {{ a.location }}</span>
              <span>🕐 {{ fmtTime(a.start_time) }}</span>
            </div>
            <div class="meta-line">
              <span>👥 {{ a.signup_count }}/{{ a.max_participants }}</span>
              <span>👁 {{ a.view_count }}</span>
            </div>
          </div>
          <div class="item-actions">
            <el-button size="small" type="warning" plain @click="openEdit(a)">编辑</el-button>
            <el-button size="small" type="primary" plain @click="showSignups(a)">实名报名清单</el-button>
            <el-button size="small" type="success" plain @click="showCheckins(a)">签到清单</el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(a)">删除</el-button>
          </div>
        </el-card>
        <el-empty v-if="!loading && activities.length === 0" description="还没有活动" />
      </el-tab-pane>

      <!-- Tab 2：报名信息（完整身份信息 + 确认/拒绝审核） -->
      <el-tab-pane label="报名信息" name="signups">
        <el-select v-model="signupFilter" placeholder="按活动筛选" clearable style="width: 100%; margin-bottom: 12px" @change="signupFilter = signupFilter || 0">
          <el-option label="全部活动" :value="0" />
          <el-option v-for="o in activityOptions" :key="o.id" :label="o.title" :value="o.id" />
        </el-select>
        <el-card v-for="s in filteredSignups" :key="s.id" class="item-card">
          <div class="item-head">
            <h3>{{ s.user.real_name }}（{{ s.user.nickname }}）</h3>
            <el-tag size="small">{{ s.activity.title }}</el-tag>
            <el-tag size="small" :type="s.status === 'pending' ? 'warning' : s.status === 'confirmed' ? 'success' : 'danger'">
              {{ signupStatusText[s.status] }}
            </el-tag>
          </div>
          <div class="info-grid">
            <span>性别：{{ s.user.gender }}</span>
            <span>学号：{{ s.user.student_id }}</span>
            <span>学院：{{ s.user.college }}</span>
            <span>手机号：{{ s.user.phone }}</span>
            <span>身份证号：{{ s.user.id_card }}</span>
            <span>微信：{{ s.user.wechat }}</span>
            <span>QQ：{{ s.user.qq }}</span>
            <span>报名时间：{{ fmtTime(s.created_at) }}</span>
          </div>
          <!-- 待确认的报名：管理员选择确认或拒绝 -->
          <div v-if="s.status === 'pending'" class="item-actions">
            <el-button size="small" type="success" @click="reviewSignupItem(s, 'confirm')">确认报名</el-button>
            <el-button size="small" type="danger" plain @click="reviewSignupItem(s, 'reject')">拒绝报名</el-button>
          </div>
        </el-card>
        <el-empty v-if="!loading && filteredSignups.length === 0" description="暂无报名记录" />
      </el-tab-pane>

      <!-- Tab 3：违约记录（已确认报名但活动结束未签到） -->
      <el-tab-pane label="违约记录" name="noshows">
        <el-card class="stats-card">
          <template #header><b>违约次数清单</b></template>
          <el-table :data="noShowStats" size="small">
            <el-table-column label="用户">
              <template #default="{ row }">{{ row.nickname }}（{{ row.real_name }}）</template>
            </el-table-column>
            <el-table-column label="违约次数" align="center">
              <template #default="{ row }">
                <el-tag type="danger" size="small">{{ row.count }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="noShowStats.length === 0" description="暂无违约记录" :image-size="60" />
        </el-card>
        <el-card v-for="n in noShows" :key="n.id" class="item-card">
          <div class="item-head">
            <h3>{{ n.user.nickname }}（{{ n.user.real_name }}）</h3>
            <el-tag type="danger" size="small">未签到·违约</el-tag>
          </div>
          <div class="item-meta">
            <span>活动：{{ n.activity.title }}</span>
            <span>结束于：{{ fmtTime(n.activity.end_time) }}</span>
          </div>
        </el-card>
        <el-empty v-if="!loading && noShows.length === 0" description="暂无违约记录" />
      </el-tab-pane>

      <!-- Tab 4：退出记录（含按用户统计的退出次数清单） -->
      <el-tab-pane label="退出记录" name="cancellations">
        <!-- 统计清单：每个用户的退出次数 -->
        <el-card class="stats-card">
          <template #header><b>退出次数清单</b></template>
          <el-table :data="userStats" size="small">
            <el-table-column label="用户">
              <template #default="{ row }">{{ row.nickname }}（{{ row.real_name }}）</template>
            </el-table-column>
            <el-table-column label="退出总次数" align="center">
              <template #default="{ row }">{{ row.total }}</template>
            </el-table-column>
            <el-table-column label="恶意退出次数" align="center">
              <template #default="{ row }">
                <el-tag :type="row.malicious > 0 ? 'danger' : 'info'" size="small">
                  {{ row.malicious }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="userStats.length === 0" description="暂无退出记录" :image-size="60" />
        </el-card>

        <!-- 实时记录列表 -->
        <el-card v-for="c in cancellations" :key="c.id" class="item-card">
          <div class="item-head">
            <h3>{{ c.user.nickname }}（{{ c.user.real_name }}）</h3>
            <el-tag v-if="c.is_malicious" type="danger" size="small">恶意退出</el-tag>
          </div>
          <div class="item-meta">
            <span>活动：{{ c.activity.title }}</span>
            <span>退出时间：{{ fmtTime(c.created_at) }}</span>
          </div>
          <div class="cancel-reason">原因：{{ c.reason }}</div>
          <div class="item-actions">
            <el-button size="small" :type="c.is_malicious ? 'info' : 'danger'" plain @click="toggleMalicious(c)">
              {{ c.is_malicious ? '取消恶意标记' : '标记恶意退出' }}
            </el-button>
          </div>
        </el-card>
        <el-empty v-if="!loading && cancellations.length === 0" description="暂无退出记录" />
      </el-tab-pane>
    </el-tabs>

    <!-- 编辑活动弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑活动" width="90%">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="90px">
        <el-form-item label="活动名称" prop="title">
          <el-input v-model="editForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="活动介绍">
          <el-input v-model="editForm.description" type="textarea" :rows="2" maxlength="2000" />
        </el-form-item>
        <el-form-item label="活动图片">
          <div class="upload-row">
            <el-upload :http-request="handleEditImageUpload" :show-file-list="false" accept="image/png,image/jpeg" multiple>
              <el-button size="small">+ 添加图片</el-button>
            </el-upload>
            <div v-for="(img, i) in editForm.image_urls" :key="img" class="thumb">
              <img :src="img" />
              <el-button class="thumb-del" size="small" circle type="danger" @click="removeEditImage(i)">✕</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="活动地点" prop="location">
          <el-input v-model="editForm.location" maxlength="255" />
        </el-form-item>
        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker v-model="editForm.start_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker v-model="editForm.end_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="报名截止" prop="signup_deadline">
          <el-date-picker v-model="editForm.signup_deadline" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="人数上限">
          <el-input-number v-model="editForm.max_participants" :min="1" :max="100000" />
        </el-form-item>
        <el-form-item label="加群方式">
          <el-input v-model="editForm.group_info" maxlength="255" placeholder="如：QQ群 123456789" />
        </el-form-item>
        <el-form-item label="群二维码">
          <div class="upload-row">
            <el-upload :http-request="handleEditQrUpload" :show-file-list="false" accept="image/png,image/jpeg">
              <el-button size="small">{{ editForm.group_qr_code ? '更换二维码' : '上传二维码' }}</el-button>
            </el-upload>
            <img v-if="editForm.group_qr_code" :src="editForm.group_qr_code" class="qr-thumb" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleEditSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 实名清单弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="95%">
      <el-table v-if="dialogMode === 'signups'" :data="dialogItems" size="small">
        <el-table-column prop="nickname" label="昵称" />
        <el-table-column prop="real_name" label="姓名" />
        <el-table-column prop="gender" label="性别" />
        <el-table-column prop="student_id" label="学号" />
        <el-table-column prop="college" label="学院" />
        <el-table-column prop="phone" label="手机号" />
        <el-table-column prop="id_card" label="身份证号" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag size="small">{{ signupStatusText[row.status] }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-else :data="dialogItems" size="small">
        <el-table-column prop="nickname" label="昵称" />
        <el-table-column prop="real_name" label="姓名" />
        <el-table-column prop="student_id" label="学号" />
        <el-table-column prop="college" label="学院" />
        <el-table-column prop="phone" label="手机号" />
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
.item-card {
  margin-bottom: 12px;
}
.item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.item-meta {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #606266;
  font-size: 13px;
}
.meta-line {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
/* 连体单元整体换行 */
.item-meta span {
  white-space: nowrap;
}
.item-actions {
  margin-top: 10px;
}
.info-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  color: #606266;
  font-size: 13px;
}
.cancel-reason {
  margin-top: 8px;
  color: #e6a23c;
  font-size: 13px;
}
.stats-card {
  margin-bottom: 12px;
}
.checkin-time {
  font-size: 11px;
  color: #909399;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
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
.qr-thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}
</style>
