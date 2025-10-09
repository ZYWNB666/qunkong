<template>
  <div class="terminal-page">
    <!-- 左侧Agent列表 -->
    <div class="agent-sidebar">
      <div class="sidebar-header">
        <h3>
          <el-icon><Monitor /></el-icon>
          Agent列表
        </h3>
        <el-button size="small" @click="refreshAgents">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
      
      <!-- 搜索框 -->
      <div class="search-container">
        <el-input
          v-model="searchText"
          placeholder="搜索主机名或IP地址"
          :prefix-icon="Search"
          clearable
          size="small"
        />
      </div>
      
      <div class="agent-list">
        <div 
          v-for="agent in filteredAgents" 
          :key="agent.id"
          class="agent-item"
          :class="{ 
            'active': activeTerminals.some(t => t.agentId === agent.id),
            'online': agent.status === 'ONLINE'
          }"
          @click="openTerminalTab(agent)"
        >
          <div class="agent-info">
            <div class="agent-name">{{ agent.hostname }}</div>
            <div class="agent-ip">{{ agent.ip }}</div>
          </div>
          <div class="agent-status">
            <el-tag 
              :type="agent.status === 'ONLINE' ? 'success' : 'danger'" 
              size="small"
            >
              {{ agent.status === 'ONLINE' ? '在线' : '离线' }}
            </el-tag>
          </div>
        </div>
        
        <!-- 无搜索结果 -->
        <div v-if="filteredAgents.length === 0 && agents.length > 0" class="no-results">
          <el-empty 
            description="未找到匹配的Agent" 
            :image-size="60"
          />
        </div>
      </div>
    </div>

    <!-- 右侧终端区域 -->
    <div class="terminal-area">
      <!-- 终端标签页 -->
      <div v-if="activeTerminals.length === 0" class="empty-terminal">
        <el-empty description="请从左侧选择Agent打开终端">
          <template #image>
            <el-icon size="100" color="#ccc"><Monitor /></el-icon>
          </template>
        </el-empty>
      </div>

      <div v-else class="terminal-tabs-container">
        <!-- 标签页头部 -->
        <div class="terminal-tabs">
          <div 
            v-for="terminal in activeTerminals"
            :key="terminal.id"
            class="terminal-tab"
            :class="{ 'active': currentTerminalId === terminal.id }"
            @click="switchTerminal(terminal.id)"
          >
            <span class="tab-title">{{ terminal.hostname }}</span>
            <div class="tab-status">
              <el-tag 
                :type="getTerminalStatusType(terminal.status)" 
                size="small"
              >
                {{ getTerminalStatusText(terminal.status) }}
              </el-tag>
            </div>
            <el-button 
              class="close-btn"
              size="small" 
              type="text" 
              @click.stop="closeTerminalTab(terminal.id)"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>

        <!-- 终端内容区域 -->
        <div class="terminal-content">
          <div 
            v-for="terminal in activeTerminals"
            :key="terminal.id"
            v-show="currentTerminalId === terminal.id"
            class="terminal-panel"
          >
            <!-- 终端工具栏 -->
            <div class="terminal-toolbar">
              <div class="toolbar-left">
                <span class="terminal-info">
                  📍 {{ terminal.hostname }} ({{ terminal.ip }})
                </span>
              </div>
              <div class="toolbar-right">
                <el-button-group size="small">
                  <el-button @click="clearTerminal(terminal.id)" :disabled="terminal.status !== 'connected'">
                    <el-icon><Delete /></el-icon>
                    清屏
                  </el-button>
                  <el-button @click="toggleHelp">
                    <el-icon><QuestionFilled /></el-icon>
                    帮助
                  </el-button>
                  <el-button @click="reconnectTerminal(terminal.id)" :disabled="terminal.status === 'connecting'">
                    <el-icon><Refresh /></el-icon>
                    重连
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
                        </ul>
                      </div>
                      
                      <div class="help-section">
                        <h4>安全限制</h4>
                        <ul>
                          <li>仅允许执行白名单中的安全命令</li>
                          <li>禁止执行危险的系统操作</li>
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
            <div v-if="terminal.status !== 'connected'" class="status-overlay">
              <div class="status-content">
                <el-icon v-if="terminal.status === 'connecting'" class="loading-icon"><Loading /></el-icon>
                <el-icon v-else-if="terminal.status === 'error'" class="error-icon"><Warning /></el-icon>
                <el-icon v-else class="disconnected-icon"><Connection /></el-icon>
                
                <h3>{{ getStatusTitle(terminal.status) }}</h3>
                <p>{{ getStatusMessage(terminal.status) }}</p>
                
                <el-button 
                  v-if="terminal.status === 'error' || terminal.status === 'disconnected'"
                  type="primary" 
                  @click="reconnectTerminal(terminal.id)"
                  :loading="terminal.status === 'connecting'"
                >
                  <el-icon><Refresh /></el-icon>
                  重新连接
                </el-button>
              </div>
            </div>

            <!-- xterm.js 终端容器 -->
            <div 
              v-show="terminal.status === 'connected'"
              class="terminal-container" 
              :ref="el => setTerminalRef(terminal.id, el)"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Monitor, Connection, Delete, QuestionFilled, Refresh, Close, 
  Loading, Warning, Search
} from '@element-plus/icons-vue'
import axios from 'axios'

