<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo-container">
          <img src="/logo.svg" alt="Qunkong" class="logo" />
          <h1 class="title">Qunkong</h1>
        </div>
        <p class="subtitle">分布式脚本执行系统</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名或邮箱"
            size="large"
            :prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <div class="login-options">
            <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
            <el-link type="primary" @click="showRegisterDialog = true">
              注册账号
            </el-link>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loginLoading"
            @click="handleLogin"
            class="login-button"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p>默认管理员账户: admin / admin123</p>
      </div>
    </div>

    <!-- 注册对话框 -->
    <el-dialog
      v-model="showRegisterDialog"
      title="注册账号"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-width="80px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名"
            maxlength="20"
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="请输入邮箱地址"
            type="email"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showRegisterDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="registerLoading"
          @click="handleRegister"
        >
          注册
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '../api'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const loginFormRef = ref()
    const registerFormRef = ref()
    const loginLoading = ref(false)
    const registerLoading = ref(false)
    const showRegisterDialog = ref(false)

    const loginForm = reactive({
      username: '',
      password: '',
      remember: false
    })

    const registerForm = reactive({
      username: '',
      email: '',
      password: '',
      confirmPassword: ''
    })

    const loginRules = {
      username: [
        { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' }
      ]
    }

    const registerRules = {
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
      ],
      email: [
        { required: true, message: '请输入邮箱地址', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: '请再次输入密码', trigger: 'blur' },
        {
          validator: (rule, value, callback) => {
            if (value !== registerForm.password) {
              callback(new Error('两次输入的密码不一致'))
            } else {
              callback()
            }
          },
          trigger: 'blur'
        }
      ]
    }

    const handleLogin = async () => {
      if (!loginFormRef.value) return

      try {
        await loginFormRef.value.validate()
        loginLoading.value = true

        const response = await authApi.login({
          username: loginForm.username,
          password: loginForm.password
        })

        // 保存用户信息和令牌
        localStorage.setItem('qunkong_token', response.token)
        localStorage.setItem('qunkong_user', JSON.stringify(response.user))

        if (loginForm.remember) {
          localStorage.setItem('qunkong_remember', 'true')
        }

        ElMessage.success('登录成功')
        router.push('/')

      } catch (error) {
        ElMessage.error(error.message || '登录失败')
      } finally {
        loginLoading.value = false
      }
    }

    const handleRegister = async () => {
      if (!registerFormRef.value) return

      try {
        await registerFormRef.value.validate()
        registerLoading.value = true

        await authApi.register({
          username: registerForm.username,
          email: registerForm.email,
          password: registerForm.password,
          confirm_password: registerForm.confirmPassword
        })

        ElMessage.success('注册成功，请登录')
        showRegisterDialog.value = false

        // 清空注册表单
        registerForm.username = ''
        registerForm.email = ''
        registerForm.password = ''
        registerForm.confirmPassword = ''

      } catch (error) {
        ElMessage.error(error.message || '注册失败')
      } finally {
        registerLoading.value = false
      }
    }

    // 检查是否已登录
    onMounted(() => {
      const token = localStorage.getItem('qunkong_token')
      if (token) {
        // 验证令牌是否有效
        authApi.verifyToken().then(() => {
          router.push('/')
        }).catch(() => {
          // 令牌无效，清除本地存储
          localStorage.removeItem('qunkong_token')
          localStorage.removeItem('qunkong_user')
        })
      }
    })

    return {
      loginFormRef,
      registerFormRef,
      loginForm,
      registerForm,
      loginRules,
      registerRules,
      loginLoading,
      registerLoading,
      showRegisterDialog,
      handleLogin,
      handleRegister,
      User,
      Lock
    }
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-box {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  padding: 40px;
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.logo {
  height: 48px;
  margin-right: 12px;
}

.title {
  font-size: 32px;
  font-weight: 600;
  color: #1890ff;
  margin: 0;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 8px 0 0 0;
}

.login-form {
  margin-bottom: 20px;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.login-button {
  width: 100%;
  height: 44px;
  font-size: 16px;
}

.login-footer {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 20px;
}

.login-footer p {
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .login-container {
    padding: 10px;
  }
  
  .login-box {
    padding: 30px 20px;
  }
  
  .title {
    font-size: 28px;
  }
}
</style>