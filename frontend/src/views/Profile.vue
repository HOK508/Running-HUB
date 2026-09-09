<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword, updateProfile } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { user, isAdmin, setAuth, clearAuth } = useAuth()

// 修改昵称
const nicknameDialog = ref(false)
const nickname = ref('')
const savingNickname = ref(false)

// 修改实名信息
const infoDialog = ref(false)
const infoForm = reactive({
  nickname: '',
  phone: '',
  real_name: '',
  gender: '',
  student_id: '',
  college: '',
  id_card: '',
  wechat: '',
  qq: ''
})
const savingInfo = ref(false)
const infoFormRef = ref()

const infoRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  student_id: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  college: [{ required: true, message: '请输入学院', trigger: 'blur' }],
  id_card: [
    { required: true, message: '请输入身份证号', trigger: 'blur' },
    { pattern: /^\d{17}[\dXx]$/, message: '身份证号格式不正确（18位）', trigger: 'blur' }
  ],
  wechat: [{ required: true, message: '请输入微信号', trigger: 'blur' }],
  qq: [{ required: true, message: '请输入QQ号', trigger: 'blur' }]
}

function openInfoEdit() {
  const u = user.value || {}
  infoForm.nickname = u.nickname || ''
  infoForm.phone = u.phone || ''
  infoForm.real_name = u.real_name || ''
  infoForm.gender = u.gender || ''
  infoForm.student_id = u.student_id || ''
  infoForm.college = u.college || ''
  infoForm.id_card = u.id_card || ''
  infoForm.wechat = u.wechat || ''
  infoForm.qq = u.qq || ''
  infoDialog.value = true
}

async function saveInfo() {
  const valid = await infoFormRef.value.validate().catch(() => false)
  if (!valid) return
  savingInfo.value = true
  try {
    // 管理员只需要昵称（无实名信息）
    const payload = isAdmin.value
      ? { nickname: infoForm.nickname }
      : {
          nickname: infoForm.nickname,
          phone: infoForm.phone,
          real_name: infoForm.real_name,
          gender: infoForm.gender,
          student_id: infoForm.student_id,
          college: infoForm.college,
          id_card: infoForm.id_card,
          wechat: infoForm.wechat,
          qq: infoForm.qq
        }
    const data = await updateProfile(payload)
    setAuth({ token: localStorage.getItem('token'), user: data })
    ElMessage.success('信息已更新')
    infoDialog.value = false
  } catch (e) {
    // 已提示
  } finally {
    savingInfo.value = false
  }
}

// 修改密码
const passwordDialog = ref(false)
const passwordForm = reactive({ old_password: '', new_password: '', confirm: '' })
const savingPassword = ref(false)
const passwordFormRef = ref()

const passwordRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 32, message: '6~32 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        value === passwordForm.new_password ? callback() : callback(new Error('两次输入的密码不一致'))
      },
      trigger: 'blur'
    }
  ]
}

function openNickname() {
  nickname.value = user.value?.nickname || ''
  nicknameDialog.value = true
}

async function saveNickname() {
  savingNickname.value = true
  try {
    const data = await updateProfile({ nickname: nickname.value })
    setAuth({ token: localStorage.getItem('token'), user: data })
    ElMessage.success('昵称已更新')
    nicknameDialog.value = false
  } catch (e) {
    // 已提示
  } finally {
    savingNickname.value = false
  }
}

async function savePassword() {
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return
  savingPassword.value = true
  try {
    await changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    ElMessage.success('密码修改成功')
    passwordDialog.value = false
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm = ''
  } catch (e) {
    // 已提示
  } finally {
    savingPassword.value = false
  }
}

function logout() {
  clearAuth()
  router.push('/login')
}
</script>