// 导入xterm.js
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

const router = useRouter()

// 响应式数据
const agents = ref([])
const activeTerminals = ref([])
const currentTerminalId = ref(null)
const showHelp = ref(false)
const searchText = ref('')

// 终端实例管理
const terminalInstances = ref(new Map()) // terminalId -> { terminal, fitAddon, webLinksAddon }
const terminalRefs = ref(new Map()) // terminalId -> DOM element
const websocketConnections = ref(new Map()) // terminalId -> WebSocket

// 搜索过滤
const filteredAgents = computed(() => {
  if (!searchText.value.trim()) {
    return agents.value
  }
  
  const searchLower = searchText.value.toLowerCase().trim()
  return agents.value.filter(agent => 
    agent.hostname.toLowerCase().includes(searchLower) ||
    agent.ip.toLowerCase().includes(searchLower)
  )
})

// 检查登录状态
const checkAuth = () => {
  const token = localStorage.getItem('qunkong_token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return false
  }
  return true
}

// 页面加载时检查登录状态
onMounted(async () => {
  if (!checkAuth()) return
  
  // 设置页面标题
  document.title = 'Multi Terminal - Qunkong'
  
  // 加载Agent列表
  await loadAgents()
  
  // 监听窗口大小变化，调整所有终端大小
  window.addEventListener('resize', handleGlobalResize)
})

onUnmounted(() => {
  // 清理所有终端连接
  activeTerminals.value.forEach(terminal => {
    cleanupTerminal(terminal.id)
  })
  
  // 移除全局事件监听器
  window.removeEventListener('resize', handleGlobalResize)
})

// 窗口关闭前确认
window.addEventListener('beforeunload', (e) => {
  if (activeTerminals.value.some(t => t.status === 'connected')) {
    e.preventDefault()
    e.returnValue = '存在活跃的终端连接，确定要关闭吗？'
  }
})

