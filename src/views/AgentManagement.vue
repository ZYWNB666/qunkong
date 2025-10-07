<template>
  <div class="agent-management">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="page-title">Agent管理</span>
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
            <el-button type="primary" @click="refreshAgents" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="resetFilters">
              <el-icon><Delete /></el-icon>
              重置筛选
            </el-button>
            <el-button type="danger" @click="quickDeleteDownAgents" plain>
              <el-icon><Delete /></el-icon>
              清理DOWN状态
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
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="text" @click="viewAgentDetails(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button 
              type="text" 
              @click="openTerminal(row)"
              :disabled="row.status !== 'ONLINE'"
              style="color: #67c23a"
            >
              <el-icon><Monitor /></el-icon>
              终端
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
                      <span class="metric-value">{{ currentAgent.system_info.cpu_usage?.toFixed(1) || 0 }}%</span>
                    </div>
                    <el-progress 
                      :percentage="currentAgent.system_info.cpu_usage || 0" 
                      :show-text="false" 
                      :color="getCpuColor(currentAgent.system_info.cpu_usage || 0)"
                    />
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card class="metric-card">
                    <div class="metric-header">
                      <span>内存使用率</span>
                      <span class="metric-value">{{ currentAgent.system_info.memory_usage?.toFixed(1) || 0 }}%</span>
                    </div>
                    <el-progress 
                      :percentage="currentAgent.system_info.memory_usage || 0" 
                      :show-text="false" 
                      :color="getMemoryColor(currentAgent.system_info.memory_usage || 0)"
                    />
                  </el-card>
                </el-col>
                <el-col :span="8">
                  <el-card class="metric-card">
                    <div class="metric-header">
                      <span>磁盘使用率</span>
                      <span class="metric-value">{{ currentAgent.system_info.disk_usage?.toFixed(1) || 0 }}%</span>
                    </div>
                    <el-progress 
                      :percentage="currentAgent.system_info.disk_usage || 0" 
                      :show-text="false" 
                      :color="getDiskColor(currentAgent.system_info.disk_usage || 0)"
                    />
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
              <el-radio value="delete_down">删除DOWN状态Agent</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="batchForm.action === 'update'" label="目标版本">
            <el-input v-model="batchForm.version" placeholder="请输入目标版本" />
          </el-form-item>
          <el-form-item v-if="batchForm.action === 'delete_down'">
            <el-alert
              title="警告"
              type="warning"
              description="此操作将永久删除所有选中的DOWN或OFFLINE状态的Agent，无法恢复！"
              :closable="false"
              show-icon
            />
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
              <div class="option-desc">仅重启Qunkong Agent服务，不影响主机运行</div>
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

    <!-- 终端对话框 -->
    <el-dialog
      v-model="showTerminalDialog"
      :title="`安全终端 - ${currentTerminalAgent?.hostname || 'Unknown'}`"
      width="80%"
      height="70vh"
      :close-on-click-modal="false"
      @close="closeTerminal"
      class="terminal-dialog"
    >
      <div v-if="currentTerminalAgent" class="terminal-container" ref="terminalContainer">
        <!-- 终端状态栏 -->
        <div class="terminal-header">
          <div class="terminal-info">
            <el-tag :type="getTerminalStatusType()" size="small">
              <el-icon><Monitor /></el-icon>
              {{ getTerminalStatusText() }}
            </el-tag>
            <span class="agent-info">
              📍 {{ currentTerminalAgent.hostname }} ({{ currentTerminalAgent.ip }})
            </span>
          </div>
          <div class="terminal-actions">
            <el-button size="small" @click="clearTerminal" :disabled="terminalStatus !== 'connected'">
              <el-icon><Delete /></el-icon>
              清屏
            </el-button>
            <el-button size="small" type="info" @click="showCommandHelp = !showCommandHelp">
              <el-icon><QuestionFilled /></el-icon>
              帮助
            </el-button>
          </div>
        </div>

        <!-- 命令帮助 -->
        <el-collapse-transition>
          <div v-show="showCommandHelp" class="command-help">
            <el-alert
              title="🔒 安全终端使用说明"
              type="info"
              :closable="false"
            >
              <template #default>
                <p><strong>基本操作：</strong></p>
                <ul>
                  <li>• 按 <kbd>Enter</kbd> 执行命令</li>
                  <li>• 按 <kbd>↑</kbd>/<kbd>↓</kbd> 浏览历史命令</li>
                  <li>• 输入 <code>exit</code> 或 <code>quit</code> 退出终端</li>
                </ul>
                <p><strong>安全限制：</strong></p>
                <ul>
                  <li>• 仅允许执行白名单中的安全命令</li>
                  <li>• 禁止执行危险的系统操作（如删除、格式化等）</li>
                  <li>• 命令执行超时限制为30秒</li>
                  <li>• 所有操作都会被记录和审计</li>
                </ul>
              </template>
            </el-alert>
          </div>
        </el-collapse-transition>

        <!-- xterm.js 终端容器 -->
        <div 
          v-if="terminalStatus === 'connected'"
          class="xterm-container" 
          ref="terminalContainer"
        ></div>

        <!-- 连接状态提示 -->
        <div v-else class="terminal-status-message">
          <el-empty
            :image-size="80"
            :description="getTerminalStatusText()"
          >
            <template #image>
              <el-icon size="80" :color="terminalStatus === 'error' ? '#f56c6c' : '#409eff'">
                <Monitor />
              </el-icon>
            </template>
            <el-button
              v-if="terminalStatus === 'error' || terminalStatus === 'disconnected'"
              type="primary"
              @click="connectTerminalWebSocket(currentTerminalAgent.id)"
            >
              重新连接
            </el-button>
          </el-empty>
        </div>
      </div>
      
      <template #footer>
        <div class="terminal-footer">
          <span class="terminal-tips">
            <el-icon><InfoFilled /></el-icon>
            提示: 使用 ↑/↓ 键浏览命令历史，Ctrl+C 中断当前操作
          </span>
          <el-button @click="closeTerminal">关闭终端</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, scriptApi } from '../api'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

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
    const refreshTimer = ref(null)
    const refreshInterval = ref(5000) // 默认5秒刷新
    
    // 终端相关状态 - xterm.js
    const showTerminalDialog = ref(false)
    const currentTerminalAgent = ref(null)
    const terminalStatus = ref('disconnected') // 'disconnected', 'connecting', 'connected', 'error'
    const currentSessionId = ref(null)
    const terminalWebSocket = ref(null)
    const showCommandHelp = ref(false)
    const terminalContainer = ref(null)
    
    // xterm.js 相关
    const terminal = ref(null)
    const fitAddon = ref(null)
    const webLinksAddon = ref(null)

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

    const loadAgents = async (showLoading = true) => {
      try {
        if (showLoading) {
          loading.value = true
        }
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
        if (showLoading) {
          ElMessage.error('加载Agent列表失败')
        }
      } finally {
        if (showLoading) {
          loading.value = false
        }
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

    const startAutoRefresh = (interval = refreshInterval.value) => {
      // 清除已存在的定时器
      stopAutoRefresh()
      
      // 如果间隔为0，则不启动定时器
      if (interval <= 0) {
        return
      }
      
      // 设置自动刷新
      refreshTimer.value = setInterval(() => {
        loadAgents(false) // 静默刷新，不显示loading
      }, interval)
    }

    const stopAutoRefresh = () => {
      if (refreshTimer.value) {
        clearInterval(refreshTimer.value)
        refreshTimer.value = null
      }
    }

    const handleRefreshIntervalChange = (newInterval) => {
      // 保存用户偏好到本地存储
      localStorage.setItem('agentManagementRefreshInterval', newInterval.toString())
      
      // 重新启动自动刷新
      startAutoRefresh(newInterval)
    }

    const loadUserPreferences = () => {
      // 从本地存储加载用户偏好
      const savedInterval = localStorage.getItem('agentManagementRefreshInterval')
      if (savedInterval !== null) {
        refreshInterval.value = parseInt(savedInterval)
      }
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
          system_info: null // 初始为null，等待从服务器获取
        }
        
        // 获取详细的系统信息
        try {
          const detailedData = await agentApi.getAgentDetails(agent.id)
          if (detailedData && detailedData.system_info) {
            currentAgent.value.system_info = detailedData.system_info
          } else {
            // 如果没有系统信息，设置默认提示
            currentAgent.value.system_info = {
              os: '暂无数据',
              kernel: '暂无数据',
              cpu: '暂无数据',
              memory: '暂无数据',
              disk: '暂无数据',
              network: '暂无数据',
              uptime: '暂无数据',
              load_average: '暂无数据',
              cpu_usage: 0,
              memory_usage: 0,
              disk_usage: 0
            }
          }
        } catch (detailError) {
          console.log('获取详细信息失败:', detailError)
          // 设置错误状态的系统信息
          currentAgent.value.system_info = {
            os: '获取失败',
            kernel: '获取失败',
            cpu: '获取失败',
            memory: '获取失败',
            disk: '获取失败',
            network: '获取失败',
            uptime: '获取失败',
            load_average: '获取失败',
            cpu_usage: 0,
            memory_usage: 0,
            disk_usage: 0
          }
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

      // 获取操作类型的中文描述
      const actionTextMap = {
        'restart': '重启服务',
        'update': '更新版本',
        'stop': '停止服务',
        'delete_down': '删除DOWN状态Agent'
      }
      const actionText = actionTextMap[batchForm.action] || batchForm.action

      try {
        // 特殊处理删除操作的确认提示
        let confirmMessage = `确定要对 ${selectedAgents.value.length} 个Agent执行 ${actionText} 操作吗？`
        if (batchForm.action === 'delete_down') {
          confirmMessage = `确定要删除选中的 ${selectedAgents.value.length} 个Agent吗？\n\n⚠️ 此操作将永久删除所有DOWN或OFFLINE状态的Agent，无法恢复！`
        }

        await ElMessageBox.confirm(
          confirmMessage,
          '确认批量操作',
          { 
            type: 'warning',
            confirmButtonText: batchForm.action === 'delete_down' ? '确认删除' : '确认',
            cancelButtonText: '取消'
          }
        )
        
        // 调用批量管理API
        const agentIds = selectedAgents.value.map(agent => agent.id)
        const response = await agentApi.batchManageAgents({
          action: batchForm.action,
          agent_ids: agentIds,
          version: batchForm.version
        })
        
        // 显示操作结果
        if (response.success_count > 0) {
          ElMessage.success(`批量操作完成：成功 ${response.success_count}/${response.total_count}`)
        } else {
          ElMessage.warning(`批量操作完成：成功 ${response.success_count}/${response.total_count}`)
        }
        
        // 显示详细结果
        if (response.results && response.results.length > 0) {
          const failedResults = response.results.filter(r => !r.success)
          if (failedResults.length > 0) {
            console.log('批量操作失败的Agent:', failedResults)
          }
        }
        
        showBatchDialog.value = false
        
        // 刷新Agent列表
        setTimeout(() => {
          refreshAgents()
        }, 1000)
        
      } catch (error) {
        if (error !== 'cancel' && error.message !== 'cancel') {
          ElMessage.error('批量操作失败: ' + (error.response?.data?.error || error.message || '未知错误'))
        }
      }
    }

    const quickDeleteDownAgents = async () => {
      try {
        // 筛选出所有DOWN或OFFLINE状态的Agent
        const downAgents = agents.value.filter(agent => 
          agent.status === 'DOWN' || agent.status === 'OFFLINE'
        )
        
        if (downAgents.length === 0) {
          ElMessage.info('没有找到DOWN或OFFLINE状态的Agent')
          return
        }
        
        await ElMessageBox.confirm(
          `检测到 ${downAgents.length} 个DOWN或OFFLINE状态的Agent，确定要全部删除吗？\n\n⚠️ 此操作将永久删除这些Agent，无法恢复！`,
          '确认批量删除',
          { 
            type: 'warning',
            confirmButtonText: '确认删除',
            cancelButtonText: '取消'
          }
        )
        
        // 调用批量删除API
        const agentIds = downAgents.map(agent => agent.id)
        const response = await agentApi.batchManageAgents({
          action: 'delete_down',
          agent_ids: agentIds
        })
        
        // 显示操作结果
        if (response.success_count > 0) {
          ElMessage.success(`成功删除 ${response.success_count} 个Agent`)
        } else {
          ElMessage.warning(`删除失败，请检查日志`)
        }
        
        // 刷新Agent列表
        setTimeout(() => {
          refreshAgents()
        }, 1000)
        
      } catch (error) {
        if (error !== 'cancel' && error.message !== 'cancel') {
          ElMessage.error('删除操作失败: ' + (error.response?.data?.error || error.message || '未知错误'))
        }
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
        
        // 调用重启API
        if (restartType.value === 'host') {
          await agentApi.restartHost(currentRestartAgent.value.id)
          ElMessage.success(`主机 ${currentRestartAgent.value.hostname} 重启请求已发送`)
        } else {
          await agentApi.restartAgent(currentRestartAgent.value.id)
          ElMessage.success(`Agent ${currentRestartAgent.value.hostname} 重启请求已发送`)
        }
        
        showRestartConfirmDialog.value = false
        currentRestartAgent.value = null
        
        // 刷新Agent列表
        setTimeout(() => {
          refreshAgents()
        }, 2000)
        
      } catch (error) {
        if (error.message && error.message !== 'cancel') {
          ElMessage.error('重启操作失败: ' + (error.response?.data?.error || error.message))
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

    const getCpuColor = (usage) => {
      if (usage < 50) return '#67c23a'  // 绿色
      if (usage < 80) return '#e6a23c'  // 橙色
      return '#f56c6c'  // 红色
    }

    const getMemoryColor = (usage) => {
      if (usage < 60) return '#67c23a'  // 绿色
      if (usage < 85) return '#e6a23c'  // 橙色
      return '#f56c6c'  // 红色
    }

    const getDiskColor = (usage) => {
      if (usage < 70) return '#67c23a'  // 绿色
      if (usage < 90) return '#e6a23c'  // 橙色
      return '#f56c6c'  // 红色
    }
    
    // 终端相关方法
    const openTerminal = async (agent) => {
      if (agent.status !== 'ONLINE') {
        ElMessage.warning('Agent不在线，无法打开终端')
        return
      }
      
      currentTerminalAgent.value = agent
      showTerminalDialog.value = true
      terminalStatus.value = 'connecting'
      
      // 延迟等待对话框完全打开
      await nextTick()
      await new Promise(resolve => setTimeout(resolve, 300))
      
      // 初始化xterm.js终端
      initializeTerminal()
      
      // 建立WebSocket连接
      connectTerminalWebSocket(agent.id)
    }
    
    const initializeTerminal = () => {
      try {
        // 清理已有的终端
        if (terminal.value) {
          terminal.value.dispose()
        }
        
        // 创建新的终端实例
        terminal.value = new Terminal({
          theme: {
            background: '#1e1e1e',
            foreground: '#d4d4d4',
            cursor: '#d4d4d4',
            selection: '#264F78',
            black: '#000000',
            red: '#cd3131',
            green: '#0dbc79',
            yellow: '#e5e510',
            blue: '#2472c8',
            magenta: '#bc3fbc',
            cyan: '#11a8cd',
            white: '#e5e5e5',
            brightBlack: '#666666',
            brightRed: '#f14c4c',
            brightGreen: '#23d18b',
            brightYellow: '#f5f543',
            brightBlue: '#3b8eea',
            brightMagenta: '#d670d6',
            brightCyan: '#29b8db',
            brightWhite: '#e5e5e5'
          },
          fontSize: 14,
          fontFamily: 'Consolas, "Courier New", monospace',
          cursorBlink: true,
          convertEol: true,
          scrollback: 1000,
          tabStopWidth: 4
        })
        
        // 创建并加载插件
        fitAddon.value = new FitAddon()
        webLinksAddon.value = new WebLinksAddon()
        
        terminal.value.loadAddon(fitAddon.value)
        terminal.value.loadAddon(webLinksAddon.value)
        
        // 将终端挂载到DOM元素
        terminal.value.open(terminalContainer.value)
        
        // 调整终端大小以适应容器
        fitAddon.value.fit()
        
        // 监听窗口大小变化
        window.addEventListener('resize', handleTerminalResize)
        
        // 监听终端输入
        terminal.value.onData((data) => {
          if (terminalWebSocket.value && terminalWebSocket.value.readyState === WebSocket.OPEN) {
            const message = {
              type: 'terminal_input',
              data: data
            }
            terminalWebSocket.value.send(JSON.stringify(message))
          }
        })
        
        console.log('xterm.js终端初始化成功')
        
      } catch (error) {
        console.error('初始化终端失败:', error)
        ElMessage.error('终端初始化失败')
        terminalStatus.value = 'error'
      }
    }
    
    const handleTerminalResize = () => {
      if (fitAddon.value && terminal.value) {
        try {
          fitAddon.value.fit()
          // 发送终端大小变化消息
          if (terminalWebSocket.value && terminalWebSocket.value.readyState === WebSocket.OPEN) {
            const message = {
              type: 'terminal_resize',
              cols: terminal.value.cols,
              rows: terminal.value.rows
            }
            terminalWebSocket.value.send(JSON.stringify(message))
          }
        } catch (error) {
          console.error('调整终端大小失败:', error)
        }
      }
    }
    
    const connectTerminalWebSocket = (agentId) => {
      try {
        const wsUrl = `ws://${__WEBSOCKET_HOST__}:${__WEBSOCKET_PORT__}/terminal/${agentId}`
        console.log('连接PTY终端WebSocket:', wsUrl)
        
        terminalWebSocket.value = new WebSocket(wsUrl)
        
        terminalWebSocket.value.onopen = () => {
          console.log('PTY终端WebSocket连接已建立')
          terminalStatus.value = 'connected'
          ElMessage.success('终端连接成功')
          
          // 后端会自动处理初始化，前端只需要等待 terminal_ready 消息
        }
        
        terminalWebSocket.value.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            handleTerminalMessage(data)
          } catch (error) {
            console.error('解析终端消息失败:', error)
            // 如果不是JSON，可能是二进制数据
            if (terminal.value) {
              terminal.value.write(event.data)
            }
          }
        }
        
        terminalWebSocket.value.onclose = () => {
          console.log('PTY终端WebSocket连接已关闭')
          terminalStatus.value = 'disconnected'
          if (showTerminalDialog.value) {
            ElMessage.warning('终端连接已断开')
          }
        }
        
        terminalWebSocket.value.onerror = (error) => {
          console.error('PTY终端WebSocket连接错误:', error)
          terminalStatus.value = 'error'
          ElMessage.error('终端连接失败')
        }
        
      } catch (error) {
        console.error('建立PTY终端WebSocket连接失败:', error)
        terminalStatus.value = 'error'
        ElMessage.error('无法建立终端连接')
      }
    }
    
    const handleTerminalMessage = (data) => {
      switch (data.type) {
        case 'terminal_ready':
          console.log('终端就绪:', data)
          currentSessionId.value = data.session_id
          
          // 发送当前终端大小
          if (terminal.value && terminalWebSocket.value && terminalWebSocket.value.readyState === WebSocket.OPEN) {
            const resizeMessage = {
              type: 'terminal_resize',
              cols: terminal.value.cols,
              rows: terminal.value.rows
            }
            terminalWebSocket.value.send(JSON.stringify(resizeMessage))
          }
          break
        case 'terminal_data':
          // 将数据写入xterm.js终端
          if (terminal.value && data.data) {
            terminal.value.write(data.data)
          }
          break
        case 'terminal_error':
          console.error('终端错误:', data.error)
          if (terminal.value) {
            terminal.value.write(`\r\n\x1b[31m❌ ${data.error}\x1b[0m\r\n`)
          }
          ElMessage.error(data.error)
          break
        case 'terminal_pong':
          // 心跳响应，不需要特殊处理
          break
        default:
          console.log('收到未知终端消息:', data)
      }
    }
    
    const clearTerminal = () => {
      if (terminal.value) {
        terminal.value.clear()
      }
    }
    
    const closeTerminal = () => {
      try {
        // 清理事件监听器
        window.removeEventListener('resize', handleTerminalResize)
        
        // 关闭WebSocket连接
        if (terminalWebSocket.value) {
          try {
            terminalWebSocket.value.close()
          } catch (error) {
            console.warn('关闭WebSocket连接时出错:', error)
          }
          terminalWebSocket.value = null
        }
        
        // 清理xterm.js实例和插件
        if (terminal.value) {
          try {
            // 清理插件引用，避免dispose时的插件错误
            if (fitAddon.value) {
              fitAddon.value = null
            }
            
            if (webLinksAddon.value) {
              webLinksAddon.value = null
            }
            
            // 清理终端实例（会自动清理已加载的插件）
            terminal.value.dispose()
            terminal.value = null
            
          } catch (error) {
            console.warn('清理终端实例时出错:', error)
            // 强制清理引用，避免内存泄漏
            terminal.value = null
          }
        }
        
        // 清理插件引用
        fitAddon.value = null
        webLinksAddon.value = null
        
        console.log('PTY终端WebSocket连接已关闭')
        
      } catch (error) {
        console.error('关闭终端时发生错误:', error)
      } finally {
        // 无论如何都要重置状态
        showTerminalDialog.value = false
        currentTerminalAgent.value = null
        terminalStatus.value = 'disconnected'
        currentSessionId.value = null
      }
    }
    
    const getTerminalStatusText = () => {
      switch (terminalStatus.value) {
        case 'connecting': return '连接中...'
        case 'connected': return '已连接'
        case 'disconnected': return '已断开'
        case 'error': return '连接错误'
        default: return '未知状态'
      }
    }
    
    const getTerminalStatusType = () => {
      switch (terminalStatus.value) {
        case 'connecting': return 'warning'
        case 'connected': return 'success'
        case 'disconnected': return 'info'
        case 'error': return 'danger'
        default: return 'info'
      }
    }

    onMounted(() => {
      loadUserPreferences()
      loadAgents()
      startAutoRefresh()
    })

    onUnmounted(() => {
      stopAutoRefresh()
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
      refreshInterval,
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
      quickDeleteDownAgents,
      viewTaskResult,
      getStatusType,
      getStatusText,
      getAgentStatusType,
      getAgentStatusText,
      isAgentOnline,
      formatDateTime,
      startAutoRefresh,
      stopAutoRefresh,
      handleRefreshIntervalChange,
      getCpuColor,
      getMemoryColor,
      getDiskColor,
      // 终端相关
      showTerminalDialog,
      currentTerminalAgent,
      terminalStatus,
      showCommandHelp,
      terminalContainer,
      openTerminal,
      clearTerminal,
      closeTerminal,
      getTerminalStatusText,
      getTerminalStatusType,
      // xterm.js相关
      terminal,
      fitAddon,
      webLinksAddon
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

/* 终端样式 */
.terminal-dialog {
  --terminal-bg: #1e1e1e;
  --terminal-text: #d4d4d4;
  --terminal-border: #333;
  --terminal-error: #f85552;
  --terminal-success: #16a085;
  --terminal-warning: #f39c12;
}

.terminal-dialog .el-dialog__body {
  padding: 0;
  height: calc(70vh - 120px);
  overflow: hidden;
}

.terminal-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--terminal-bg);
  color: var(--terminal-text);
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'Courier New', monospace;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2d2d30;
  border-bottom: 1px solid var(--terminal-border);
  flex-shrink: 0;
}

.terminal-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-info {
  font-size: 13px;
  color: #cccccc;
}

.terminal-actions {
  display: flex;
  gap: 8px;
}

.command-help {
  background: #252526;
  padding: 16px;
  border-bottom: 1px solid var(--terminal-border);
}

.command-help .el-alert {
  background: rgba(24, 144, 255, 0.1);
  border: 1px solid rgba(24, 144, 255, 0.2);
}

.command-help p {
  margin: 8px 0;
  color: var(--terminal-text);
}

.command-help ul {
  margin: 8px 0;
  padding-left: 20px;
  color: var(--terminal-text);
}

.command-help li {
  margin: 4px 0;
}

.command-help kbd {
  background: #3c3c3c;
  color: #ffffff;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  border: 1px solid #666;
}

.command-help code {
  background: #3c3c3c;
  color: #ce9178;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 12px;
}

/* xterm.js 终端容器 */
.xterm-container {
  flex: 1;
  overflow: hidden;
  background: var(--terminal-bg);
  padding: 8px;
  height: 500px; /* 设置固定高度 */
}

/* 确保xterm.js终端的样式正确 */
.xterm-container .xterm {
  height: 100% !important;
}

.xterm-container .xterm-viewport {
  background-color: var(--terminal-bg) !important;
}

/* 保留连接状态的样式 */
.terminal-content.connecting {
  color: var(--terminal-warning);
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}


.terminal-status-message {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--terminal-bg);
}

.terminal-status-message .el-empty__description {
  color: var(--terminal-text);
}

.terminal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
}

.terminal-tips {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666;
}

/* 滚动条样式 */
.terminal-output::-webkit-scrollbar {
  width: 8px;
}

.terminal-output::-webkit-scrollbar-track {
  background: #2d2d30;
}

.terminal-output::-webkit-scrollbar-thumb {
  background: #424245;
  border-radius: 4px;
}

.terminal-output::-webkit-scrollbar-thumb:hover {
  background: #4c4c4c;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .terminal-dialog {
    width: 95% !important;
  }
  
  .terminal-header {
    flex-direction: column;
    gap: 8px;
    align-items: stretch;
  }
  
  .terminal-info {
    justify-content: center;
  }
  
  .terminal-actions {
    justify-content: center;
  }
}
</style>
