<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createActivity, uploadActivityImage } from '../api/activities'

const router = useRouter()
const loading = ref(false)
const formRef = ref()

const form = reactive({
  title: '',
  description: '',
  location: '',
  start_time: '',
  end_time: '',
  signup_deadline: '',
  max_participants: 20,
  group_info: ''
})
const imageUrls = ref([])
const qrCodeUrl = ref('')

const rules = {
  title: [{ required: true, message: '请输入活动名称', trigger: 'blur' }],
  location: [{ required: true, message: '请输入活动地点', trigger: 'blur' }],
  start_time: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_time: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  signup_deadline: [{ required: true, message: '请选择报名截止时间', trigger: 'change' }],
  max_participants: [{ required: true, message: '请输入人数上限', trigger: 'blur' }]
}

// 上传图片（选完立即上传，返回 URL 存列表）
async function handleImageUpload(options) {
  const { file, onSuccess, onError } = options
  try {
    const data = await uploadActivityImage(file)
    imageUrls.value.push(data.image_url)
    onSuccess(data)
  } catch (e) {
    onError(e)
  }
}

async function handleQrUpload(options) {
  const { file, onSuccess, onError } = options
  try {
    const data = await uploadActivityImage(file)
    qrCodeUrl.value = data.image_url
    onSuccess(data)
  } catch (e) {
    onError(e)
  }
}

function removeImage(index) {
  imageUrls.value.splice(index, 1)
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await createActivity({
      title: form.title,
      description: form.description || undefined,
      image_urls: imageUrls.value,
      location: form.location,
      start_time: form.start_time,
      end_time: form.end_time,
      signup_deadline: form.signup_deadline,
      max_participants: form.max_participants,
      group_info: form.group_info || undefined,
      group_qr_code: qrCodeUrl.value || undefined
    })
    ElMessage.success('活动创建成功，等待管理员审核')
    router.push('/my/activities')
  } catch (e) {
    // 错误已由拦截器提示
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <el-card>
      <template #header><b>发起活动</b></template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="create-form">
        <el-form-item label="活动名称" prop="title">
          <el-input v-model="form.title" placeholder="如：周末环湖约跑" />
        </el-form-item>
        <el-form-item label="活动介绍" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="文字说明活动内容（选填）" />
        </el-form-item>
        <el-form-item label="活动图片">
          <div class="upload-row">
            <el-upload :http-request="handleImageUpload" :show-file-list="false" accept="image/png,image/jpeg" multiple>
              <el-button>+ 上传图片（最多 9 张）</el-button>
            </el-upload>
            <div v-for="(img, i) in imageUrls" :key="img" class="thumb">
              <img :src="img" />
              <el-button class="thumb-del" size="small" circle type="danger" @click="removeImage(i)">✕</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="活动地点" prop="location">
          <el-input v-model="form.location" placeholder="如：学校田径场" />
        </el-form-item>
        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="选择开始时间" />
        </el-form-item>
        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="选择结束时间" />
        </el-form-item>
        <el-form-item label="报名截止" prop="signup_deadline">
          <el-date-picker v-model="form.signup_deadline" type="datetime" placeholder="选择报名截止时间" />
        </el-form-item>
        <el-form-item label="人数上限" prop="max_participants">
          <el-input-number v-model="form.max_participants" :min="1" :max="100000" />
        </el-form-item>
        <el-form-item label="加群方式">
          <el-input v-model="form.group_info" placeholder="如：QQ群 123456789 或微信群号（选填）" />
        </el-form-item>
        <el-form-item label="群二维码">
          <div class="upload-row">
            <el-upload :http-request="handleQrUpload" :show-file-list="false" accept="image/png,image/jpeg">
              <el-button>{{ qrCodeUrl ? '更换二维码' : '上传二维码（选填）' }}</el-button>
            </el-upload>
            <div v-if="qrCodeUrl" class="thumb">
              <img :src="qrCodeUrl" />
            </div>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">提交（需管理员审核）</el-button>
          <el-button @click="router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.create-form {
  max-width: 600px;
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
</style>