const loadAgents = async () => {
  try {
    const token = localStorage.getItem('qunkong_token')
    const response = await axios.get('/api/servers', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    agents.value = response.data || []
  } catch (error) {
    console.error('加载Agent列表失败:', error)
    if (error.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    } else {
      ElMessage.error('加载Agent列表失败')
    }
  }
}

const refreshAgents = () => {
  loadAgents()
}

const openTerminalTab = (agent) => {
  if (agent.status !== 'ONLINE') {
    ElMessage.warning('Agent不在线，无法打开终端')
    return
  }
  
  // 检查是否已经打开了该Agent的终端
  const existingTerminal = activeTerminals.value.find(t => t.agentId === agent.id)
  if (existingTerminal) {
    switchTerminal(existingTerminal.id)
    return
  }
  
  // 创建新的终端标签
  const terminalId = `terminal_${agent.id}_${Date.now()}`
  const newTerminal = {
    id: terminalId,
    agentId: agent.id,
    hostname: agent.hostname,
    ip: agent.ip,
    status: 'connecting',
    sessionId: null
  }
  
  activeTerminals.value.push(newTerminal)
  currentTerminalId.value = terminalId
  
  // 等待DOM更新后初始化终端
  nextTick(() => {
    setTimeout(() => {
      initializeTerminal(terminalId)
      connectTerminalWebSocket(terminalId, agent.id)
    }, 100)
  })
}

const switchTerminal = (terminalId) => {
  currentTerminalId.value = terminalId
  
  // 让当前终端获得焦点并调整大小
  nextTick(() => {
    setTimeout(() => {
      const instance = terminalInstances.value.get(terminalId)
      if (instance?.terminal && instance?.fitAddon) {
        instance.fitAddon.fit()
        instance.terminal.focus()
      }
    }, 50)
  })
}

const closeTerminalTab = async (terminalId) => {
  const terminal = activeTerminals.value.find(t => t.id === terminalId)
  if (terminal?.status === 'connected') {
    try {
      await ElMessageBox.confirm(
        `确定要关闭终端 "${terminal.hostname}" 吗？`,
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
  
  // 清理终端
  cleanupTerminal(terminalId)
  
  // 从活跃列表中移除
  const index = activeTerminals.value.findIndex(t => t.id === terminalId)
  if (index > -1) {
    activeTerminals.value.splice(index, 1)
  }
  
  // 如果关闭的是当前终端，切换到其他终端
  if (currentTerminalId.value === terminalId) {
    if (activeTerminals.value.length > 0) {
      currentTerminalId.value = activeTerminals.value[0].id
      switchTerminal(currentTerminalId.value)
    } else {
      currentTerminalId.value = null
    }
  }
}

// 设置终端右键菜单和复制粘贴功能
const setupTerminalContextMenu = (terminal, containerEl, terminalId) => {
  let contextMenu = null
  
  // 创建右键菜单
  const createContextMenu = () => {
    const menu = document.createElement('div')
    menu.className = 'terminal-context-menu'
    menu.innerHTML = `
      <div class="context-menu-item" data-action="copy">
        <span>复制</span>
        <span class="shortcut">Ctrl+C</span>
      </div>
      <div class="context-menu-item" data-action="paste">
        <span>粘贴</span>
        <span class="shortcut">Ctrl+V</span>
      </div>
      <div class="context-menu-divider"></div>
      <div class="context-menu-item" data-action="selectall">
        <span>全选</span>
        <span class="shortcut">Ctrl+A</span>
      </div>
      <div class="context-menu-item" data-action="clear">
        <span>清屏</span>
        <span class="shortcut">Ctrl+L</span>
      </div>
    `
    document.body.appendChild(menu)
    return menu
  }
  
  // 显示右键菜单
  const showContextMenu = (x, y) => {
    hideContextMenu()
    contextMenu = createContextMenu()
    
    // 设置菜单位置
    contextMenu.style.left = x + 'px'
    contextMenu.style.top = y + 'px'
    
    // 确保菜单不超出屏幕边界
    const rect = contextMenu.getBoundingClientRect()
    if (rect.right > window.innerWidth) {
      contextMenu.style.left = (x - rect.width) + 'px'
    }
    if (rect.bottom > window.innerHeight) {
      contextMenu.style.top = (y - rect.height) + 'px'
    }
    
    // 更新菜单项状态
    const hasSelection = terminal.hasSelection()
    const copyItem = contextMenu.querySelector('[data-action="copy"]')
    if (copyItem) {
      copyItem.classList.toggle('disabled', !hasSelection)
    }
    
    // 添加菜单项点击事件
    contextMenu.addEventListener('click', handleContextMenuClick)
  }
  
  // 隐藏右键菜单
  const hideContextMenu = () => {
    if (contextMenu) {
      contextMenu.removeEventListener('click', handleContextMenuClick)
      document.body.removeChild(contextMenu)
      contextMenu = null
    }
  }
  
  // 处理右键菜单点击
  const handleContextMenuClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    
    const action = e.target.closest('.context-menu-item')?.dataset.action
    if (!action) return
    
    switch (action) {
      case 'copy':
        copySelectedText()
        break
      case 'paste':
        pasteFromClipboard()
        break
      case 'selectall':
        terminal.selectAll()
        break
      case 'clear':
        clearTerminal(terminalId)
        break
    }
    
    hideContextMenu()
  }
  
  // 复制选中文本
  const copySelectedText = async () => {
    const selection = terminal.getSelection()
    if (selection) {
      try {
        await navigator.clipboard.writeText(selection)
        ElMessage.success('已复制到剪贴板')
      } catch (err) {
        console.error('复制失败:', err)
        // 降级方案：使用传统方法
        const textArea = document.createElement('textarea')
        textArea.value = selection
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        ElMessage.success('已复制到剪贴板')
      }
    }
  }
  
  // 创建隐藏的粘贴输入框（降级方案）
  const createPasteInput = () => {
    const pasteInput = document.createElement('textarea')
    pasteInput.style.position = 'fixed'
    pasteInput.style.left = '-9999px'
    pasteInput.style.top = '-9999px'
    pasteInput.style.opacity = '0'
    pasteInput.style.pointerEvents = 'none'
    document.body.appendChild(pasteInput)
    return pasteInput
  }

  // 从剪贴板粘贴 - 用于右键菜单
  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (text) {
        sendTextToTerminal(text)
        ElMessage.success(`已粘贴 ${text.length} 个字符`)
      } else {
        ElMessage.warning('剪贴板为空')
      }
    } catch (err) {
      console.error('粘贴失败:', err)
      ElMessage.error('粘贴失败，请尝试使用 Ctrl+V')
    }
  }

  // 发送文本到终端
  const sendTextToTerminal = (text) => {
    const ws = websocketConnections.value.get(terminalId)
    if (ws && ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'terminal_input',
        data: text
      }
      ws.send(JSON.stringify(message))
    }
  }
  
  // 监听右键点击
  containerEl.addEventListener('contextmenu', (e) => {
    e.preventDefault()
    showContextMenu(e.clientX, e.clientY)
  })
  
  // 使用xterm.js的attachCustomKeyEventHandler来处理键盘事件
  terminal.attachCustomKeyEventHandler((e) => {
    // Ctrl+C: 如果有选中文本则复制，否则发送中断信号
    if (e.ctrlKey && e.key === 'c') {
      if (terminal.hasSelection()) {
        e.preventDefault()
        copySelectedText()
        return false // 阻止xterm.js处理这个事件
      }
      // 如果没有选中文本，返回true让xterm.js处理（发送中断信号）
      return true
    }
    
    // Ctrl+V: 粘贴 - 在用户交互上下文中直接处理
    if (e.ctrlKey && e.key === 'v' && !e.shiftKey) {
      e.preventDefault()
      
      // 直接在这个事件处理器中处理粘贴，确保在用户交互上下文中
      const handleDirectPaste = async () => {
        try {
          // 在用户交互上下文中，现代剪贴板API更容易成功
          const text = await navigator.clipboard.readText()
          if (text) {
            sendTextToTerminal(text)
            ElMessage.success(`已粘贴 ${text.length} 个字符`)
            return
          }
        } catch (err) {
          console.log('现代剪贴板API失败，使用降级方案:', err)
          
          // 降级方案：创建临时输入框
          const tempInput = document.createElement('textarea')
          tempInput.style.position = 'fixed'
          tempInput.style.left = '-9999px'
          tempInput.style.opacity = '0'
          document.body.appendChild(tempInput)
          
          tempInput.focus()
          tempInput.select()
          
          // 监听粘贴事件
          const onPaste = (pasteEvent) => {
            pasteEvent.preventDefault()
            const pastedText = pasteEvent.clipboardData?.getData('text/plain') || ''
            if (pastedText) {
              sendTextToTerminal(pastedText)
              ElMessage.success(`已粘贴 ${pastedText.length} 个字符`)
            } else {
              ElMessage.warning('剪贴板为空')
            }
            
            // 清理
            tempInput.removeEventListener('paste', onPaste)
            document.body.removeChild(tempInput)
            terminal.focus()
          }
          
          tempInput.addEventListener('paste', onPaste)
          
          // 执行粘贴命令
          const success = document.execCommand('paste')
          if (!success) {
            // 如果execCommand失败，清理并提示
            tempInput.removeEventListener('paste', onPaste)
            document.body.removeChild(tempInput)
            ElMessage.error('粘贴失败，请确保剪贴板中有内容')
          }
        }
      }
      
      handleDirectPaste()
      return false // 阻止xterm.js处理这个事件
    }
    
    // Ctrl+A: 全选
    if (e.ctrlKey && e.key === 'a') {
      e.preventDefault()
      terminal.selectAll()
      return false // 阻止xterm.js处理这个事件
    }
    
    // Ctrl+L: 清屏
    if (e.ctrlKey && e.key === 'l') {
      e.preventDefault()
      clearTerminal(terminalId)
      return false // 阻止xterm.js处理这个事件
    }
    
    // 对于其他按键，让xterm.js正常处理
    return true
  })
  
  // 点击其他地方隐藏菜单
  document.addEventListener('click', hideContextMenu)
  document.addEventListener('contextmenu', (e) => {
    if (!containerEl.contains(e.target)) {
      hideContextMenu()
    }
  })
  
  // 确保容器可以获得焦点
  containerEl.setAttribute('tabindex', '-1')
}