<template>
  <div>
    <!-- 个人信息卡片 -->
    <el-card class="user-card">
      <div class="user-head">
        <div class="avatar">{{ (user?.nickname || '跑')[0] }}</div>
        <div class="user-info">
          <div class="nickname">
            {{ user?.nickname }}
            <el-button link type="primary" size="small" @click="openNickname">编辑</el-button>
          </div>
          <div class="sub" v-if="user?.real_name">{{ user?.real_name }}（{{ user?.gender }}）· {{ user?.college }}</div>
          <div class="sub" v-else>管理员席位</div>
        </div>
      </div>
      <el-descriptions :column="1" size="small" class="user-detail">
        <el-descriptions-item label="userid">{{ user?.id }}</el-descriptions-item>
        <!-- 管理员只有序号；学生展示完整实名信息 -->
        <el-descriptions-item v-if="isAdmin" label="管理员序号">{{ user?.phone }}</el-descriptions-item>
        <template v-else>
          <el-descriptions-item label="学号">{{ user?.student_id }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ user?.phone }}</el-descriptions-item>
          <el-descriptions-item label="微信">{{ user?.wechat }}</el-descriptions-item>
          <el-descriptions-item label="QQ">{{ user?.qq }}</el-descriptions-item>
        </template>
      </el-descriptions>
    </el-card>

    <!-- 功能入口：管理员只保留修改信息/修改密码（管理功能走 TabBar） -->
    <el-card class="menu-card">
      <div class="menu-item" @click="openInfoEdit">
        <span>✏️ 修改信息</span><span class="arrow">›</span>
      </div>
      <div class="menu-item" @click="passwordDialog = true">
        <span>🔒 修改密码</span><span class="arrow">›</span>
      </div>
      <div v-if="!isAdmin" class="menu-item" @click="logout">
        <span style="color: #f56c6c">退出登录</span><span class="arrow">›</span>
      </div>
    </el-card>

    <!-- 管理员退出入口（菜单外独立按钮） -->
    <el-button v-if="isAdmin" class="logout-btn" @click="logout">退出登录</el-button>

    <!-- 修改昵称 -->
    <el-dialog v-model="nicknameDialog" title="修改昵称" width="85%">
      <el-input v-model="nickname" placeholder="昵称" maxlength="50" />
      <template #footer>
        <el-button @click="nicknameDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingNickname" @click="saveNickname">保存</el-button>
      </template>
    </el-dialog>

    <!-- 修改实名信息 -->
    <el-dialog v-model="infoDialog" title="修改信息" width="90%">
      <el-form ref="infoFormRef" :model="infoForm" :rules="infoRules" label-width="90px">
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="infoForm.nickname" maxlength="50" />
        </el-form-item>
        <!-- 管理员无实名信息，仅昵称可改 -->
        <template v-if="!isAdmin">
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="infoForm.phone" type="tel" maxlength="11" />
          <div class="field-tip">手机号是登录账号，修改后下次用新手机号登录</div>
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="infoForm.real_name" maxlength="50" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-select v-model="infoForm.gender" placeholder="请选择性别" style="width: 100%">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item label="学号" prop="student_id">
          <el-input v-model="infoForm.student_id" maxlength="30" />
        </el-form-item>
        <el-form-item label="学院" prop="college">
          <el-input v-model="infoForm.college" maxlength="100" />
        </el-form-item>
        <el-form-item label="身份证号" prop="id_card">
          <el-input v-model="infoForm.id_card" maxlength="18" />
        </el-form-item>
        <el-form-item label="微信号" prop="wechat">
          <el-input v-model="infoForm.wechat" maxlength="50" />
        </el-form-item>
        <el-form-item label="QQ号" prop="qq">
          <el-input v-model="infoForm.qq" maxlength="20" />
        </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="infoDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingInfo" @click="saveInfo">保存</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码 -->
    <el-dialog v-model="passwordDialog" title="修改密码" width="85%">
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px">
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="6~32 位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm">
          <el-input v-model="passwordForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingPassword" @click="savePassword">修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.user-card {
  border-radius: 12px;
  margin-bottom: 12px;
}
.user-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nickname {
  font-size: 17px;
  font-weight: 600;
}
.sub {
  color: #909399;
  font-size: 13px;
  margin-top: 2px;
}
.user-detail {
  margin-top: 4px;
}
.menu-card {
  border-radius: 12px;
  padding: 0;
}
.menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 4px;
  border-bottom: 1px solid #f5f7fa;
  cursor: pointer;
  font-size: 15px;
}
.menu-item:last-child {
  border-bottom: none;
}
.arrow {
  color: #c0c4cc;
  font-size: 18px;
}
.logout-btn {
  width: 100%;
  margin-top: 12px;
}
.field-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
</style>
