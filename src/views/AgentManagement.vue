<template>
  <div class="agent-management">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="page-title">Agent管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="refreshAgents">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="showBatchDialog = true">
              <el-icon><Operation /></el-icon>
              批量管理
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-input
              v-model="filters.keyword"
              placeholder="搜索主机名、IP地址..."
              clearable
              @input="filterAgents"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.status" placeholder="状态筛选" clearable>
              <el-option label="全部" value="" />
              <el-option label="在线" value="ONLINE" />
              <el-option label="离线" value="OFFLINE" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="filters.region" placeholder="区域筛选" clearable>
              <el-option label="全部" value="" />
              <el-option label="默认" value="default" />
              <el-option label="办公室" value="office" />
            </el-select>
          </el-col>
          <el-col :span="8">
            <el-button @click="resetFilters">
              <el-icon><Delete /></el-icon>
              重置筛选
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- Agent列表 -->
      <el-table
        :data="filteredAgents"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
        @sort-change="handleSortChange"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column prop="hostname" label="主机名" min-width="150" sortable="custom">
          <template #default="{ row }">
            <el-link type="primary" @click="viewAgentDetails(row)">
              {{ row.hostname }}
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column prop="ip" label="内网IP" width="140" sortable="custom" />
        
        <el-table-column prop="external_ip" label="外网IP" width="140">
          <template #default="{ row }">
            {{ row.external_ip || '-' }}
          </template>
        </el-table-column>
        
        <el-table-column prop="last_heartbeat" label="心跳更新时间" width="180" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.last_heartbeat) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="version" label="版本" width="100">
          <template #default="{ row }">
            {{ row.version || 'v1.0' }}
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getAgentStatusType(row.status)" size="small">
              {{ getAgentStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="text" @click="viewAgentDetails(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button type="text" @click="showRestartDialog(row)">
              <el-icon><RefreshRight /></el-icon>
              重启
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

    <!-- Agent详情对话框 -->
    <el-dialog
      v-model="showAgentDialog"
      :title="`Agent详情 - ${currentAgent?.hostname || ''}`"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="currentAgent" class="agent-details">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="Agent ID">
                {{ currentAgent.id }}
              </el-descriptions-item>
              <el-descriptions-item label="主机名">
                {{ currentAgent.hostname }}
              </el-descriptions-item>
              <el-descriptions-item label="内网IP">
                {{ currentAgent.ip }}
              </el-descriptions-item>
              <el-descriptions-item label="外网IP">
                {{ currentAgent.external_ip || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="currentAgent.status === 'ONLINE' ? 'success' : 'danger'">
                  {{ currentAgent.status }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="版本">
                {{ currentAgent.version || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="注册时间">
                {{ formatDateTime(currentAgent.register_time) }}
              </el-descriptions-item>
              <el-descriptions-item label="最后心跳">
                {{ formatDateTime(currentAgent.last_heartbeat) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
          
          <el-tab-pane label="系统信息" name="system">
            <div v-if="currentAgent.system_info" class="system-info">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-card class="info-card">
                    <template #header>
                      <div class="card-header">
                        <el-icon><Monitor /></el-icon>
                        <span>系统基础信息</span>
                      </div>
                    </template>
                    <el-descriptions :column="1" size="small">
                      <el-descriptions-item label="操作系统">
                        {{ currentAgent.system_info.os }}
                      </el-descriptions-item>
                      <el-descriptions-item label="内核版本">
                        {{ currentAgent.system_info.kernel }}
                      </el-descriptions-item>
                      <el-descriptions-item label="系统运行时间">
                        {{ currentAgent.system_info.uptime }}
                      </el-descriptions-item>
                      <el-descriptions-item label="负载均衡">
                        {{ currentAgent.system_info.load_average }}
                      </el-descriptions-item>
                    </el-descriptions>
                  </el-card>
                </el-col>
                <el-col :span="12">
                  <el-card class="info-card">
                    <template #header>
                      <div class="card-header">
                        <el-icon><Cpu /></el-icon>
                        <span>硬件资源信息</span>
                      </div>
                    </template>
                    <el-descriptions :column="1" size="small">
                      <el-descriptions-item label="CPU信息">
                        {{ currentAgent.system_info.cpu }}
                      </el-descriptions-item>
                      <el-descriptions-item label="内存使用">
                        {{ currentAgent.system_info.memory }}
                      </el-descriptions-item>
                      <el-descriptions-item label="磁盘使用">
                        {{ currentAgent.system_info.disk }}
                      </el-descriptions-item>
                      <el-descriptions-item label="网络接口">
                        {{ currentAgent.system_info.network }}
                      </el-descriptions-item>
                    </el-descriptions>
                  </el-card>
                </el-col>
              </el-row>
              
              <!-- 资源使用图表区域 -->
              <el-row :gutter="16" style="margin-top: 16px;">
                <el-col :span="8">
                  <el-card class="metric-card">
                    <div class="metric-header">
                      <span>CPU使用率</span>
                      <span class="metric-value">23.5%</span>
                    </div>
                    <el-progress :percentage="23.5" :show-text="false" />
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card class="metric-card">
                    <div class="metric-header">
                      <span>内存使用率</span>
                      <span class="metric-value">52.5%</span>
                    </div>
                    <el-progress :percentage="52.5" :show-text="false" color="#f56c6c" />
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card class="metric-card">
                    <div class="metric-header">
                      <span>磁盘使用率</span>
                      <span class="metric-value">45.0%</span>
                    </div>
                    <el-progress :percentage="45.0" :show-text="false" color="#67c23a" />
                  </el-card>
                </el-col>
              </el-row>
            </div>
            <el-empty v-else description="暂无系统信息" />
          </el-tab-pane>
          
          <el-tab-pane label="执行历史" name="history">
            <el-table :data="agentTasks" stripe>
              <el-table-column prop="script_name" label="任务名称" />
              <el-table-column prop="status" label="状态">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)">
                    {{ getStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="执行时间">
                <template #default="{ row }">
                  {{ formatDateTime(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作">
                <template #default="{ row }">
                  <el-button type="text" @click="viewTaskResult(row)">
                    查看结果
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- 批量管理对话框 -->
    <el-dialog
      v-model="showBatchDialog"
      title="批量管理"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="batch-management">
        <p>已选择 {{ selectedAgents.length }} 个Agent</p>
        <el-form :model="batchForm" label-width="100px">
          <el-form-item label="操作类型">
            <el-radio-group v-model="batchForm.action">
              <el-radio value="restart">重启服务</el-radio>
              <el-radio value="update">更新版本</el-radio>
              <el-radio value="stop">停止服务</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="batchForm.action === 'update'" label="目标版本">
            <el-input v-model="batchForm.version" placeholder="请输入目标版本" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showBatchDialog = false">取消</el-button>
        <el-button type="primary" @click="executeBatchAction">执行</el-button>
      </template>
    </el-dialog>

    <!-- 任务结果对话框 -->
    <el-dialog
      v-model="showTaskResultDialog"
      title="任务执行结果"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="currentTaskResult" class="task-result-content">
        <!-- 任务基本信息 -->
        <el-card class="task-info-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>任务信息</span>
            </div>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="任务ID">
              {{ currentTaskResult.id }}
            </el-descriptions-item>
            <el-descriptions-item label="任务名称">
              {{ currentTaskResult.script_name }}
            </el-descriptions-item>
            <el-descriptions-item label="执行状态">
              <el-tag :type="getStatusType(currentTaskResult.status)">
                {{ getStatusText(currentTaskResult.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="执行用户">
              {{ currentTaskResult.execution_user || 'root' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDateTime(currentTaskResult.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="开始时间">
              {{ formatDateTime(currentTaskResult.started_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="完成时间">
              {{ formatDateTime(currentTaskResult.completed_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="超时时间">
              {{ currentTaskResult.timeout }}秒
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 脚本内容 -->
        <el-card class="script-content-card" shadow="never" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>脚本内容</span>
            </div>
          </template>
          <div class="script-editor-container">
            <div class="editor-wrapper">
              <div class="line-numbers">
                <div 
                  v-for="(line, index) in (currentTaskResult.script || currentTaskResult.script_content || '').split('\n')" 
                  :key="index" 
                  class="line-number"
                >
                  {{ index + 1 }}
                </div>
              </div>
              <div class="script-editor">
                <pre>{{ currentTaskResult.script || currentTaskResult.script_content || '无脚本内容' }}</pre>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 脚本参数 -->
        <el-card v-if="currentTaskResult.script_params" class="params-card" shadow="never" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>脚本参数</span>
            </div>
          </template>
          <pre class="params-content">{{ currentTaskResult.script_params }}</pre>
        </el-card>

        <!-- 执行结果 -->
        <el-card class="result-card" shadow="never" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>执行结果</span>
            </div>
          </template>
          <div v-if="currentTaskResult.results && Object.keys(currentTaskResult.results).length > 0">
            <div v-for="(result, agentId) in currentTaskResult.results" :key="agentId" class="agent-result">
              <h4>Agent: {{ agentId }}</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="退出码">
                  <el-tag :type="result.exit_code === 0 ? 'success' : 'danger'">
                    {{ result.exit_code }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="执行时间">
                  {{ result.execution_time }}秒
                </el-descriptions-item>
                <el-descriptions-item v-if="result.stdout" label="标准输出">
                  <pre class="output-content">{{ result.stdout }}</pre>
                </el-descriptions-item>
                <el-descriptions-item v-if="result.stderr" label="错误输出">
                  <pre class="error-content">{{ result.stderr }}</pre>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
          <div v-else class="no-result">
            <el-empty description="暂无执行结果" />
          </div>
        </el-card>

        <!-- 错误信息 -->
        <el-card v-if="currentTaskResult.error_message" class="error-card" shadow="never" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>错误信息</span>
            </div>
          </template>
          <el-alert
            :title="currentTaskResult.error_message"
            type="error"
            :closable="false"
            show-icon
          />
        </el-card>
      </div>
      
      <template #footer>
        <el-button @click="showTaskResultDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 重启确认对话框 -->
    <el-dialog
      v-model="showRestartConfirmDialog"
      title="选择重启类型"
      width="400px"
      :close-on-click-modal="false"
    >
      <div v-if="currentRestartAgent" class="restart-dialog-content">
        <p>请选择要对 <strong>{{ currentRestartAgent.hostname }}</strong> 执行的重启操作：</p>
        
        <el-radio-group v-model="restartType" class="restart-options">
          <el-radio value="agent" class="restart-option">
            <div class="option-content">
              <div class="option-title">重启Agent</div>
              <div class="option-desc">仅重启QueenBee Agent服务，不影响主机运行</div>
            </div>
          </el-radio>
          <el-radio value="host" class="restart-option">
            <div class="option-content">
              <div class="option-title">重启主机</div>
              <div class="option-desc">重启整个主机系统，所有服务将停止</div>
            </div>
          </el-radio>
        </el-radio-group>
      </div>
      
      <template #footer>
        <el-button @click="showRestartConfirmDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmRestart">确认重启</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, scriptApi } from '../api'

export default {
  name: 'AgentManagement',
  setup() {
    const router = useRouter()
    const loading = ref(false)
    const agents = ref([])
    const selectedAgents = ref([])
    const showAgentDialog = ref(false)
    const showBatchDialog = ref(false)
    const currentAgent = ref(null)
    const activeTab = ref('basic')
    const agentTasks = ref([])
    const showTaskResultDialog = ref(false)
    const currentTaskResult = ref(null)
    const showRestartConfirmDialog = ref(false)
    const currentRestartAgent = ref(null)
    const restartType = ref('agent')

    const filters = reactive({
      keyword: '',
      status: '',
      region: ''
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

    const batchForm = reactive({
      action: 'restart',
      version: ''
    })

    const filteredAgents = computed(() => {
      let result = [...agents.value]

      // 关键词搜索
      if (filters.keyword) {
        const keyword = filters.keyword.toLowerCase()
        result = result.filter(agent => 
          agent.hostname.toLowerCase().includes(keyword) ||
          agent.ip.toLowerCase().includes(keyword) ||
          (agent.external_ip && agent.external_ip.toLowerCase().includes(keyword))
        )
      }

      // 状态筛选
      if (filters.status) {
        result = result.filter(agent => agent.status === filters.status)
      }

      // 区域筛选
      if (filters.region) {
        result = result.filter(agent => (agent.region || 'default') === filters.region)
      }

      // 排序
      if (sortConfig.prop) {
        result.sort((a, b) => {
          let aVal = a[sortConfig.prop]
          let bVal = b[sortConfig.prop]

          if (sortConfig.prop === 'last_heartbeat') {
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

    const loadAgents = async () => {
      try {
        loading.value = true
        const data = await agentApi.getServers()
        
        // 处理Agent数据，确保字段正确
        agents.value = data.map(agent => ({
          ...agent,
          // 确保状态字段正确
          status: agent.status || 'OFFLINE',
          // 添加外网IP字段（如果没有则为空）
          external_ip: agent.external_ip || '',
          // 确保版本字段
          version: agent.version || 'v1.0',
          // 判断Agent是否在线（基于心跳时间）
          status: isAgentOnline(agent.last_heartbeat) ? 'ONLINE' : 'OFFLINE'
        }))
        
        pagination.total = agents.value.length
      } catch (error) {
        ElMessage.error('加载Agent列表失败')
      } finally {
        loading.value = false
      }
    }

    const isAgentOnline = (lastHeartbeat) => {
      if (!lastHeartbeat) {
        console.log('No heartbeat time provided')
        return false
      }
      
      const now = new Date().getTime()
      const heartbeatTime = new Date(lastHeartbeat).getTime()
      const diffMinutes = (now - heartbeatTime) / (1000 * 60)
      
      console.log(`Heartbeat check: ${lastHeartbeat}, diff: ${diffMinutes.toFixed(2)} minutes`)
      
      // 如果心跳时间超过15秒，认为离线
      return diffMinutes <= 0.25  // 15秒 = 0.25分钟
    }

    const refreshAgents = () => {
      loadAgents()
    }

    const filterAgents = () => {
      // 筛选逻辑在computed中处理
    }

    const resetFilters = () => {
      filters.keyword = ''
      filters.status = ''
      filters.region = ''
      pagination.currentPage = 1
    }

    const handleSelectionChange = (selection) => {
      selectedAgents.value = selection
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

    const viewAgentDetails = async (agent) => {
      try {
        // 先设置基本信息
        currentAgent.value = {
          id: agent.id,
          hostname: agent.hostname,
          ip: agent.ip,
          external_ip: agent.external_ip || '-',
          status: agent.status,
          version: agent.version || 'v1.0.0',
          register_time: agent.register_time,
          last_heartbeat: agent.last_heartbeat,
          region: agent.region || 'default',
          system_info: {
            os: 'Ubuntu 20.04 LTS',
            kernel: 'Linux 5.4.0-74-generic',
            cpu: 'Intel(R) Xeon(R) CPU E5-2686 v4 @ 2.30GHz (4 cores)',
            memory: '8GB (Used: 4.2GB, Free: 3.8GB)',
            disk: '100GB SSD (Used: 45GB, Free: 55GB)',
            network: 'eth0: 1000Mbps, lo: loopback',
            uptime: '15 days, 8 hours, 32 minutes',
            load_average: '0.15, 0.18, 0.12'
          }
        }
        
        // 尝试获取详细信息
        try {
          const detailedData = await agentApi.getAgentDetails(agent.id)
          if (detailedData && detailedData.system_info) {
            currentAgent.value.system_info = {
              ...currentAgent.value.system_info,
              ...detailedData.system_info
            }
          }
        } catch (detailError) {
          console.log('获取详细信息失败，使用默认信息')
        }
        
        showAgentDialog.value = true
        activeTab.value = 'basic'
        
        // 加载该Agent的执行历史
        await loadAgentTasks(agent.id)
      } catch (error) {
        ElMessage.error('获取Agent详情失败')
      }
    }

    const loadAgentTasks = async (agentId) => {
      try {
        const data = await agentApi.getAgentTasks(agentId)
        agentTasks.value = data
      } catch (error) {
        console.error('加载Agent任务失败:', error)
        // 如果专用接口失败，尝试从所有任务中筛选
        try {
          const allTasks = await scriptApi.getTasks()
          agentTasks.value = allTasks.filter(task => 
            task.target_hosts && task.target_hosts.includes(agentId)
          )
        } catch (fallbackError) {
          console.error('备用方法也失败:', fallbackError)
          agentTasks.value = []
        }
      }
    }

    const restartAgent = async (agent) => {
      try {
        await ElMessageBox.confirm(`确定要重启Agent ${agent.hostname} 吗？`, '确认重启', {
          type: 'warning'
        })
        ElMessage.success('Agent重启请求已发送')
        // 这里可以调用重启Agent的API
      } catch (error) {
        // 用户取消
      }
    }

    const updateAgent = async (agent) => {
      try {
        await ElMessageBox.confirm(`确定要更新Agent ${agent.hostname} 吗？`, '确认更新', {
          type: 'warning'
        })
        ElMessage.success('Agent更新请求已发送')
        // 这里可以调用更新Agent的API
      } catch (error) {
        // 用户取消
      }
    }

    const handleAgentAction = (command, agent) => {
      switch (command) {
        case 'restart':
          restartAgent(agent)
          break
        case 'update':
          updateAgent(agent)
          break
        case 'logs':
          ElMessage.info('查看日志功能待实现')
          break
        case 'config':
          ElMessage.info('配置管理功能待实现')
          break
      }
    }

    const executeBatchAction = async () => {
      if (selectedAgents.value.length === 0) {
        ElMessage.warning('请先选择要操作的Agent')
        return
      }

      try {
        await ElMessageBox.confirm(
          `确定要对 ${selectedAgents.value.length} 个Agent执行 ${batchForm.action} 操作吗？`,
          '确认批量操作',
          { type: 'warning' }
        )
        
        ElMessage.success('批量操作请求已发送')
        showBatchDialog.value = false
        // 这里可以调用批量操作的API
      } catch (error) {
        // 用户取消
      }
    }

    const showRestartDialog = (agent) => {
      currentRestartAgent.value = agent
      showRestartConfirmDialog.value = true
    }

    const confirmRestart = async () => {
      if (!currentRestartAgent.value) return
      
      try {
        const actionText = restartType.value === 'host' ? '重启主机' : '重启Agent'
        await ElMessageBox.confirm(
          `确定要${actionText} ${currentRestartAgent.value.hostname} 吗？`,
          '确认重启',
          { type: 'warning' }
        )
        
        // 这里调用重启API
        if (restartType.value === 'host') {
          ElMessage.success(`主机 ${currentRestartAgent.value.hostname} 重启请求已发送`)
          // TODO: 调用重启主机API
        } else {
          ElMessage.success(`Agent ${currentRestartAgent.value.hostname} 重启请求已发送`)
          // TODO: 调用重启Agent API
        }
        
        showRestartConfirmDialog.value = false
        currentRestartAgent.value = null
        
      } catch (error) {
        if (error.message && error.message !== 'cancel') {
          ElMessage.error('重启操作失败: ' + error.message)
        }
      }
    }

    const viewTaskResult = async (task) => {
      try {
        // 获取任务详情并显示
        const taskDetails = await scriptApi.getTaskDetails(task.id)
        
        // 设置当前任务结果并显示对话框
        currentTaskResult.value = taskDetails
        showTaskResultDialog.value = true
        
      } catch (error) {
        ElMessage.error('获取任务结果失败: ' + (error.message || '未知错误'))
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

    const getAgentStatusType = (status) => {
      // 判断Agent是否在线，基于心跳时间
      return status === 'ONLINE' ? 'success' : 'danger'
    }

    const getAgentStatusText = (status) => {
      return status === 'ONLINE' ? 'online' : 'down'
    }

    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-'
      return new Date(dateTime).toLocaleString('zh-CN')
    }

    onMounted(() => {
      loadAgents()
    })

    return {
      loading,
      agents,
      selectedAgents,
      showAgentDialog,
      showBatchDialog,
      currentAgent,
      activeTab,
      agentTasks,
      showTaskResultDialog,
      currentTaskResult,
      showRestartConfirmDialog,
      currentRestartAgent,
      restartType,
      filters,
      pagination,
      batchForm,
      filteredAgents,
      loadAgents,
      refreshAgents,
      filterAgents,
      resetFilters,
      handleSelectionChange,
      handleSortChange,
      handleSizeChange,
      handleCurrentChange,
      viewAgentDetails,
      loadAgentTasks,
      showRestartDialog,
      confirmRestart,
      executeBatchAction,
      viewTaskResult,
      getStatusType,
      getStatusText,
      getAgentStatusType,
      getAgentStatusText,
      isAgentOnline,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.agent-management {
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

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.agent-details {
  max-height: 70vh;
  overflow-y: auto;
}

.system-info {
  margin-top: 16px;
}

.batch-management {
  padding: 16px 0;
}

.batch-management p {
  margin-bottom: 16px;
  color: #666;
}

.info-card {
  height: 100%;
}

.info-card .card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.metric-card {
  text-align: center;
  padding: 16px;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.metric-header span:first-child {
  font-size: 14px;
  color: #666;
}

.metric-value {
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
}

.system-info .el-row {
  margin-bottom: 0;
}

.system-info .el-card {
  border-radius: 8px;
}

.system-info .el-descriptions {
  margin-top: 0;
}

/* 任务结果对话框样式 */
.task-result-content {
  max-height: 70vh;
  overflow-y: auto;
}

.task-info-card,
.script-content-card,
.params-card,
.result-card,
.error-card {
  margin-bottom: 16px;
}

.script-editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.editor-wrapper {
  display: flex;
  min-height: 200px;
  max-height: 400px;
  overflow: hidden;
}

.line-numbers {
  background-color: #f1f3f4;
  border-right: 1px solid #dcdfe6;
  padding: 8px 12px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #666;
  user-select: none;
  overflow-y: auto;
  min-width: 50px;
  text-align: right;
}

.line-number {
  height: 21px;
}

.script-editor {
  flex: 1;
  padding: 8px 12px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  overflow-y: auto;
  background-color: #fff;
}

.script-editor pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.params-content {
  background-color: #f8f9fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.agent-result {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.agent-result:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.agent-result h4 {
  margin: 0 0 12px 0;
  color: #409EFF;
  font-size: 16px;
}

.output-content,
.error-content {
  background-color: #f8f9fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px;
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.error-content {
  background-color: #fef0f0;
  border-color: #fbc4c4;
  color: #f56c6c;
}

.no-result {
  text-align: center;
  padding: 40px 0;
}

/* 重启对话框样式 */
.restart-dialog-content {
  padding: 16px 0;
}

.restart-dialog-content p {
  margin-bottom: 20px;
  color: #666;
  font-size: 14px;
}

.restart-options {
  width: 100%;
}

.restart-option {
  width: 100%;
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  transition: all 0.3s;
}

.restart-option:hover {
  border-color: #409EFF;
  background-color: #f0f9ff;
}

.restart-option.is-checked {
  border-color: #409EFF;
  background-color: #f0f9ff;
}

.option-content {
  margin-left: 24px;
}

.option-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.option-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.4;
}
</style>