const initializeTerminal = (terminalId) => {
  try {
    const containerEl = terminalRefs.value.get(terminalId)
    if (!containerEl) {
      console.error('找不到终端容器元素:', terminalId)
      return
    }
    
    // 创建新的终端实例
    const terminal = new Terminal({
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
      scrollback: 3000,
      tabStopWidth: 4,
      allowTransparency: false
    })
    
    // 创建并加载插件
    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()
    
    terminal.loadAddon(fitAddon)
    terminal.loadAddon(webLinksAddon)
    
    // 将终端挂载到DOM元素
    terminal.open(containerEl)
    
    // 调整终端大小以适应容器
    setTimeout(() => {
      fitAddon.fit()
    }, 100)
    
    // 监听终端输入
    terminal.onData((data) => {
      const ws = websocketConnections.value.get(terminalId)
      if (ws && ws.readyState === WebSocket.OPEN) {
        const message = {
          type: 'terminal_input',
          data: data
        }
        ws.send(JSON.stringify(message))
      }
    })
    
    // 监听终端大小变化
    terminal.onResize(({ cols, rows }) => {
      const ws = websocketConnections.value.get(terminalId)
      if (ws && ws.readyState === WebSocket.OPEN) {
        const resizeMessage = {
          type: 'terminal_resize',
          cols: cols,
          rows: rows
        }
        ws.send(JSON.stringify(resizeMessage))
      }
    })
    
    // 添加右键菜单和复制粘贴功能
    setupTerminalContextMenu(terminal, containerEl, terminalId)
    
    // 存储终端实例
    terminalInstances.value.set(terminalId, {
      terminal,
      fitAddon,
      webLinksAddon
    })
    
    console.log('终端初始化完成:', terminalId)
  } catch (error) {
    console.error('初始化终端失败:', error)
    updateTerminalStatus(terminalId, 'error')
  }
}

