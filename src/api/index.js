import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 从localStorage获取token并添加到请求头
    const token = localStorage.getItem('qunkong_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API 接口
export const scriptApi = {
  // 执行脚本
  executeScript: (data) => api.post('/execute', data),
  
  // 获取任务列表
  getTasks: () => api.get('/tasks'),
  
  // 获取任务详情
  getTaskDetails: (taskId) => api.get(`/tasks/${taskId}`),
  
  // 重试任务
  retryTask: (taskId) => api.post(`/tasks/${taskId}/retry`),
  
  // 停止任务
  stopTask: (taskId) => api.post(`/tasks/${taskId}/stop`)
}

export const agentApi = {
  // 获取Agent列表
  getAgents: () => api.get('/agents'),
  
  // 获取服务器列表
  getServers: () => api.get('/servers'),
  
  // 获取Agent详情
  getAgentDetails: (agentId) => api.get(`/agents/${agentId}`),
  
  // 获取Agent的执行历史
  getAgentTasks: (agentId) => api.get(`/agents/${agentId}/tasks`),
  
  // 重启Agent
  restartAgent: (agentId) => api.post(`/agents/${agentId}/restart`),
  
  // 重启主机
  restartHost: (agentId) => api.post(`/agents/${agentId}/restart-host`),
  
  // 批量管理Agent
  batchManageAgents: (data) => api.post('/agents/batch', data),
  
  // 清理离线Agent
  cleanupOfflineAgents: (offlineHours) => api.post('/agents/cleanup', { offline_hours: offlineHours })
}

export const authApi = {
  // 用户注册
  register: (data) => api.post('/auth/register', data),
  
  // 用户登录
  login: (data) => api.post('/auth/login', data),
  
  // 用户登出
  logout: () => api.post('/auth/logout'),
  
  // 获取用户信息
  getProfile: () => api.get('/auth/profile'),
  
  // 验证令牌
  verifyToken: () => api.post('/auth/verify'),
  
  // 修改密码
  changePassword: (data) => api.post('/auth/change-password', data)
}

export const jobsApi = {
  // 获取作业模板列表
  getJobTemplates: (params) => api.get('/jobs/templates', { params }),
  
  // 获取作业模板详情
  getJobTemplate: (templateId) => api.get(`/jobs/templates/${templateId}`),
  
  // 创建作业模板
  createJobTemplate: (data) => api.post('/jobs/templates', data),
  
  // 获取作业实例列表
  getJobInstances: (params) => api.get('/jobs/instances', { params }),
  
  // 获取作业实例详情
  getJobInstance: (jobId) => api.get(`/jobs/instances/${jobId}`),
  
  // 创建作业实例
  createJobInstance: (data) => api.post('/jobs/instances', data),
  
  // 执行作业实例
  executeJobInstance: (jobId) => api.post(`/jobs/instances/${jobId}/execute`),
  
  // 停止作业实例
  stopJobInstance: (jobId) => api.post(`/jobs/instances/${jobId}/stop`),
  
  // 获取作业分类
  getJobCategories: () => api.get('/jobs/categories'),
  
  // 获取步骤类型
  getStepTypes: () => api.get('/jobs/step-types')
}

// 简单作业API
export const simpleJobsApi = {
  // 获取作业列表
  getJobs: (params) => api.get('/simple-jobs', { params }),
  
  // 获取作业详情
  getJob: (jobId) => api.get(`/simple-jobs/${jobId}`),
  
  // 创建作业
  createJob: (data) => api.post('/simple-jobs', data),
  
  // 更新作业
  updateJob: (jobId, data) => api.put(`/simple-jobs/${jobId}`, data),
  
  // 删除作业
  deleteJob: (jobId) => api.delete(`/simple-jobs/${jobId}`),
  
  // 添加步骤
  addStep: (jobId, data) => api.post(`/simple-jobs/${jobId}/steps`, data),
  
  // 更新步骤
  updateStep: (jobId, stepId, data) => api.put(`/simple-jobs/${jobId}/steps/${stepId}`, data),
  
  // 删除步骤
  deleteStep: (jobId, stepId) => api.delete(`/simple-jobs/${jobId}/steps/${stepId}`),
  
  // 执行作业
  executeJob: (jobId) => api.post(`/simple-jobs/${jobId}/execute`),
  
  // 获取执行记录
  getExecution: (executionId) => api.get(`/simple-jobs/executions/${executionId}`),
  
  // 获取执行历史
  getExecutions: (params) => api.get('/simple-jobs/executions', { params })
}

export default api
