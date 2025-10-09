import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import Login from '../views/Login.vue'
import ScriptExecution from '../views/ScriptExecution.vue'
import ExecutionHistory from '../views/ExecutionHistory.vue'
import AgentManagement from '../views/AgentManagement.vue'
import SimpleJobs from '../views/SimpleJobs.vue'
import Terminal from '../views/Terminal.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    redirect: '/script-execution'
  },
  {
    path: '/script-execution',
    name: 'ScriptExecution',
    component: ScriptExecution,
    meta: { requiresAuth: true }
  },
  {
    path: '/execution-history',
    name: 'ExecutionHistory',
    component: ExecutionHistory,
    meta: { requiresAuth: true }
  },
  {
    path: '/agent-management',
    name: 'AgentManagement',
    component: AgentManagement,
    meta: { requiresAuth: true }
  },
  {
    path: '/jobs',
    name: 'SimpleJobs',
    component: SimpleJobs,
    meta: { requiresAuth: true }
  },
  {
    path: '/terminal/:agentId',
    name: 'Terminal',
    component: Terminal,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：检查用户是否已登录
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('qunkong_token')
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
  
  if (requiresAuth && !token) {
    // 需要登录但未登录，跳转到登录页
    ElMessage.warning('请先登录')
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已登录用户访问登录页，跳转到首页
    next('/')
  } else {
    next()
  }
})

export default router