const connectTerminalWebSocket = (terminalId, agentId) => {
  try {
    const wsUrl = `ws://${__WEBSOCKET_HOST__}:${__WEBSOCKET_PORT__}/terminal/${agentId}`
    console.log('连接终端WebSocket:', wsUrl)
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('终端WebSocket连接已建立:', terminalId)
      updateTerminalStatus(terminalId, 'connected')
      ElMessage.success(`终端 "${getTerminalByid(terminalId)?.hostname}" 连接成功`)
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleTerminalMessage(terminalId, data)
      } catch (error) {
        console.error('解析终端消息失败:', error)
        // 如果不是JSON，可能是二进制数据
        const instance = terminalInstances.value.get(terminalId)
        if (instance?.terminal) {
          instance.terminal.write(event.data)
        }
      }
    }
    
    ws.onclose = () => {
      console.log('终端WebSocket连接已关闭:', terminalId)
      updateTerminalStatus(terminalId, 'disconnected')
      const terminal = getTerminalByid(terminalId)
      if (terminal) {
        ElMessage.warning(`终端 "${terminal.hostname}" 连接已断开`)
      }
    }
    
    ws.onerror = (error) => {
      console.error('终端WebSocket连接错误:', error)
      updateTerminalStatus(terminalId, 'error')
      const terminal = getTerminalByid(terminalId)
      if (terminal) {
        ElMessage.error(`终端 "${terminal.hostname}" 连接失败`)
      }
    }
    
    // 存储WebSocket连接
    websocketConnections.value.set(terminalId, ws)
    
  } catch (error) {
    console.error('建立终端WebSocket连接失败:', error)
    updateTerminalStatus(terminalId, 'error')
  }
}

