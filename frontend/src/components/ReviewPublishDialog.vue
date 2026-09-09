<script setup>
// 发布回顾帖弹窗（公共组件）：活动详情页 + 管理面板共用
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadActivityImage } from '../api/activities'
import { publishReview } from '../api/posts'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  activityId: { type: Number, required: true }
})
const emit = defineEmits(['update:modelValue', 'published'])

const loading = ref(false)
const content = ref('')
const imageUrls = ref([])

// 每次打开重置表单
watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      content.value = ''
      imageUrls.value = []
    }
  }
)

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

function removeImage(index) {
  imageUrls.value.splice(index, 1)
}

async function handlePublish() {
  if (!content.value.trim()) {
    ElMessage.warning('请填写活动总结内容')
    return
  }
  loading.value = true
  try {
    await publishReview(props.activityId, {
      content: content.value.trim(),
      image_urls: imageUrls.value
    })
    ElMessage.success('回顾已发布')
    emit('update:modelValue', false)
    emit('published')
  } catch (e) {
    // 已提示
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="发布活动回顾"
    width="90%"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-input
      v-model="content"
      type="textarea"
      :rows="4"
      maxlength="2000"
      show-word-limit
      placeholder="介绍活动运行整体情况，如参与人数、氛围、成绩等"
    />
    <div class="upload-row">
      <el-upload
        :http-request="handleImageUpload"
        :show-file-list="false"
        accept="image/png,image/jpeg"
        multiple
      >
        <el-button size="small">+ 上传图片（最多 9 张）</el-button>
      </el-upload>
      <div v-for="(img, i) in imageUrls" :key="img" class="thumb">
        <img :src="img" />
        <el-button class="thumb-del" size="small" circle type="danger" @click="removeImage(i)">✕</el-button>
      </div>
    </div>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handlePublish">发布</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
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
</style>
