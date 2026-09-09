<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api/auth'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const router = useRouter()
const { setAuth } = useAuth()

const activeTab = ref('login')
const loading = ref(false)
const loginFormRef = ref()
const registerFormRef = ref()

const loginForm = reactive({ phone: '', password: '' })
const registerForm = reactive({
  phone: '',
  password: '',
  confirm: '',
  nickname: '',
  real_name: '',
  gender: '',
  student_id: '',
  college: '',
  id_card: '',
  wechat: '',
  qq: ''
})

const loginRules = {
  phone: [
    { required: true, message: '请输入手机号或管理员序号', trigger: 'blur' },
    { pattern: /^(1\d{10}|00[0-4])$/, message: '格式不正确', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}
const registerRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 6, max: 32, message: '6~32 位', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        value === registerForm.password ? callback() : callback(new Error('两次输入的密码不一致'))
      },
      trigger: 'blur'
    }
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

function afterAuth(data) {
  setAuth(data)
  ElMessage.success('欢迎回来')
  router.push(route.query.redirect || '/')
}

async function handleLogin() {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    afterAuth(await login({ phone: loginForm.phone, password: loginForm.password }))
  } catch (e) {
    // 错误提示已由 axios 拦截器统一弹出
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const data = await register({
      phone: registerForm.phone,
      password: registerForm.password,
      nickname: registerForm.nickname || undefined,
      real_name: registerForm.real_name,
      gender: registerForm.gender,
      student_id: registerForm.student_id,
      college: registerForm.college,
      id_card: registerForm.id_card,
      wechat: registerForm.wechat,
      qq: registerForm.qq
    })
    afterAuth(data)
  } catch (e) {
    // 错误提示已由 axios 拦截器统一弹出
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="brand">
      <div class="brand-logo">🏃</div>
      <h1>RUNing HUB</h1>
    </div>

    <el-card class="login-card">
      <el-tabs v-model="activeTab" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-width="0">
            <el-form-item prop="phone">
              <el-input
                v-model="loginForm.phone"
                placeholder="手机号 / 管理员序号"
                type="tel"
                maxlength="11"
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="密码" show-password @keyup.enter="handleLogin" />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="handleLogin">登 录</el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-width="0">
            <p class="section-title">账号信息</p>
            <el-form-item prop="phone">
              <el-input v-model="registerForm.phone" placeholder="手机号（登录账号）" type="tel" maxlength="11" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="设置密码（6~32 位）" show-password />
            </el-form-item>
            <el-form-item prop="confirm">
              <el-input v-model="registerForm.confirm" type="password" placeholder="确认密码" show-password />
            </el-form-item>
            <el-form-item prop="nickname">
              <el-input v-model="registerForm.nickname" placeholder="昵称（选填，留空默认 跑友+尾号）" maxlength="50" />
            </el-form-item>

            <p class="section-title">实名信息（一个 userid 对应一个人）</p>
            <el-form-item prop="real_name">
              <el-input v-model="registerForm.real_name" placeholder="真实姓名" maxlength="50" />
            </el-form-item>
            <el-form-item prop="gender">
              <el-select v-model="registerForm.gender" placeholder="请选择性别" style="width: 100%">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
            <el-form-item prop="student_id">
              <el-input v-model="registerForm.student_id" placeholder="学号" maxlength="30" />
            </el-form-item>
            <el-form-item prop="college">
              <el-input v-model="registerForm.college" placeholder="学院" maxlength="100" />
            </el-form-item>
            <el-form-item prop="id_card">
              <el-input v-model="registerForm.id_card" placeholder="身份证号（18位）" maxlength="18" />
            </el-form-item>
            <el-form-item prop="wechat">
              <el-input v-model="registerForm.wechat" placeholder="微信号" maxlength="50" />
            </el-form-item>
            <el-form-item prop="qq">
              <el-input v-model="registerForm.qq" placeholder="QQ号" maxlength="20" />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="handleRegister">注 册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #409eff 0%, #79bbff 45%, #eef1f5 45%);
  padding: 40px 16px 24px;
}
.brand {
  text-align: center;
  color: #fff;
  margin-bottom: 24px;
}
.brand-logo {
  font-size: 48px;
}
.brand h1 {
  font-size: 26px;
  margin-top: 4px;
}
.brand p {
  font-size: 13px;
  opacity: 0.9;
}
.login-card {
  border-radius: 12px;
}
.submit-btn {
  width: 100%;
  height: 40px;
}
.section-title {
  font-size: 13px;
  color: #909399;
  margin: 4px 0 8px;
}
</style>