const handleTerminalMessage = (terminalId, data) => {
  const instance = terminalInstances.value.get(terminalId)
  if (!instance) return
  
  switch (data.type) {
    case 'terminal_ready':
      console.log('终端就绪:', data)
      updateTerminalSessionId(terminalId, data.session_id)
      
      // 发送当前终端大小
      const ws = websocketConnections.value.get(terminalId)
      if (instance.terminal && ws && ws.readyState === WebSocket.OPEN) {
        const resizeMessage = {
          type: 'terminal_resize',
          cols: instance.terminal.cols,
          rows: instance.terminal.rows
        }
        ws.send(JSON.stringify(resizeMessage))
      }
      break
      
    case 'terminal_data':
      // 将数据写入xterm.js终端
      if (instance.terminal && data.data) {
        instance.terminal.write(data.data)
      }
      break
      
    case 'terminal_error':
      console.error('终端错误:', data.error)
      if (instance.terminal) {
        instance.terminal.write(`\r\n\x1b[31m❌ ${data.error}\x1b[0m\r\n`)
      }
      const terminal = getTerminalByid(terminalId)
      if (terminal) {
        ElMessage.error(`终端 "${terminal.hostname}": ${data.error}`)
      }
      break
      
    case 'terminal_pong':
      // 心跳响应，不需要特殊处理
      break
      
    default:
      console.log('收到未知终端消息:', data)
  }
}

const reconnectTerminal = (terminalId) => {
  const terminal = getTerminalByid(terminalId)
  if (!terminal || terminal.status === 'connecting') return
  
  // 清理现有连接
  cleanupTerminal(terminalId, false) // 不从列表中移除
  
  // 更新状态为连接中
  updateTerminalStatus(terminalId, 'connecting')
  
  // 重新初始化
  setTimeout(() => {
    initializeTerminal(terminalId)
    connectTerminalWebSocket(terminalId, terminal.agentId)
  }, 1000)
}

const clearTerminal = (terminalId) => {
  const instance = terminalInstances.value.get(terminalId)
  if (instance?.terminal) {
    instance.terminal.clear()
  }
}

const toggleHelp = () => {
  showHelp.value = !showHelp.value
}

