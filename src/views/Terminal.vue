<template>
  <div class="terminal-page">
    <!-- 终端头部 -->
    <div class="terminal-header">
      <div class="header-left">
        <div class="logo">
          <el-icon><Monitor /></el-icon>
          <span>Qunkong Terminal</span>
        </div>
        <div class="agent-info" v-if="agentInfo">
          <el-tag :type="getConnectionStatusType()" size="small">
            <el-icon><Connection /></el-icon>
            {{ getConnectionStatusText() }}
          </el-tag>
          <span class="agent-details">
            📍 {{ agentInfo.hostname }} ({{ agentInfo.ip }})
          </span>
        </div>
      </div>
      
      <div class="header-right">
        <el-button-group size="small">
          <el-button @click="clearTerminal" :disabled="terminalStatus !== 'connected'">
            <el-icon><Delete /></el-icon>
            清屏
          </el-button>
          <el-button @click="showHelp = !showHelp">
            <el-icon><QuestionFilled /></el-icon>
            帮助
          </el-button>
          <el-button @click="reconnect" :disabled="terminalStatus === 'connecting'">
            <el-icon><Refresh /></el-icon>
            重连
          </el-button>
          <el-button type="danger" @click="closeTerminal">
            <el-icon><Close /></el-icon>
            关闭
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 帮助面板 -->
    <el-collapse-transition>
      <div v-show="showHelp" class="help-panel">
        <el-alert
          title="🔒 安全终端使用说明"
          type="info"
          :closable="false"
        >
          <template #default>
            <div class="help-content">
              <div class="help-section">
                <h4>基本操作</h4>
                <ul>
                  <li>按 <kbd>Enter</kbd> 执行命令</li>
                  <li>按 <kbd>↑</kbd>/<kbd>↓</kbd> 浏览历史命令</li>
                  <li>按 <kbd>Ctrl+C</kbd> 中断当前命令</li>
                  <li>按 <kbd>Ctrl+D</kbd> 发送EOF信号</li>
                  <li>输入 <code>exit</code> 或 <code>logout</code> 退出会话</li>
                </ul>
              </div>
              
              <div class="help-section">
                <h4>快捷键</h4>
                <ul>
                  <li><kbd>Ctrl+L</kbd> - 清屏（等同于clear命令）</li>
                  <li><kbd>Tab</kbd> - 自动补全</li>
                  <li><kbd>Ctrl+A</kbd> - 光标移到行首</li>
                  <li><kbd>Ctrl+E</kbd> - 光标移到行尾</li>
                  <li><kbd>Ctrl+U</kbd> - 删除光标前的内容</li>
                  <li><kbd>Ctrl+K</kbd> - 删除光标后的内容</li>
                </ul>
              </div>
              
              <div class="help-section">
                <h4>安全限制</h4>
                <ul>
                  <li>仅允许执行白名单中的安全命令</li>
                  <li>禁止执行危险的系统操作（如删除、格式化等）</li>
                  <li>命令执行超时限制为30秒</li>
                  <li>所有操作都会被记录和审计</li>
                </ul>
              </div>
            </div>
          </template>
        </el-alert>
      </div>
    </el-collapse-transition>

    <!-- 连接状态提示 -->
    <div v-if="terminalStatus !== 'connected'" class="status-overlay">
      <div class="status-content">
        <el-icon v-if="terminalStatus === 'connecting'" class="loading-icon"><Loading /></el-icon>
        <el-icon v-else-if="terminalStatus === 'error'" class="error-icon"><Warning /></el-icon>
        <el-icon v-else class="disconnected-icon"><Connection /></el-icon>
        
        <h3>{{ getStatusTitle() }}</h3>
        <p>{{ getStatusMessage() }}</p>
        
        <el-button 
          v-if="terminalStatus === 'error' || terminalStatus === 'disconnected'"
          type="primary" 
          @click="reconnect"
          :loading="terminalStatus === 'connecting'"
        >
          <el-icon><Refresh /></el-icon>
          重新连接
        </el-button>
      </div>
    </div>

    <!-- xterm.js 终端容器 -->
    <div 
      v-show="terminalStatus === 'connected'"
      class="terminal-container" 
      ref="terminalContainer"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Monitor, Connection, Delete, QuestionFilled, Refresh, Close, 
  Loading, Warning 
} from '@element-plus/icons-vue'

