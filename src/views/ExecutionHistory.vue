<template>
  <div class="execution-history">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="page-title">执行历史</span>
          <div class="header-actions">
            <el-select 
              v-model="refreshInterval" 
              @change="handleRefreshIntervalChange"
              size="small"
              style="width: 140px"
            >
              <el-option label="关闭自动刷新" :value="0" />
              <el-option label="1秒刷新" :value="1000" />
              <el-option label="3秒刷新" :value="3000" />
              <el-option label="5秒刷新" :value="5000" />
              <el-option label="10秒刷新" :value="10000" />
            </el-select>
            <el-tag 
              :type="refreshInterval > 0 ? 'success' : 'info'" 
              size="small"
            >
              <el-icon><Clock /></el-icon>
              {{ refreshInterval > 0 ? `自动刷新中 (${refreshInterval/1000}s)` : '自动刷新已关闭' }}
            </el-tag>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-select v-model="filters.category" placeholder="全部类型" clearable>
              <el-option label="全部" value="" />
              <el-option label="快速执行" value="quick" />
              <el-option label="作业执行" value="job" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索任务ID，任务名称，执行方式，任务状态，执行人..."
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="6">
            <el-date-picker
              v-model="filters.dateRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </el-col>
          <el-col :span="6">
            <el-button type="primary" @click="loadTasks(true)" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="resetFilters">
              <el-icon><Delete /></el-icon>
              重置
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 任务列表 -->
      <el-table
        :data="filteredTasks"
        v-loading="loading"
        stripe
        style="width: 100%"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="id" label="ID" width="120" sortable="custom">
          <template #default="{ row }">
            <el-link type="primary" @click="viewTaskDetails(row)">
              {{ row.id.substring(0, 8) }}...
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column prop="script_name" label="任务名称" min-width="200" sortable="custom">
          <template #default="{ row }">
            <el-tooltip :content="row.script_name" placement="top">
              <span class="task-name">{{ row.script_name }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        
        <el-table-column prop="execution_type" label="执行方式" width="120">
          <template #default="{ row }">
            <el-tag type="info" size="small">快速执行</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="environment" label="环境" width="100">
          <template #default="{ row }">
            <el-tag type="warning" size="small">默认</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="任务状态" width="120" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="execution_user" label="执行人" width="120" />
        
        <el-table-column prop="created_at" label="开始时间" width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="耗时" width="120">
          <template #default="{ row }">
            {{ getDuration(row) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="text" @click="viewTaskDetails(row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button 
              v-if="row.status === 'RUNNING'" 
              type="text" 
              @click="stopTask(row)"
            >
              <el-icon><VideoPause /></el-icon>
              停止
            </el-button>
            <el-button 
              v-if="row.status === 'COMPLETED' || row.status === 'FAILED'" 
              type="text" 
              @click="retryTask(row)"
            >
              <el-icon><RefreshRight /></el-icon>
              重试
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="showTaskDialog"
      :title="`任务详情 - ${currentTask?.script_name || ''}`"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="currentTask" class="task-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">
            {{ currentTask.id }}
          </el-descriptions-item>
          <el-descriptions-item label="任务名称">
            {{ currentTask.script_name }}
          </el-descriptions-item>
          <el-descriptions-item label="执行状态">
            <el-tag :type="getStatusType(currentTask.status)">
              {{ getStatusText(currentTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行人">
            {{ currentTask.execution_user }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(currentTask.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(currentTask.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ formatDateTime(currentTask.completed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="超时设置">
            {{ currentTask.timeout }} 秒
          </el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <div class="script-content">
          <h4>脚本内容</h4>
          <el-input
            v-model="currentTask.script"
            type="textarea"
            :rows="10"
            readonly
            class="script-textarea"
          />
        </div>

        <div v-if="currentTask.script_params" class="script-params">
          <h4>脚本参数</h4>
          <el-input
            v-model="currentTask.script_params"
            readonly
            class="params-input"
          />
        </div>

        <div class="execution-results">
          <h4>执行结果</h4>
          <el-tabs v-model="activeResultTab">
            <el-tab-pane
              v-for="(result, agentId) in currentTask.results"
              :key="agentId"
              :label="getAgentName(agentId)"
              :name="agentId"
            >
              <div class="result-content">
                <el-descriptions :column="1" size="small">
                  <el-descriptions-item label="退出码">
                    <el-tag :type="result.exit_code === 0 ? 'success' : 'danger'">
                      {{ result.exit_code }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="执行时间">
                    {{ result.execution_time }} 秒
                  </el-descriptions-item>
                </el-descriptions>
                
                <div class="output-section">
                  <h5>标准输出</h5>
                  <el-input
                    v-model="result.stdout"
                    type="textarea"
                    :rows="8"
                    readonly
                    class="output-textarea"
                  />
                </div>
                
                <div v-if="result.stderr" class="output-section">
                  <h5>错误输出</h5>
                  <el-input
                    v-model="result.stderr"
                    type="textarea"
                    :rows="4"
                    readonly
                    class="error-textarea"
                  />
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { scriptApi, agentApi } from '../api'

export default {
  name: 'ExecutionHistory',
  setup() {
    const loading = ref(false)
    const tasks = ref([])
    const showTaskDialog = ref(false)
    const currentTask = ref(null)
    const activeResultTab = ref('')
    const refreshTimer = ref(null)
    const refreshInterval = ref(3000) // 默认3秒刷新
    const agents = ref([])

    const filters = reactive({
      category: '',
      keyword: '',
      dateRange: []
    })

    const pagination = reactive({
      currentPage: 1,
      pageSize: 10,
      total: 0
    })

    const sortConfig = reactive({
      prop: '',
      order: ''
    })

    const filteredTasks = computed(() => {
      let result = [...tasks.value]

      // 关键词搜索
      if (filters.keyword) {
        const keyword = filters.keyword.toLowerCase()
        result = result.filter(task => 
          task.id.toLowerCase().includes(keyword) ||
          task.script_name.toLowerCase().includes(keyword) ||
          task.execution_user.toLowerCase().includes(keyword) ||
          task.status.toLowerCase().includes(keyword)
        )
      }

      // 类型筛选
      if (filters.category) {
        // 这里可以根据实际需求添加类型筛选逻辑
      }

      // 日期范围筛选
      if (filters.dateRange && filters.dateRange.length === 2) {
        const [startDate, endDate] = filters.dateRange
        result = result.filter(task => {
          const taskDate = new Date(task.created_at)
          return taskDate >= new Date(startDate) && taskDate <= new Date(endDate)
        })
      }

      // 排序
      if (sortConfig.prop) {
        result.sort((a, b) => {
          let aVal = a[sortConfig.prop]
          let bVal = b[sortConfig.prop]

          if (sortConfig.prop === 'created_at' || sortConfig.prop === 'started_at') {
            aVal = new Date(aVal).getTime()
            bVal = new Date(bVal).getTime()
          }

          if (sortConfig.order === 'ascending') {
            return aVal > bVal ? 1 : -1
          } else {
            return aVal < bVal ? 1 : -1
          }
        })
      }

      // 分页
      const start = (pagination.currentPage - 1) * pagination.pageSize
      const end = start + pagination.pageSize
      return result.slice(start, end)
    })

    const loadTasks = async (showLoading = true) => {
      try {
        if (showLoading) {
          loading.value = true
        }
        const data = await scriptApi.getTasks()
        tasks.value = data
        pagination.total = data.length
      } catch (error) {
        ElMessage.error('加载任务列表失败')
      } finally {
        if (showLoading) {
          loading.value = false
        }
      }
    }

    const startAutoRefresh = (interval = refreshInterval.value) => {
      // 清除已存在的定时器
      stopAutoRefresh()
      
      // 如果间隔为0，则不启动定时器
      if (interval <= 0) {
        return
      }
      
      // 设置自动刷新
      refreshTimer.value = setInterval(() => {
        loadTasks(false) // 静默刷新，不显示loading
      }, interval)
    }

    const stopAutoRefresh = () => {
      if (refreshTimer.value) {
        clearInterval(refreshTimer.value)
        refreshTimer.value = null
      }
    }

    const handleRefreshIntervalChange = (newInterval) => {
      refreshInterval.value = newInterval
      
      // 保存用户偏好到本地存储
      localStorage.setItem('executionHistoryRefreshInterval', newInterval.toString())
      
      // 重新启动自动刷新
      startAutoRefresh(newInterval)
    }

    const loadUserPreferences = () => {
      // 从本地存储加载用户偏好
      const savedInterval = localStorage.getItem('executionHistoryRefreshInterval')
      if (savedInterval !== null) {
        refreshInterval.value = parseInt(savedInterval)
      }
    }

    const loadAgents = async () => {
      try {
        const data = await agentApi.getServers()
        agents.value = data
      } catch (error) {
        console.error('加载Agent信息失败:', error)
      }
    }

    const resetFilters = () => {
      filters.category = ''
      filters.keyword = ''
      filters.dateRange = []
      pagination.currentPage = 1
    }

    const handleSortChange = ({ prop, order }) => {
      sortConfig.prop = prop
      sortConfig.order = order
    }

    const handleSizeChange = (size) => {
      pagination.pageSize = size
      pagination.currentPage = 1
    }

    const handleCurrentChange = (page) => {
      pagination.currentPage = page
    }

    const viewTaskDetails = async (task) => {
      try {
        const data = await scriptApi.getTaskDetails(task.id)
        currentTask.value = data
        showTaskDialog.value = true
        
        // 设置默认激活的标签页
        if (data.results && Object.keys(data.results).length > 0) {
          activeResultTab.value = Object.keys(data.results)[0]
        }
      } catch (error) {
        ElMessage.error('获取任务详情失败')
      }
    }

    const stopTask = async (task) => {
      try {
        await ElMessageBox.confirm('确定要停止此任务吗？', '确认停止', {
          type: 'warning'
        })
        
        await scriptApi.stopTask(task.id)
        ElMessage.success('任务已停止')
        
        // 刷新任务列表
        await loadTasks()
      } catch (error) {
        if (error.message && error.message !== 'cancel') {
          ElMessage.error('停止任务失败: ' + error.message)
        }
      }
    }

    const retryTask = async (task) => {
      try {
        await ElMessageBox.confirm('确定要重试此任务吗？', '确认重试', {
          type: 'warning'
        })
        
        const result = await scriptApi.retryTask(task.id)
        ElMessage.success('任务重试已启动')
        
        // 刷新任务列表
        await loadTasks()
      } catch (error) {
        if (error.message && error.message !== 'cancel') {
          ElMessage.error('重试任务失败: ' + error.message)
        }
      }
    }

    const getStatusType = (status) => {
      const statusMap = {
        'PENDING': 'info',
        'RUNNING': 'warning',
        'COMPLETED': 'success',
        'SUCCEED': 'success',
        'FAILED': 'danger'
      }
      return statusMap[status] || 'info'
    }

    const getStatusText = (status) => {
      const statusMap = {
        'PENDING': '等待中',
        'RUNNING': '执行中',
        'COMPLETED': '已完成',
        'SUCCEED': '成功',
        'FAILED': '失败'
      }
      return statusMap[status] || status
    }

    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-'
      return new Date(dateTime).toLocaleString('zh-CN')
    }

    const getDuration = (task) => {
      if (!task.started_at) return '-'
      
      const startTime = new Date(task.started_at)
      const endTime = task.completed_at ? new Date(task.completed_at) : new Date()
      const duration = Math.floor((endTime - startTime) / 1000)
      
      if (duration < 60) {
        return `${duration}秒`
      } else if (duration < 3600) {
        return `${Math.floor(duration / 60)}分${duration % 60}秒`
      } else {
        const hours = Math.floor(duration / 3600)
        const minutes = Math.floor((duration % 3600) / 60)
        return `${hours}小时${minutes}分钟`
      }
    }

    const getAgentName = (agentId) => {
      // 根据agentId查找对应的主机名
      const agent = agents.value.find(a => a.id === agentId)
      if (agent) {
        return `${agent.hostname} (${agent.ip})`
      }
      // 如果找不到对应的agent信息，返回agentId
      return agentId
    }

    onMounted(() => {
      loadUserPreferences()
      loadAgents()
      loadTasks()
      startAutoRefresh()
    })

    onUnmounted(() => {
      stopAutoRefresh()
    })

    return {
      loading,
      tasks,
      showTaskDialog,
      currentTask,
      activeResultTab,
      filters,
      pagination,
      filteredTasks,
      refreshInterval,
      agents,
      loadTasks,
      loadAgents,
      resetFilters,
      handleSortChange,
      handleSizeChange,
      handleCurrentChange,
      viewTaskDetails,
      stopTask,
      retryTask,
      getStatusType,
      getStatusText,
      formatDateTime,
      getDuration,
      getAgentName,
      startAutoRefresh,
      stopAutoRefresh,
      handleRefreshIntervalChange
    }
  }
}
</script>

<style scoped>
.execution-history {
  height: 100%;
}

.page-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.task-name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.task-details {
  max-height: 70vh;
  overflow-y: auto;
}

.script-content,
.script-params,
.execution-results {
  margin-top: 20px;
}

.script-content h4,
.script-params h4,
.execution-results h4 {
  margin-bottom: 12px;
  color: #262626;
  font-size: 16px;
}

.script-textarea,
.params-input {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.output-section {
  margin-top: 16px;
}

.output-section h5 {
  margin-bottom: 8px;
  color: #595959;
  font-size: 14px;
}

.output-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  background: #f8f8f8;
}

.error-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  background: #fff2f0;
}

.result-content {
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}
</style>