const handleGlobalResize = () => {
  // 延迟调整所有终端大小
  setTimeout(() => {
    terminalInstances.value.forEach((instance, terminalId) => {
      if (instance?.fitAddon && instance?.terminal) {
        try {
          instance.fitAddon.fit()
        } catch (error) {
          console.warn('调整终端大小失败:', terminalId, error)
        }
      }
    })
  }, 100)
}

const cleanupTerminal = (terminalId, removeFromList = true) => {
  // 清理WebSocket连接
  const ws = websocketConnections.value.get(terminalId)
  if (ws) {
    ws.close()
    websocketConnections.value.delete(terminalId)
  }
  
  // 清理终端实例
  const instance = terminalInstances.value.get(terminalId)
  if (instance?.terminal) {
    instance.terminal.dispose()
    terminalInstances.value.delete(terminalId)
  }
  
  // 清理DOM引用
  terminalRefs.value.delete(terminalId)
}

// 辅助函数
const setTerminalRef = (terminalId, el) => {
  if (el) {
    terminalRefs.value.set(terminalId, el)
  }
}

const getTerminalByid = (terminalId) => {
  return activeTerminals.value.find(t => t.id === terminalId)
}

const updateTerminalStatus = (terminalId, status) => {
  const terminal = getTerminalByid(terminalId)
  if (terminal) {
    terminal.status = status
  }
}

const updateTerminalSessionId = (terminalId, sessionId) => {
  const terminal = getTerminalByid(terminalId)
  if (terminal) {
    terminal.sessionId = sessionId
  }
}

