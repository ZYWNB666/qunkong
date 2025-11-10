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
    
    // 自动添加project_id到请求（排除某些不需要项目的接口）
    const noProjectUrls = ['/auth/login', '/auth/register', '/auth/logout', '/auth/verify', '/projects/my-projects']
    const needsProject = !noProjectUrls.some(url => config.url.includes(url))
    
    if (needsProject) {
      const currentProject = JSON.parse(localStorage.getItem('qunkong_current_project') || '{}')
      if (currentProject.id) {
        // GET请求添加到params
        if (config.method === 'get' && !config.params?.project_id) {
          config.params = config.params || {}
          config.params.project_id = currentProject.id
        }
        // POST/PUT/PATCH请求添加到data
        else if (['post', 'put', 'patch'].includes(config.method)) {
          // 确保 data 存在且是对象
          if (typeof config.data === 'object' && config.data !== null && !Array.isArray(config.data)) {
            if (!config.data.project_id) {
              config.data.project_id = currentProject.id
            }
          } else if (!config.data) {
            config.data = { project_id: currentProject.id }
          }
        }
      }
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
    
    // 处理 401 未授权错误
    if (error.response && error.response.status === 401) {
      // 清除本地存储
      localStorage.removeItem('qunkong_token')
      localStorage.removeItem('qunkong_user')
      localStorage.removeItem('qunkong_current_project')
      
      // 只在非登录页面时跳转
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    
    return Promise.reject(error)
  }
)

// API 接口
export const scriptApi = {
  executeScript: (data) => api.post('/execute', data),
  getTasks: () => api.get('/tasks'),
  getTaskDetails: (taskId) => api.get(`/tasks/${taskId}`),
  retryTask: (taskId) => api.post(`/tasks/${taskId}/retry`),
  stopTask: (taskId) => api.post(`/tasks/${taskId}/stop`)
}

export const agentApi = {
  getAgents: () => api.get('/agents'),
  getServers: () => api.get('/servers'),
  getAgentDetails: (agentId) => api.get(`/agents/${agentId}`),
  getAgentTasks: (agentId) => api.get(`/agents/${agentId}/tasks`),
  restartAgent: (agentId) => api.post(`/agents/${agentId}/restart`),
  restartHost: (agentId) => api.post(`/agents/${agentId}/restart-host`),
  batchManageAgents: (data) => api.post('/agents/batch', data),
  cleanupOfflineAgents: (offlineHours) => api.post('/agents/cleanup', { offline_hours: offlineHours })
}

export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getProfile: () => api.get('/auth/profile'),
  verifyToken: () => api.post('/auth/verify'),
  changePassword: (data) => api.post('/auth/change-password', data)
}

export const jobsApi = {
  getJobTemplates: (params) => api.get('/jobs/templates', { params }),
  getJobTemplate: (templateId) => api.get(`/jobs/templates/${templateId}`),
  createJobTemplate: (data) => api.post('/jobs/templates', data),
  getJobInstances: (params) => api.get('/jobs/instances', { params }),
  getJobInstance: (jobId) => api.get(`/jobs/instances/${jobId}`),
  createJobInstance: (data) => api.post('/jobs/instances', data),
  executeJobInstance: (jobId) => api.post(`/jobs/instances/${jobId}/execute`),
  stopJobInstance: (jobId) => api.post(`/jobs/instances/${jobId}/stop`),
  getJobCategories: () => api.get('/jobs/categories'),
  getStepTypes: () => api.get('/jobs/step-types')
}

export const simpleJobsApi = {
  getJobs: (params) => api.get('/simple-jobs', { params }),
  getJob: (jobId) => api.get(`/simple-jobs/${jobId}`),
  createJob: (data) => api.post('/simple-jobs', data),
  updateJob: (jobId, data) => api.put(`/simple-jobs/${jobId}`, data),
  deleteJob: (jobId) => api.delete(`/simple-jobs/${jobId}`),
  addStep: (jobId, data) => api.post(`/simple-jobs/${jobId}/steps`, data),
  updateStep: (jobId, stepId, data) => api.put(`/simple-jobs/${jobId}/steps/${stepId}`, data),
  deleteStep: (jobId, stepId) => api.delete(`/simple-jobs/${jobId}/steps/${stepId}`),
  executeJob: (jobId) => api.post(`/simple-jobs/${jobId}/execute`),
  getExecution: (executionId) => api.get(`/simple-jobs/executions/${executionId}`),
  getExecutions: (params) => api.get('/simple-jobs/executions', { params })
}

export const usersApi = {
  getUsers: (params) => api.get('/users', { params }),
  getUser: (userId) => api.get(`/users/${userId}`),
  createUser: (data) => api.post('/users', data),
  updateUser: (userId, data) => api.put(`/users/${userId}`, data),
  deleteUser: (userId) => api.delete(`/users/${userId}`),
  changePassword: (userId, data) => api.put(`/users/${userId}/password`, data),
  updateUserRole: (userId, data) => api.put(`/users/${userId}/role`, data),
  updateUserStatus: (userId, data) => api.put(`/users/${userId}/status`, data),
  getUserStats: () => api.get('/users/stats')
}

export const tenantsApi = {
  getTenants: (params) => api.get('/tenants', { params }),
  getTenant: (tenantId) => api.get(`/tenants/${tenantId}`),
  getMyTenants: () => api.get('/tenants/my-tenants'),
  createTenant: (data) => api.post('/tenants', data),
  updateTenant: (tenantId, data) => api.put(`/tenants/${tenantId}`, data),
  deleteTenant: (tenantId) => api.delete(`/tenants/${tenantId}`),
  getTenantMembers: (tenantId) => api.get(`/tenants/${tenantId}/members`),
  addTenantMember: (tenantId, data) => api.post(`/tenants/${tenantId}/members`, data),
  updateMemberRole: (tenantId, userId, data) => api.put(`/tenants/${tenantId}/members/${userId}/role`, data),
  removeTenantMember: (tenantId, userId) => api.delete(`/tenants/${tenantId}/members/${userId}`)
}

export const projectsApi = {
  getProjects: (params) => api.get('/projects', { params }),
  getProject: (projectId) => api.get(`/projects/${projectId}`),
  createProject: (data) => api.post('/projects', data),
  updateProject: (projectId, data) => api.put(`/projects/${projectId}`, data),
  deleteProject: (projectId) => api.delete(`/projects/${projectId}`),
  getProjectMembers: (projectId) => api.get(`/projects/${projectId}/members`),
  addProjectMember: (projectId, data) => api.post(`/projects/${projectId}/members`, data),
  removeProjectMember: (projectId, userId) => api.delete(`/projects/${projectId}/members/${userId}`),
  updateMemberRole: (projectId, userId, data) => api.put(`/projects/${projectId}/members/${userId}/role`, data),
  getMyProjects: () => api.get('/projects/my-projects')
}

export default api

