<template>
  <div class="jobs-management">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="page-title">作业管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateJobDialog = true">
              <el-icon><Plus /></el-icon>
              创建作业
            </el-button>
            <el-button @click="showTemplateDialog = true">
              <el-icon><Document /></el-icon>
              作业模板
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索作业名称..."
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.status" placeholder="状态筛选" clearable>
              <el-option label="全部" value="" />
              <el-option label="等待中" value="PENDING" />
              <el-option label="运行中" value="RUNNING" />
              <el-option label="已完成" value="COMPLETED" />
              <el-option label="失败" value="FAILED" />
              <el-option label="已取消" value="CANCELLED" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.priority" placeholder="优先级筛选" clearable>
              <el-option label="全部" value="" />
              <el-option label="高" value="1" />
              <el-option label="中" value="5" />
              <el-option label="低" value="9" />
            </el-select>
          </el-col>
          <el-col :span="10">
            <el-button type="primary" @click="loadJobInstances" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="resetFilters">
              <el-icon><Delete /></el-icon>
              重置筛选
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 作业实例列表 -->
      <el-table :data="filteredJobs" v-loading="loading" stripe>
        <el-table-column prop="name" label="作业名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="viewJobDetails(row)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column prop="template_id" label="模板" width="150">
          <template #default="{ row }">
            {{ getTemplateName(row.template_id) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)" size="small">
              {{ getPriorityText(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <div class="progress-info">
              <span>{{ row.current_step }}/{{ row.total_steps }}</span>
              <el-progress 
                :percentage="getProgress(row)" 
                :status="getProgressStatus(row.status)"
                style="flex: 1; margin-left: 12px;"
              />
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.status === 'PENDING'" 
              type="text" 
              size="small"
              @click="executeJob(row)"
            >
              <el-icon><VideoPlay /></el-icon>
              执行
            </el-button>
            <el-button 
              v-if="row.status === 'RUNNING'" 
              type="text" 
              size="small"
              @click="stopJob(row)"
            >
              <el-icon><VideoPause /></el-icon>
              停止
            </el-button>
            <el-button type="text" size="small" @click="viewJobDetails(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button 
              v-if="row.status === 'FAILED'" 
              type="text" 
              size="small"
              @click="retryJob(row)"
            >
              <el-icon><Refresh /></el-icon>
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
        />
      </div>
    </el-card>

    <!-- 创建作业对话框 -->
    <el-dialog
      v-model="showCreateJobDialog"
      title="创建作业"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-form :model="jobForm" :rules="jobRules" ref="jobFormRef" label-width="100px">
        <el-form-item label="作业模板" prop="template_id">
          <el-select v-model="jobForm.template_id" placeholder="请选择作业模板" @change="handleTemplateChange">
            <el-option
              v-for="template in templates"
              :key="template.id"
              :label="template.name"
              :value="template.id"
            >
              <span style="float: left">{{ template.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">{{ template.category }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="作业名称" prop="name">
          <el-input v-model="jobForm.name" placeholder="请输入作业名称" />
        </el-form-item>
        
        <el-form-item label="作业描述" prop="description">
          <el-input v-model="jobForm.description" type="textarea" :rows="3" placeholder="请输入作业描述" />
        </el-form-item>
        
        <el-form-item label="目标主机" prop="target_hosts">
          <el-select v-model="jobForm.target_hosts" multiple placeholder="请选择目标主机">
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="`${agent.hostname} (${agent.ip})`"
              :value="agent.id"
              :disabled="agent.status !== 'ONLINE'"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="优先级" prop="priority">
          <el-radio-group v-model="jobForm.priority">
            <el-radio :value="1">高</el-radio>
            <el-radio :value="5">中</el-radio>
            <el-radio :value="9">低</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="作业参数" v-if="selectedTemplate">
          <el-descriptions :column="1" border>
            <el-descriptions-item
              v-for="(value, key) in selectedTemplate.default_params"
              :key="key"
              :label="key"
            >
              <el-input v-model="jobForm.params[key]" :placeholder="String(value)" />
            </el-descriptions-item>
          </el-descriptions>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateJobDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateJob" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 作业模板对话框 -->
    <el-dialog
      v-model="showTemplateDialog"
      title="作业模板"
      width="1000px"
      :close-on-click-modal="false"
    >
      <el-table :data="templates" v-loading="loadingTemplates">
        <el-table-column prop="name" label="模板名称" width="200" />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="250" />
        <el-table-column prop="tags" label="标签" width="200">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" style="margin-right: 4px;">
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="text" size="small" @click="viewTemplateDetails(row)">
              查看详情
            </el-button>
            <el-button type="text" size="small" @click="useTemplate(row)">
              使用模板
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 作业详情对话框 -->
    <el-dialog
      v-model="showJobDetailsDialog"
      :title="`作业详情 - ${currentJob?.name || ''}`"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="currentJob" class="job-details">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="作业ID">{{ currentJob.id }}</el-descriptions-item>
              <el-descriptions-item label="作业名称">{{ currentJob.name }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getStatusType(currentJob.status)">
                  {{ getStatusText(currentJob.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="优先级">
                <el-tag :type="getPriorityType(currentJob.priority)">
                  {{ getPriorityText(currentJob.priority) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ formatDateTime(currentJob.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="开始时间">
                {{ formatDateTime(currentJob.started_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="完成时间">
                {{ formatDateTime(currentJob.completed_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="超时时间">
                {{ currentJob.timeout }}秒
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
          
          <el-tab-pane label="执行步骤" name="steps">
            <el-timeline>
              <el-timeline-item
                v-for="(step, index) in currentJob.steps_status"
                :key="index"
                :timestamp="formatDateTime(step.completed_at)"
                :type="getStepTimelineType(step.status)"
                :icon="getStepIcon(step.status)"
              >
                <div class="step-item">
                  <h4>{{ step.name }}</h4>
                  <el-tag :type="getStatusType(step.status)" size="small">
                    {{ getStatusText(step.status) }}
                  </el-tag>
                  <p v-if="step.error_message" class="error-message">
                    {{ step.error_message }}
                  </p>
                  <div v-if="step.execution_time" class="execution-time">
                    执行时间: {{ step.execution_time }}秒
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-tab-pane>
          
          <el-tab-pane label="执行结果" name="results">
            <div v-if="currentJob.execution_log && currentJob.execution_log.length > 0">
              <el-card v-for="(log, index) in currentJob.execution_log" :key="index" class="log-card">
                <pre class="log-content">{{ log }}</pre>
              </el-card>
            </div>
            <el-empty v-else description="暂无执行日志" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { jobsApi } from '../api'
import { agentApi } from '../api'

export default {
  name: 'Jobs',
  setup() {
    const loading = ref(false)
    const loadingTemplates = ref(false)
    const creating = ref(false)
    const jobs = ref([])
    const templates = ref([])
    const agents = ref([])
    const showCreateJobDialog = ref(false)
    const showTemplateDialog = ref(false)
    const showJobDetailsDialog = ref(false)
    const currentJob = ref(null)
    const selectedTemplate = ref(null)
    const activeTab = ref('basic')
    const jobFormRef = ref()

    const filters = reactive({
      keyword: '',
      status: '',
      priority: ''
    })

    const pagination = reactive({
      currentPage: 1,
      pageSize: 10,
      total: 0
    })

    const jobForm = reactive({
      template_id: '',
      name: '',
      description: '',
      target_hosts: [],
      priority: 5,
      params: {}
    })

    const jobRules = {
      template_id: [{ required: true, message: '请选择作业模板', trigger: 'change' }],
      name: [{ required: true, message: '请输入作业名称', trigger: 'blur' }],
      target_hosts: [{ required: true, message: '请选择目标主机', trigger: 'change' }]
    }

    const filteredJobs = computed(() => {
      let result = [...jobs.value]
      
      if (filters.keyword) {
        const keyword = filters.keyword.toLowerCase()
        result = result.filter(job => 
          job.name.toLowerCase().includes(keyword)
        )
      }
      
      if (filters.status) {
        result = result.filter(job => job.status === filters.status)
      }
      
      if (filters.priority) {
        result = result.filter(job => job.priority === parseInt(filters.priority))
      }
      
      pagination.total = result.length
      const start = (pagination.currentPage - 1) * pagination.pageSize
      const end = start + pagination.pageSize
      return result.slice(start, end)
    })

    const loadJobInstances = async () => {
      try {
        loading.value = true
        const data = await jobsApi.getJobInstances()
        jobs.value = data.instances || []
        pagination.total = jobs.value.length
      } catch (error) {
        ElMessage.error('加载作业实例失败: ' + error.message)
      } finally {
        loading.value = false
      }
    }

    const loadTemplates = async () => {
      try {
        loadingTemplates.value = true
        const data = await jobsApi.getJobTemplates()
        templates.value = data.templates || []
      } catch (error) {
        ElMessage.error('加载作业模板失败: ' + error.message)
      } finally {
        loadingTemplates.value = false
      }
    }

    const loadAgents = async () => {
      try {
        const data = await agentApi.getServers()
        agents.value = data || []
      } catch (error) {
        console.error('加载Agent列表失败:', error)
      }
    }

    const resetFilters = () => {
      filters.keyword = ''
      filters.status = ''
      filters.priority = ''
      pagination.currentPage = 1
    }

    const handleTemplateChange = (templateId) => {
      const template = templates.value.find(t => t.id === templateId)
      if (template) {
        selectedTemplate.value = template
        jobForm.params = { ...template.default_params }
      }
    }

    const handleCreateJob = async () => {
      if (!jobFormRef.value) return
      
      try {
        await jobFormRef.value.validate()
        creating.value = true
        
        await jobsApi.createJobInstance({
          template_id: jobForm.template_id,
          name: jobForm.name,
          description: jobForm.description,
          target_hosts: jobForm.target_hosts,
          priority: jobForm.priority,
          params: jobForm.params
        })
        
        ElMessage.success('作业创建成功')
        showCreateJobDialog.value = false
        
        // 重置表单
        Object.assign(jobForm, {
          template_id: '',
          name: '',
          description: '',
          target_hosts: [],
          priority: 5,
          params: {}
        })
        selectedTemplate.value = null
        
        // 刷新作业列表
        loadJobInstances()
      } catch (error) {
        ElMessage.error('创建作业失败: ' + error.message)
      } finally {
        creating.value = false
      }
    }

    const executeJob = async (job) => {
      try {
        await ElMessageBox.confirm(`确定要执行作业 ${job.name} 吗？`, '确认执行', {
          type: 'warning'
        })
        
        await jobsApi.executeJobInstance(job.id)
        ElMessage.success('作业开始执行')
        loadJobInstances()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('执行作业失败: ' + error.message)
        }
      }
    }

    const stopJob = async (job) => {
      try {
        await ElMessageBox.confirm(`确定要停止作业 ${job.name} 吗？`, '确认停止', {
          type: 'warning'
        })
        
        await jobsApi.stopJobInstance(job.id)
        ElMessage.success('作业已停止')
        loadJobInstances()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('停止作业失败: ' + error.message)
        }
      }
    }

    const retryJob = async (job) => {
      try {
        await ElMessageBox.confirm(`确定要重试作业 ${job.name} 吗？`, '确认重试', {
          type: 'warning'
        })
        
        // 重新创建作业实例
        await jobsApi.createJobInstance({
          template_id: job.template_id,
          name: `[重试] ${job.name}`,
          description: job.description,
          target_hosts: job.target_hosts,
          priority: job.priority,
          params: job.params
        })
        
        ElMessage.success('作业重试已创建')
        loadJobInstances()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('重试作业失败: ' + error.message)
        }
      }
    }

    const viewJobDetails = async (job) => {
      try {
        const data = await jobsApi.getJobInstance(job.id)
        currentJob.value = data.instance
        showJobDetailsDialog.value = true
        activeTab.value = 'basic'
      } catch (error) {
        ElMessage.error('获取作业详情失败: ' + error.message)
      }
    }

    const viewTemplateDetails = (template) => {
      ElMessage.info('模板详情功能开发中...')
    }

    const useTemplate = (template) => {
      handleTemplateChange(template.id)
      jobForm.template_id = template.id
      jobForm.name = template.name
      jobForm.description = template.description
      showTemplateDialog.value = false
      showCreateJobDialog.value = true
    }

    const getTemplateName = (templateId) => {
      const template = templates.value.find(t => t.id === templateId)
      return template ? template.name : '-'
    }

    const getStatusType = (status) => {
      const map = {
        'PENDING': 'info',
        'RUNNING': 'warning',
        'COMPLETED': 'success',
        'FAILED': 'danger',
        'CANCELLED': 'info'
      }
      return map[status] || 'info'
    }

    const getStatusText = (status) => {
      const map = {
        'PENDING': '等待中',
        'RUNNING': '运行中',
        'COMPLETED': '已完成',
        'FAILED': '失败',
        'CANCELLED': '已取消'
      }
      return map[status] || status
    }

    const getPriorityType = (priority) => {
      if (priority <= 3) return 'danger'
      if (priority <= 6) return 'warning'
      return 'info'
    }

    const getPriorityText = (priority) => {
      if (priority <= 3) return '高'
      if (priority <= 6) return '中'
      return '低'
    }

    const getProgress = (job) => {
      if (job.total_steps === 0) return 0
      return Math.round((job.current_step / job.total_steps) * 100)
    }

    const getProgressStatus = (status) => {
      if (status === 'COMPLETED') return 'success'
      if (status === 'FAILED') return 'exception'
      return undefined
    }

    const getCategoryLabel = (category) => {
      const map = {
        'monitoring': '系统监控',
        'deployment': '应用部署',
        'maintenance': '系统维护',
        'backup': '数据备份',
        'security': '安全检查',
        'custom': '自定义'
      }
      return map[category] || category
    }

    const getStepTimelineType = (status) => {
      const map = {
        'PENDING': 'primary',
        'RUNNING': 'warning',
        'COMPLETED': 'success',
        'FAILED': 'danger'
      }
      return map[status] || 'primary'
    }

    const getStepIcon = (status) => {
      // 这里可以返回不同的图标
      return undefined
    }

    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-'
      return new Date(dateTime).toLocaleString('zh-CN')
    }

    onMounted(() => {
      loadJobInstances()
      loadTemplates()
      loadAgents()
    })

    return {
      loading,
      loadingTemplates,
      creating,
      jobs,
      templates,
      agents,
      showCreateJobDialog,
      showTemplateDialog,
      showJobDetailsDialog,
      currentJob,
      selectedTemplate,
      activeTab,
      jobFormRef,
      filters,
      pagination,
      jobForm,
      jobRules,
      filteredJobs,
      loadJobInstances,
      loadTemplates,
      resetFilters,
      handleTemplateChange,
      handleCreateJob,
      executeJob,
      stopJob,
      retryJob,
      viewJobDetails,
      viewTemplateDetails,
      useTemplate,
      getTemplateName,
      getStatusType,
      getStatusText,
      getPriorityType,
      getPriorityText,
      getProgress,
      getProgressStatus,
      getCategoryLabel,
      getStepTimelineType,
      getStepIcon,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.jobs-management {
  padding: 24px;
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
  gap: 12px;
}

.filter-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.job-details {
  max-height: 70vh;
  overflow-y: auto;
}

.step-item {
  padding: 8px 0;
}

.step-item h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.error-message {
  color: #f56c6c;
  margin: 8px 0 0 0;
  font-size: 14px;
}

.execution-time {
  margin-top: 8px;
  color: #909399;
  font-size: 13px;
}

.log-card {
  margin-bottom: 16px;
}

.log-content {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>