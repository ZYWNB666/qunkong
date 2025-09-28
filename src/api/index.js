import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
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
  getAgentTasks: (agentId) => api.get(`/agents/${agentId}/tasks`)
}

export default api
