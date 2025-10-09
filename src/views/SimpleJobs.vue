<template>
  <div class="simple-jobs">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="page-title">作业管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog = true">
              <el-icon><Plus /></el-icon>
              创建作业
            </el-button>
          </div>
        </div>
      </template>

      <!-- 作业列表 -->
      <el-table :data="jobs" v-loading="loading" stripe>
        <el-table-column prop="name" label="作业名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="viewJob(row)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
        
        <el-table-column prop="step_count" label="步骤数" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.step_count }} 步</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="target_agent_id" label="目标Agent" width="180">
          <template #default="{ row }">
            {{ getAgentName(row.target_agent_id) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="executeJob(row)">
              <el-icon><VideoPlay /></el-icon>
              执行
            </el-button>
            <el-button size="small" @click="editJob(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" @click="viewJob(row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button type="danger" size="small" @click="deleteJob(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑作业对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingJob ? '编辑作业' : '创建作业'"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-form :model="jobForm" :rules="jobRules" ref="jobFormRef" label-width="120px">
        <el-form-item label="作业名称" prop="name">
          <el-input v-model="jobForm.name" placeholder="请输入作业名称" />
        </el-form-item>
        
        <el-form-item label="作业描述" prop="description">
          <el-input 
            v-model="jobForm.description" 
            type="textarea" 
            :rows="2" 
            placeholder="请输入作业描述"
          />
        </el-form-item>
        
        <el-form-item label="目标Agent" prop="target_agent_id">
          <el-select v-model="jobForm.target_agent_id" placeholder="请选择目标Agent" style="width: 100%">
            <el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="`${agent.hostname} (${agent.ip})`"
              :value="agent.id"
              :disabled="agent.status !== 'ONLINE'"
            >
              <span style="float: left">{{ agent.hostname }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                <el-tag :type="agent.status === 'ONLINE' ? 'success' : 'danger'" size="small">
                  {{ agent.status === 'ONLINE' ? '在线' : '离线' }}
                </el-tag>
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="全局环境变量">
          <el-button size="small" @click="addEnvVar">
            <el-icon><Plus /></el-icon>
            添加变量
          </el-button>
          <div v-for="(item, index) in jobForm.env_vars_array" :key="index" class="env-var-item">
            <el-input v-model="item.key" placeholder="变量名" style="width: 200px" />
            <span style="margin: 0 8px">=</span>
            <el-input v-model="item.value" placeholder="变量值" style="width: 300px" />
            <el-button type="danger" size="small" @click="removeEnvVar(index)" style="margin-left: 8px">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </el-form-item>
        
        <el-divider>作业步骤</el-divider>
        
        <el-button type="primary" size="small" @click="addStep" style="margin-bottom: 16px">
          <el-icon><Plus /></el-icon>
          添加步骤
        </el-button>
        
        <div v-for="(step, index) in jobForm.steps" :key="index" class="step-item">
          <el-card>
            <template #header>
              <div class="step-header">
                <span>步骤 {{ index + 1 }}</span>
                <el-button type="danger" size="small" @click="removeStep(index)">
                  <el-icon><Delete /></el-icon>
                  删除步骤
                </el-button>
              </div>
            </template>
            
            <el-form-item :label="`步骤名称`" :prop="`steps.${index}.step_name`" label-width="100px">
              <el-input v-model="step.step_name" placeholder="请输入步骤名称" />
            </el-form-item>
            
            <el-form-item :label="`目标Agent`" label-width="100px">
              <el-select 
                v-model="step.target_agent_id" 
                placeholder="选择目标Agent（留空则使用作业默认Agent）"
                clearable
                style="width: 100%"
              >
                <el-option
                  v-for="agent in agents"
                  :key="agent.id"
                  :label="`${agent.hostname} (${agent.ip})`"
                  :value="agent.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item :label="`脚本内容`" :prop="`steps.${index}.script_content`" label-width="100px">
              <el-input 
                v-model="step.script_content" 
                type="textarea" 
                :rows="6" 
                placeholder="请输入Shell脚本内容"
              />
            </el-form-item>
            
            <el-form-item :label="`超时时间(秒)`" label-width="100px">
              <el-input-number v-model="step.timeout" :min="10" :max="7200" />
            </el-form-item>
          </el-card>
        </div>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveJob" :loading="saving">
          {{ editingJob ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看作业详情对话框 -->
    <el-dialog
      v-model="showViewDialog"
      :title="`作业详情 - ${currentJob?.name || ''}`"
      width="900px"
      :close-on-click-modal="false"
    >
      <div v-if="currentJob" class="job-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="作业名称">{{ currentJob.name }}</el-descriptions-item>
          <el-descriptions-item label="目标Agent">
            {{ getAgentName(currentJob.target_agent_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="作业描述" :span="2">
            {{ currentJob.description || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(currentJob.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDateTime(currentJob.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider>环境变量</el-divider>
        <el-descriptions :column="1" border v-if="Object.keys(currentJob.env_vars || {}).length > 0">
          <el-descriptions-item 
            v-for="(value, key) in currentJob.env_vars" 
            :key="key" 
            :label="key"
          >
            {{ value }}
          </el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="未设置环境变量" />
        
        <el-divider>作业步骤</el-divider>
        <el-timeline>
          <el-timeline-item 
            v-for="(step, index) in currentJob.steps" 
            :key="index"
            :timestamp="`步骤 ${index + 1}`"
          >
            <h4>{{ step.step_name }}</h4>
            <div class="step-script">
              <pre>{{ step.script_content }}</pre>
            </div>
            <div class="step-info">
              <el-tag size="small">超时: {{ step.timeout }}秒</el-tag>
              <el-tag size="small" type="info" v-if="step.target_agent_id">
                目标Agent: {{ getAgentName(step.target_agent_id) }}
              </el-tag>
              <el-tag size="small" type="warning" v-else>
                使用作业默认Agent
              </el-tag>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>

    <!-- 执行详情对话框 -->
    <el-dialog
      v-model="showExecutionDetail"
      :title="`执行详情 - ${currentExecution?.job_name || ''}`"
      width="900px"
      :close-on-click-modal="false"
    >
      <div v-if="currentExecution" class="execution-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="作业名称">{{ currentExecution.job_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentExecution.status)">
              {{ getStatusText(currentExecution.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="进度">
            {{ currentExecution.current_step }}/{{ currentExecution.total_steps }}
          </el-descriptions-item>
          <el-descriptions-item label="目标Agent">
            {{ getAgentName(currentExecution.target_agent_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(currentExecution.started_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ formatDateTime(currentExecution.completed_at) }}
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider>执行日志</el-divider>
        <div class="execution-log">
          <div v-for="(log, index) in currentExecution.execution_log" :key="index" class="log-item">
            {{ log }}
          </div>
          <el-empty v-if="!currentExecution.execution_log || currentExecution.execution_log.length === 0" 
                    description="暂无日志" />
        </div>
        
        <el-alert 
          v-if="currentExecution.error_message" 
          :title="currentExecution.error_message" 
          type="error" 
          style="margin-top: 16px"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { simpleJobsApi, agentApi } from '../api'

export default {
  name: 'SimpleJobs',
  setup() {
    const router = useRouter()
    const loading = ref(false)
    const saving = ref(false)
    const jobs = ref([])
    const agents = ref([])
    const showCreateDialog = ref(false)
    const showViewDialog = ref(false)
    const showExecutionDetail = ref(false)
    const currentJob = ref(null)
    const currentExecution = ref(null)
    const editingJob = ref(null)
    const jobFormRef = ref()

    const jobForm = reactive({
      name: '',
      description: '',
      target_agent_id: '',
      env_vars_array: [],
      steps: []
    })

    const jobRules = {
      name: [{ required: true, message: '请输入作业名称', trigger: 'blur' }],
      target_agent_id: [{ required: true, message: '请选择目标Agent', trigger: 'change' }]
    }

    // 加载作业列表
    const loadJobs = async () => {
      try {
        loading.value = true
        const data = await simpleJobsApi.getJobs()
        jobs.value = data.jobs || []
      } catch (error) {
        ElMessage.error('加载作业列表失败: ' + error.message)
      } finally {
        loading.value = false
      }
    }

    // 加载Agent列表
    const loadAgents = async () => {
      try {
        const data = await agentApi.getServers()
        agents.value = data || []
      } catch (error) {
        console.error('加载Agent列表失败:', error)
      }
    }

    // 添加环境变量
    const addEnvVar = () => {
      jobForm.env_vars_array.push({ key: '', value: '' })
    }

    // 删除环境变量
    const removeEnvVar = (index) => {
      jobForm.env_vars_array.splice(index, 1)
    }

    // 添加步骤
    const addStep = () => {
      jobForm.steps.push({
        step_name: `步骤${jobForm.steps.length + 1}`,
        script_content: '',
        target_agent_id: '',  // 新增字段
        timeout: 300
      })
    }

    // 删除步骤
    const removeStep = (index) => {
      jobForm.steps.splice(index, 1)
    }

    // 保存作业
    const handleSaveJob = async () => {
      if (!jobFormRef.value) return
      
      try {
        await jobFormRef.value.validate()
        
        if (jobForm.steps.length === 0) {
          ElMessage.warning('请至少添加一个步骤')
          return
        }
        
        saving.value = true
        
        // 转换环境变量数组为对象
        const env_vars = {}
        jobForm.env_vars_array.forEach(item => {
          if (item.key && item.value) {
            env_vars[item.key] = item.value
          }
        })
        
        const data = {
          name: jobForm.name,
          description: jobForm.description,
          target_agent_id: jobForm.target_agent_id,
          env_vars: env_vars,
          steps: jobForm.steps
        }
        
        if (editingJob.value) {
          await simpleJobsApi.updateJob(editingJob.value.id, data)
          ElMessage.success('作业更新成功')
        } else {
          await simpleJobsApi.createJob(data)
          ElMessage.success('作业创建成功')
        }
        
        showCreateDialog.value = false
        resetForm()
        loadJobs()
        
      } catch (error) {
        if (error.message) {
          ElMessage.error('保存作业失败: ' + error.message)
        }
      } finally {
        saving.value = false
      }
    }

    // 编辑作业
    const editJob = async (job) => {
      try {
        const data = await simpleJobsApi.getJob(job.id)
        const jobData = data.job
        
        editingJob.value = jobData
        jobForm.name = jobData.name
        jobForm.description = jobData.description
        jobForm.target_agent_id = jobData.target_agent_id
        
        // 转换环境变量对象为数组
        jobForm.env_vars_array = Object.entries(jobData.env_vars || {}).map(([key, value]) => ({
          key, value
        }))
        
        jobForm.steps = jobData.steps.map(step => ({
          step_name: step.step_name,
          script_content: step.script_content,
          target_agent_id: step.target_agent_id || '',  // 添加target_agent_id字段
          timeout: step.timeout
        }))
        
        showCreateDialog.value = true
        
      } catch (error) {
        ElMessage.error('加载作业详情失败: ' + error.message)
      }
    }

    // 查看作业
    const viewJob = async (job) => {
      try {
        const data = await simpleJobsApi.getJob(job.id)
        currentJob.value = data.job
        showViewDialog.value = true
      } catch (error) {
        ElMessage.error('加载作业详情失败: ' + error.message)
      }
    }

    // 删除作业
    const deleteJob = async (job) => {
      try {
        await ElMessageBox.confirm(`确定要删除作业 ${job.name} 吗？`, '确认删除', {
          type: 'warning'
        })
        
        await simpleJobsApi.deleteJob(job.id)
        ElMessage.success('作业删除成功')
        loadJobs()
        
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除作业失败: ' + error.message)
        }
      }
    }

    // 执行作业
    const executeJob = async (job) => {
      try {
        await ElMessageBox.confirm(`确定要执行作业 ${job.name} 吗？`, '确认执行', {
          type: 'warning'
        })
        
        const result = await simpleJobsApi.executeJob(job.id)
        ElMessage.success('作业开始执行，执行ID: ' + result.execution_id)
        
        // 跳转到任务历史页面
        setTimeout(() => {
          router.push('/execution-history')
        }, 1000)
        
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('执行作业失败: ' + error.message)
        }
      }
    }

    // 查看执行详情
    const viewExecution = async (execution) => {
      try {
        const data = await simpleJobsApi.getExecution(execution.id)
        currentExecution.value = data.execution
        showExecutionDetail.value = true
      } catch (error) {
        ElMessage.error('加载执行详情失败: ' + error.message)
      }
    }

    // 重置表单
    const resetForm = () => {
      editingJob.value = null
      jobForm.name = ''
      jobForm.description = ''
      jobForm.target_agent_id = ''
      jobForm.env_vars_array = []
      jobForm.steps = []
    }

    // 获取Agent名称
    const getAgentName = (agentId) => {
      const agent = agents.value.find(a => a.id === agentId)
      return agent ? `${agent.hostname} (${agent.ip})` : agentId
    }

    // 格式化时间
    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-'
      return new Date(dateTime).toLocaleString('zh-CN')
    }

    // 获取状态类型
    const getStatusType = (status) => {
      const map = {
        'PENDING': 'info',
        'RUNNING': 'warning',
        'COMPLETED': 'success',
        'FAILED': 'danger'
      }
      return map[status] || 'info'
    }

    // 获取状态文本
    const getStatusText = (status) => {
      const map = {
        'PENDING': '等待中',
        'RUNNING': '运行中',
        'COMPLETED': '已完成',
        'FAILED': '失败'
      }
      return map[status] || status
    }

    // 获取进度
    const getProgress = (execution) => {
      if (execution.total_steps === 0) return 0
      return Math.round((execution.current_step / execution.total_steps) * 100)
    }

    // 获取进度状态
    const getProgressStatus = (status) => {
      if (status === 'COMPLETED') return 'success'
      if (status === 'FAILED') return 'exception'
      return undefined
    }

    onMounted(() => {
      loadJobs()
      loadAgents()
    })

    return {
      loading,
      saving,
      jobs,
      agents,
      showCreateDialog,
      showViewDialog,
      showExecutionDetail,
      currentJob,
      currentExecution,
      editingJob,
      jobFormRef,
      jobForm,
      jobRules,
      addEnvVar,
      removeEnvVar,
      addStep,
      removeStep,
      handleSaveJob,
      editJob,
      viewJob,
      deleteJob,
      executeJob,
      viewExecution,
      loadExecutions,
      getAgentName,
      formatDateTime,
      getStatusType,
      getStatusText,
      getProgress,
      getProgressStatus
    }
  }
}
</script>

<style scoped>
.simple-jobs {
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

.env-var-item {
  display: flex;
  align-items: center;
  margin-top: 8px;
}

.step-item {
  margin-bottom: 16px;
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.job-details,
.execution-details {
  max-height: 70vh;
  overflow-y: auto;
}

.step-script {
  margin: 12px 0;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
}

.step-script pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.step-info {
  margin-top: 8px;
}

.execution-log {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.log-item {
  padding: 4px 0;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #333;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