// 状态相关方法
const getTerminalStatusType = (status) => {
  switch (status) {
    case 'connected': return 'success'
    case 'connecting': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

const getTerminalStatusText = (status) => {
  switch (status) {
    case 'connected': return '已连接'
    case 'connecting': return '连接中'
    case 'error': return '连接错误'
    case 'disconnected': return '已断开'
    default: return '未知状态'
  }
}

const getStatusTitle = (status) => {
  switch (status) {
    case 'connecting': return '正在连接终端...'
    case 'error': return '连接失败'
    case 'disconnected': return '连接已断开'
    default: return '未知状态'
  }
}

const getStatusMessage = (status) => {
  switch (status) {
    case 'connecting': return '正在建立与远程主机的安全连接，请稍候...'
    case 'error': return '无法连接到远程主机，请检查网络连接或稍后重试'
    case 'disconnected': return '与远程主机的连接已断开，可以尝试重新连接'
    default: return ''
  }
}
</script>

<style scoped>
/* 确保页面不滚动，完全填充视口 */
.terminal-page {
  height: 100vh;
  width: 100vw;
  display: flex;
  background: #f0f2f5;
  overflow: hidden;
  position: fixed;
  top: 0;
  left: 0;
  margin: 0;
  padding: 0;
}

/* 左侧Agent列表 */
.agent-sidebar {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e8e9eb;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e8e9eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fafafa;
  flex-shrink: 0;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 搜索容器 */
.search-container {
  padding: 12px;
  border-bottom: 1px solid #e8e9eb;
  background: #fff;
  flex-shrink: 0;
}

.agent-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.agent-item {
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.agent-item:hover {
  background: #f5f7fa;
  border-color: #c6e2ff;
}

.agent-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}

.agent-item.online {
  border-left: 3px solid #67c23a;
}

.agent-item:not(.online) {
  border-left: 3px solid #f56c6c;
  opacity: 0.6;
}

.agent-info {
  margin-bottom: 8px;
}

.agent-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.agent-ip {
  font-size: 12px;
  color: #909399;
}

.agent-status {
  text-align: right;
}

.no-results {
  padding: 20px;
  text-align: center;
}

/* 右侧终端区域 */
.terminal-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  overflow: hidden;
  min-width: 0; /* 防止flex子元素溢出 */
}

.empty-terminal {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}

.terminal-tabs-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0; /* 重要：允许子元素收缩 */
}

/* 终端标签页 */
.terminal-tabs {
  display: flex;
  background: #2d2d30;
  border-bottom: 1px solid #3e3e42;
  overflow-x: auto;
  flex-shrink: 0;
  min-height: 40px;
}

.terminal-tab {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  min-width: 200px;
  background: #252526;
  border-right: 1px solid #3e3e42;
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;
}

.terminal-tab:hover {
  background: #2d2d30;
}

.terminal-tab.active {
  background: #1e1e1e;
  border-bottom: 2px solid #00d4aa;
}

.tab-title {
  flex: 1;
  color: #cccccc;
  font-size: 14px;
  margin-right: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-status {
  margin-right: 8px;
}

.close-btn {
  color: #909399 !important;
  padding: 2px !important;
  min-height: auto !important;
  width: 20px !important;
  height: 20px !important;
}

.close-btn:hover {
  color: #f56c6c !important;
  background: rgba(245, 108, 108, 0.1) !important;
}

/* 终端内容区域 */
.terminal-content {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0; /* 重要：允许子元素收缩 */
}

.terminal-panel {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 终端工具栏 */
.terminal-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #2d2d30;
  border-bottom: 1px solid #3e3e42;
  flex-shrink: 0;
  min-height: 48px;
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.terminal-info {
  color: #cccccc;
  font-size: 14px;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

/* 帮助面板 */
.help-panel {
  background: #252526;
  border-bottom: 1px solid #3e3e42;
  flex-shrink: 0;
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
  color: #cccccc;
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

/* 连接状态提示 */
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

/* 终端容器 - 关键修复 */
.terminal-container {
  flex: 1;
  background: #1e1e1e;
  overflow: hidden;
  min-height: 0; /* 重要：允许容器收缩 */
  position: relative;
}

/* xterm.js样式覆盖 - 确保全屏显示 */
:deep(.xterm) {
  height: 100% !important;
  width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
}

:deep(.xterm-viewport) {
  background: #1e1e1e !important;
  height: 100% !important;
  width: 100% !important;
}

:deep(.xterm-screen) {
  background: #1e1e1e !important;
  height: 100% !important;
  width: 100% !important;
}

:deep(.xterm-helper-textarea) {
  position: absolute !important;
  left: -9999px !important;
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

.agent-list::-webkit-scrollbar {
  width: 6px;
}

.agent-list::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.agent-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.agent-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.terminal-tabs::-webkit-scrollbar {
  height: 4px;
}

.terminal-tabs::-webkit-scrollbar-track {
  background: #2d2d30;
}

.terminal-tabs::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 2px;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .agent-sidebar {
    width: 200px;
  }
  
  .terminal-tab {
    min-width: 160px;
  }
}

@media (max-width: 768px) {
  .terminal-page {
    flex-direction: column;
  }
  
  .agent-sidebar {
    width: 100%;
    height: 200px;
    flex-shrink: 0;
  }
  
  .help-content {
    grid-template-columns: 1fr;
  }
  
  .terminal-toolbar {
    flex-direction: column;
    gap: 8px;
    padding: 8px;
  }
  
  .toolbar-left,
  .toolbar-right {
    width: 100%;
    justify-content: center;
  }
}

/* 终端右键菜单样式 */
:global(.terminal-context-menu) {
  position: fixed;
  background: #2d2d30;
  border: 1px solid #3e3e42;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  padding: 4px 0;
  min-width: 160px;
  z-index: 10000;
  font-size: 13px;
  color: #cccccc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

:global(.context-menu-item) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

:global(.context-menu-item:hover) {
  background: #094771;
}

:global(.context-menu-item.disabled) {
  color: #6c6c6c;
  cursor: not-allowed;
}

:global(.context-menu-item.disabled:hover) {
  background: transparent;
}

:global(.context-menu-divider) {
  height: 1px;
  background: #3e3e42;
  margin: 4px 0;
}

:global(.shortcut) {
  font-size: 11px;
  color: #888888;
  margin-left: 16px;
}
</style>