// 导入xterm.js
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { WebLinksAddon } from 'xterm-addon-web-links'
import 'xterm/css/xterm.css'

const route = useRoute()
const router = useRouter()

// 响应式数据
const agentInfo = ref(null)
const terminalStatus = ref('connecting') // connecting, connected, disconnected, error
const showHelp = ref(false)
const currentSessionId = ref(null)

// xterm.js相关
const terminal = ref(null)
const fitAddon = ref(null)
const webLinksAddon = ref(null)
const terminalContainer = ref(null)
const terminalWebSocket = ref(null)

// 从URL参数获取Agent信息
onMounted(async () => {
  const agentId = route.params.agentId
  const hostname = route.query.hostname
  const ip = route.query.ip
  
  if (!agentId || !hostname || !ip) {
    ElMessage.error('缺少必要的连接参数')
    router.push('/agents')
    return
  }
  
  agentInfo.value = {
    id: agentId,
    hostname: hostname,
    ip: ip
  }
  
  // 设置页面标题
  document.title = `Terminal - ${hostname} - Qunkong`
  
  // 等待DOM渲染完成后初始化终端
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 100))
  
  initializeTerminal()
  connectTerminalWebSocket(agentId)
})

onUnmounted(() => {
  cleanup()
})

// 窗口关闭前确认
window.addEventListener('beforeunload', (e) => {
  if (terminalStatus.value === 'connected') {
    e.preventDefault()
    e.returnValue = '终端连接将会断开，确定要关闭吗？'
  }
})

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
      fontSize: 16,
      fontFamily: 'Consolas, "Courier New", monospace',
      cursorBlink: true,
      convertEol: true,
      scrollback: 5000,
      tabStopWidth: 4,
      allowTransparency: false
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
    
    // 终端获得焦点
    terminal.value.focus()
    
    console.log('终端初始化完成')
  } catch (error) {
    console.error('初始化终端失败:', error)
    ElMessage.error('终端初始化失败')
  }
}

const connectTerminalWebSocket = (agentId) => {
  try {
    const wsUrl = `ws://${window.location.hostname}:18765/terminal/${agentId}`
    console.log('连接终端WebSocket:', wsUrl)
    
    terminalWebSocket.value = new WebSocket(wsUrl)
    
    terminalWebSocket.value.onopen = () => {
      console.log('终端WebSocket连接已建立')
      terminalStatus.value = 'connected'
      ElMessage.success('终端连接成功')
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
      console.log('终端WebSocket连接已关闭')
      terminalStatus.value = 'disconnected'
      ElMessage.warning('终端连接已断开')
    }
    
    terminalWebSocket.value.onerror = (error) => {
      console.error('终端WebSocket连接错误:', error)
      terminalStatus.value = 'error'
      ElMessage.error('终端连接失败')
    }
    
  } catch (error) {
    console.error('建立终端WebSocket连接失败:', error)
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

const handleTerminalResize = () => {
  if (fitAddon.value && terminal.value) {
    fitAddon.value.fit()
    
    // 发送新的终端大小到服务器
    if (terminalWebSocket.value && terminalWebSocket.value.readyState === WebSocket.OPEN) {
      const resizeMessage = {
        type: 'terminal_resize',
        cols: terminal.value.cols,
        rows: terminal.value.rows
      }
      terminalWebSocket.value.send(JSON.stringify(resizeMessage))
    }
  }
}

const clearTerminal = () => {
  if (terminal.value) {
    terminal.value.clear()
  }
}

const reconnect = () => {
  if (terminalStatus.value === 'connecting') return
  
  cleanup()
  terminalStatus.value = 'connecting'
  
  setTimeout(() => {
    initializeTerminal()
    connectTerminalWebSocket(agentInfo.value.id)
  }, 1000)
}

const closeTerminal = async () => {
  if (terminalStatus.value === 'connected') {
    try {
      await ElMessageBox.confirm(
        '终端连接将会断开，确定要关闭吗？',
        '确认关闭',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
    } catch {
      return // 用户取消
    }
  }
  
  cleanup()
  window.close()
}

const cleanup = () => {
  // 清理WebSocket连接
  if (terminalWebSocket.value) {
    terminalWebSocket.value.close()
    terminalWebSocket.value = null
  }
  
  // 清理终端实例
  if (terminal.value) {
    terminal.value.dispose()
    terminal.value = null
  }
  
  // 移除事件监听器
  window.removeEventListener('resize', handleTerminalResize)
}

// 状态相关方法
const getConnectionStatusType = () => {
  switch (terminalStatus.value) {
    case 'connected': return 'success'
    case 'connecting': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

const getConnectionStatusText = () => {
  switch (terminalStatus.value) {
    case 'connected': return '已连接'
    case 'connecting': return '连接中'
    case 'error': return '连接错误'
    case 'disconnected': return '已断开'
    default: return '未知状态'
  }
}

const getStatusTitle = () => {
  switch (terminalStatus.value) {
    case 'connecting': return '正在连接终端...'
    case 'error': return '连接失败'
    case 'disconnected': return '连接已断开'
    default: return '未知状态'
  }
}

const getStatusMessage = () => {
  switch (terminalStatus.value) {
    case 'connecting': return '正在建立与远程主机的安全连接，请稍候...'
    case 'error': return '无法连接到远程主机，请检查网络连接或稍后重试'
    case 'disconnected': return '与远程主机的连接已断开，可以尝试重新连接'
    default: return ''
  }
}
</script>

<style scoped>
.terminal-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  color: #d4d4d4;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2d2d30;
  border-bottom: 1px solid #3e3e42;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
  color: #00d4aa;
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-details {
  font-size: 14px;
  color: #cccccc;
}

.help-panel {
  background: #252526;
  border-bottom: 1px solid #3e3e42;
}

.help-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  padding: 16px;
}

.help-section h4 {
  margin: 0 0 8px 0;
  color: #569cd6;
  font-size: 14px;
}

.help-section ul {
  margin: 0;
  padding-left: 16px;
}

.help-section li {
  margin: 4px 0;
  font-size: 13px;
  line-height: 1.4;
}

kbd {
  background: #3c3c3c;
  border: 1px solid #666;
  border-radius: 3px;
  padding: 2px 6px;
  font-size: 12px;
  color: #fff;
}

code {
  background: #3c3c3c;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  color: #ce9178;
}

.status-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(30, 30, 30, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.status-content {
  text-align: center;
  padding: 40px;
  background: #2d2d30;
  border-radius: 8px;
  border: 1px solid #3e3e42;
  max-width: 400px;
}

.loading-icon {
  font-size: 48px;
  color: #409eff;
  animation: rotate 2s linear infinite;
}

.error-icon {
  font-size: 48px;
  color: #f56c6c;
}

.disconnected-icon {
  font-size: 48px;
  color: #909399;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.status-content h3 {
  margin: 16px 0 8px 0;
  color: #d4d4d4;
}

.status-content p {
  margin: 0 0 24px 0;
  color: #999;
  line-height: 1.5;
}

.terminal-container {
  flex: 1;
  padding: 8px;
  background: #1e1e1e;
  overflow: hidden;
}

/* xterm.js样式覆盖 */
:deep(.xterm) {
  height: 100% !important;
}

:deep(.xterm-viewport) {
  background: #1e1e1e !important;
}

:deep(.xterm-screen) {
  background: #1e1e1e !important;
}

/* 滚动条样式 */
:deep(.xterm-viewport)::-webkit-scrollbar {
  width: 8px;
}

:deep(.xterm-viewport)::-webkit-scrollbar-track {
  background: #2d2d30;
}

:deep(.xterm-viewport)::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

:deep(.xterm-viewport)::-webkit-scrollbar-thumb:hover {
  background: #666;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .terminal-header {
    flex-direction: column;
    gap: 12px;
    padding: 12px;
  }
  
  .header-left {
    width: 100%;
    justify-content: center;
  }
  
  .help-content {
    grid-template-columns: 1fr;
  }
}
</style>
