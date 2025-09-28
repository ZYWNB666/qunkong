<template>
  <div class="script-execution">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">执行脚本</h2>
    </div>

    <!-- 主要内容区域 -->
    <div class="content-wrapper">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        class="script-form"
      >
        <!-- 脚本名称 -->
        <el-form-item prop="script_name" required>
          <template #label>
            <span class="form-label">脚本名称</span>
            <span class="required-star">*</span>
          </template>
          <div class="form-item-content">
            <el-input
              v-model="form.script_name"
              placeholder="取一个便于记忆的任务名，方便后续在历史记录中快速定位..."
              maxlength="60"
              show-word-limit
              class="form-input"
            />
          </div>
        </el-form-item>

        <!-- 脚本来源 -->
        <el-form-item prop="script_source" required>
          <template #label>
            <span class="form-label">脚本来源</span>
            <span class="required-star">*</span>
          </template>
          <div class="form-item-content">
            <el-radio-group v-model="form.script_source" class="radio-group">
              <el-radio value="manual">手工录入</el-radio>
              <el-radio value="reference">脚本引用</el-radio>
            </el-radio-group>
          </div>
        </el-form-item>

        <!-- 脚本内容 -->
        <el-form-item prop="script" required>
          <template #label>
            <span class="form-label">脚本内容</span>
            <span class="required-star">*</span>
          </template>
          <div class="form-item-content">
            <!-- 脚本类型选择和主题切换 -->
            <div class="editor-header">
              <div class="script-type-tabs">
                <div 
                  class="script-tab"
                  :class="{ active: form.script_type === 'shell' }"
                  @click="setScriptType('shell')"
                >
                  Shell
                </div>
                <div 
                  class="script-tab"
                  :class="{ active: form.script_type === 'python' }"
                  @click="setScriptType('python')"
                >
                  Python
                </div>
              </div>
              <div class="editor-controls">
                <el-button-group size="small">
                  <el-button 
                    :type="editorTheme === 'vs' ? 'primary' : ''"
                    @click="setEditorTheme('vs')"
                    size="small"
                  >
                    浅色
                  </el-button>
                  <el-button 
                    :type="editorTheme === 'vs-dark' ? 'primary' : ''"
                    @click="setEditorTheme('vs-dark')"
                    size="small"
                  >
                    深色
                  </el-button>
                </el-button-group>
              </div>
            </div>
            
            <!-- 代码编辑器 -->
            <div class="code-editor-container">
              <VueMonacoEditor
                v-model:value="form.script"
                :language="form.script_type === 'shell' ? 'shell' : 'python'"
                :theme="editorTheme"
                height="400px"
                :options="editorOptions"
                @mount="handleEditorMount"
              />
            </div>
            
          </div>
        </el-form-item>

        <!-- 脚本参数 -->
        <el-form-item>
          <template #label>
            <span class="form-label">脚本参数</span>
          </template>
          <div class="form-item-content">
            <el-input
              v-model="form.script_params"
              placeholder="脚本执行时传入的参数，同脚本在终端执行时的传参格式，如：./test.sh xxxx xxx xxx"
              maxlength="5000"
              show-word-limit
              class="form-input"
            />
          </div>
        </el-form-item>

        <!-- 超时时长 -->
        <el-form-item>
          <template #label>
            <span class="form-label">超时时长</span>
          </template>
          <div class="form-item-content">
            <div class="timeout-input">
              <el-input-number
                v-model="form.timeout"
                :min="1"
                :max="86400"
                controls-position="right"
                placeholder="请输入"
              />
              <span class="unit">s</span>
            </div>
          </div>
        </el-form-item>

        <!-- 执行账号 -->
        <el-form-item prop="execution_user" required>
          <template #label>
            <span class="form-label">执行账号</span>
            <span class="required-star">*</span>
          </template>
          <div class="form-item-content">
            <el-select v-model="form.execution_user" placeholder="请选择执行账号" class="form-select">
              <el-option label="root" value="root" />
              <el-option label="admin" value="admin" />
              <el-option label="ubuntu" value="ubuntu" />
            </el-select>
          </div>
        </el-form-item>

        <!-- 目标服务器 -->
        <el-form-item prop="target_hosts" required>
          <template #label>
            <span class="form-label">目标服务器</span>
            <span class="required-star">*</span>
          </template>
          <div class="form-item-content">
            <div class="server-selection">
              <el-button type="primary" @click="showServerDialog = true" class="add-server-btn">
                <el-icon><Plus /></el-icon>
                添加服务器
              </el-button>
              <div v-if="selectedServers.length > 0" class="selected-servers">
                <el-tag
                  v-for="server in selectedServers"
                  :key="server.id"
                  closable
                  @close="removeServer(server)"
                  class="server-tag"
                >
                  {{ server.hostname }} ({{ server.ip }})
                </el-tag>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <el-button type="primary" @click="executeScript" :loading="executing" size="large">
          执行
        </el-button>
        <el-button @click="resetForm" size="large">
          重置
        </el-button>
      </div>
    </div>

    <!-- 服务器选择对话框 -->
    <el-dialog
      v-model="showServerDialog"
      title="选择目标服务器"
      width="800px"
      :close-on-click-modal="false"
    >
      <div class="server-dialog">
        <div class="server-search">
          <el-input
            v-model="serverSearchKeyword"
            placeholder="搜索主机名或IP地址..."
            @input="filterServers"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <el-table
          :data="filteredServers"
          @selection-change="handleServerSelection"
          max-height="400"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="hostname" label="主机名" />
          <el-table-column prop="ip" label="IP地址" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="getServerStatusType(row.status)" size="small">
                {{ getServerStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="last_heartbeat" label="最后心跳">
            <template #default="{ row }">
              {{ formatDateTime(row.last_heartbeat) }}
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="showServerDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmServerSelection">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { scriptApi, agentApi } from '../api'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

export default {
  name: 'ScriptExecution',
  components: {
    VueMonacoEditor
  },
  setup() {
    const router = useRouter()
    const formRef = ref()
    const executing = ref(false)
    const showServerDialog = ref(false)
    const serverSearchKeyword = ref('')
    const servers = ref([])
    const selectedServers = ref([])
    const tempSelectedServers = ref([])
    const editorTheme = ref('vs-dark')

    const generateDefaultScriptName = () => {
      const now = new Date()
      const year = now.getFullYear()
      const month = String(now.getMonth() + 1).padStart(2, '0')
      const day = String(now.getDate()).padStart(2, '0')
      const hour = String(now.getHours()).padStart(2, '0')
      const minute = String(now.getMinutes()).padStart(2, '0')
      const second = String(now.getSeconds()).padStart(2, '0')
      return `${year}年${month}月${day}日${hour}:${minute}:${second}_JOBS`
    }

    const form = reactive({
      script_name: generateDefaultScriptName(),
      script_source: 'manual',
      script_type: 'shell',
      script: '',
      script_params: '',
      timeout: 7200,
      execution_user: 'root',
      target_hosts: []
    })

    const rules = {
      script_name: [
        { required: true, message: '请输入脚本名称', trigger: 'blur' }
      ],
      script: [
        { required: true, message: '请输入脚本内容', trigger: 'blur' }
      ],
      execution_user: [
        { required: true, message: '请选择执行账号', trigger: 'change' }
      ],
      target_hosts: [
        { required: true, message: '请选择目标服务器', trigger: 'change' }
      ]
    }

    const filteredServers = computed(() => {
      if (!serverSearchKeyword.value) {
        return servers.value
      }
      return servers.value.filter(server => 
        server.hostname.toLowerCase().includes(serverSearchKeyword.value.toLowerCase()) ||
        server.ip.includes(serverSearchKeyword.value)
      )
    })

    const shellPlaceholder = String.raw`#!/bin/bash
anynowtime="date +'%Y-%m-%d %H:%M:%S'"
NOW="echo [\`$anynowtime\`][PID:$$]"

##### 可在脚本开始运行时调用，打印当时的时间戳及PID。
function job_start
{
    echo "\`eval $NOW\` job_start"
}

##### 可在脚本执行成功的逻辑分支处调用，打印当时的时间戳及PID。
function job_success
{
    MSG="$*"
    echo "\`eval $NOW\` job_success:[$MSG]"
    exit 0
}

##### 可在脚本执行失败的逻辑分支处调用，打印当时的时间戳及PID。
function job_fail
{
    MSG="$*"
    echo "\`eval $NOW\` job_fail:[$MSG]"
    exit 1
}

job_start

###### 作业平台中执行脚本成功和失败的标准只取决于脚本最后一条执行语句的返回值
###### 如果返回值为0，则认为此脚本执行成功，如果非0，则认为脚本执行失败`

    const pythonPlaceholder = String.raw`#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
from datetime import datetime

def job_start():
    """脚本开始执行"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] job_start")

def job_success(msg=""):
    """脚本执行成功"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] job_success: {msg}")
    sys.exit(0)

def job_fail(msg=""):
    """脚本执行失败"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] job_fail: {msg}")
    sys.exit(1)

if __name__ == "__main__":
    job_start()
    # 在这里编写你的Python脚本逻辑
    print("Hello, QueenBee!")
    job_success("脚本执行完成")`

    const scriptPlaceholder = computed(() => (form.script_type === 'shell' ? shellPlaceholder : pythonPlaceholder))

    // Monaco Editor 配置
    const editorOptions = {
      automaticLayout: true,
      fontSize: 14,
      fontFamily: "'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', 'Courier New', monospace",
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      wordWrap: 'on',
      lineNumbers: 'on',
      glyphMargin: false,
      folding: true,
      lineDecorationsWidth: 10,
      lineNumbersMinChars: 3,
      renderLineHighlight: 'line',
      selectOnLineNumbers: true,
      roundedSelection: false,
      readOnly: false,
      cursorStyle: 'line',
      cursorBlinking: 'blink',
      renderWhitespace: 'selection',
      renderControlCharacters: false,
      fontLigatures: true,
      suggestOnTriggerCharacters: true,
      acceptSuggestionOnEnter: 'on',
      tabCompletion: 'on',
      wordBasedSuggestions: true,
      parameterHints: { enabled: true },
      autoIndent: 'full',
      formatOnPaste: true,
      formatOnType: true,
      dragAndDrop: true,
      links: true,
      colorDecorators: true,
      contextmenu: true,
      mouseWheelZoom: true,
      multiCursorModifier: 'ctrlCmd',
      accessibilitySupport: 'auto'
    }

    const handleEditorMount = (editor) => {
      // 编辑器挂载后的回调
      console.log('Monaco Editor mounted:', editor)
    }

    const getLineCount = () => {
      return Math.max(form.script.split('\n').length, 30)
    }

    const loadServers = async () => {
      try {
        const data = await agentApi.getServers()
        // 处理服务器数据，确保状态字段正确（与Agent管理页面保持一致）
        servers.value = data.map(server => ({
          ...server,
          // 基于心跳时间判断服务器是否在线
          status: isServerOnline(server.last_heartbeat) ? 'ONLINE' : 'OFFLINE'
        }))
      } catch (error) {
        ElMessage.error('加载服务器列表失败')
      }
    }

    const isServerOnline = (lastHeartbeat) => {
      if (!lastHeartbeat) {
        return false
      }
      
      const now = new Date().getTime()
      const heartbeatTime = new Date(lastHeartbeat).getTime()
      const diffMinutes = (now - heartbeatTime) / (1000 * 60)
      
      // 如果心跳时间超过15秒，认为离线
      return diffMinutes <= 0.25  // 15秒 = 0.25分钟
    }

    const filterServers = () => {
      // 搜索逻辑在computed中处理
    }

    const handleServerSelection = (selection) => {
      tempSelectedServers.value = selection
    }

    const confirmServerSelection = () => {
      selectedServers.value = [...tempSelectedServers.value]
      form.target_hosts = selectedServers.value.map(server => server.id)
      showServerDialog.value = false
    }

    const removeServer = (server) => {
      const index = selectedServers.value.findIndex(s => s.id === server.id)
      if (index > -1) {
        selectedServers.value.splice(index, 1)
        form.target_hosts = selectedServers.value.map(s => s.id)
      }
    }


    const setScriptType = (type) => {
      if (form.script_type !== type) {
        form.script_type = type
        // 如果当前脚本内容为空或者是默认模板，则替换为新类型的模板
        if (!form.script.trim() || form.script === shellPlaceholder || form.script === pythonPlaceholder) {
          form.script = type === 'shell' ? shellPlaceholder : pythonPlaceholder
        }
      }
    }

    const setEditorTheme = (theme) => {
      editorTheme.value = theme
    }

    const getServerStatusType = (status) => {
      return status === 'ONLINE' ? 'success' : 'danger'
    }

    const getServerStatusText = (status) => {
      return status === 'ONLINE' ? 'online' : 'down'
    }

    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-'
      return new Date(dateTime).toLocaleString('zh-CN')
    }

    const executeScript = async () => {
      if (!formRef.value) return
      
      try {
        await formRef.value.validate()
        executing.value = true

        // 如果脚本名称为空，使用默认名称
        const scriptName = form.script_name.trim() || generateDefaultScriptName()

        const data = {
          script_name: scriptName,
          script: form.script,
          script_params: form.script_params,
          target_hosts: form.target_hosts,
          timeout: form.timeout,
          execution_user: form.execution_user
        }

        await scriptApi.executeScript(data)
        ElMessage.success('脚本执行任务已提交')
        
        router.push('/execution-history')
      } catch (error) {
        ElMessage.error('执行脚本失败: ' + (error.message || '未知错误'))
      } finally {
        executing.value = false
      }
    }

    const resetForm = () => {
      if (formRef.value) {
        formRef.value.resetFields()
      }
      selectedServers.value = []
      form.script = scriptPlaceholder.value
      form.script_name = generateDefaultScriptName() // 重置时也生成新的默认名称
    }

    onMounted(() => {
      loadServers()
      form.script = scriptPlaceholder.value
    })

    return {
      formRef,
      form,
      rules,
      executing,
      showServerDialog,
      serverSearchKeyword,
      servers,
      selectedServers,
      filteredServers,
      scriptPlaceholder,
      editorOptions,
      editorTheme,
      handleEditorMount,
      getLineCount,
      filterServers,
      handleServerSelection,
      confirmServerSelection,
      removeServer,
      executeScript,
      resetForm,
      setScriptType,
      setEditorTheme,
      getServerStatusType,
      getServerStatusText,
      formatDateTime,
      generateDefaultScriptName
    }
  }
}
</script>

<style scoped>
.script-execution {
  height: 100%;
  background: #fff;
}

.page-header {
  padding: 24px 24px 0 24px;
  border-bottom: 1px solid #e8e8e8;
  background: #fff;
}

.page-title {
  font-size: 20px;
  font-weight: 500;
  color: #262626;
  margin: 0 0 24px 0;
}

.content-wrapper {
  padding: 24px;
  background: #fff;
}

.script-form {
  max-width: none;
}

.script-form .el-form-item {
  margin-bottom: 24px;
}

.form-label {
  font-size: 14px;
  color: #262626;
  font-weight: 500;
}

.required-star {
  color: #ff4d4f;
  margin-left: 4px;
}

.form-item-content {
  width: 100%;
}

.form-input {
  width: 100%;
  max-width: 600px;
}

.form-select {
  width: 200px;
}

.radio-group {
  display: flex;
  gap: 24px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1px;
}

.script-type-tabs {
  display: flex;
}

.editor-controls {
  display: flex;
  align-items: center;
}

.script-tab {
  padding: 8px 16px;
  background: #fafafa;
  border: 1px solid #d9d9d9;
  border-bottom: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.3s;
}

.script-tab:first-child {
  border-top-left-radius: 6px;
}

.script-tab:last-child {
  border-top-right-radius: 6px;
  border-left: none;
}

.script-tab.active {
  background: #fff;
  color: #1890ff;
  border-color: #1890ff;
  border-bottom: 1px solid #fff;
  position: relative;
  z-index: 1;
}

.code-editor-container {
  border: 1px solid #d9d9d9;
  border-radius: 0 6px 6px 6px;
  background: #fff;
  overflow: hidden;
}


.timeout-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeout-input .el-input-number {
  width: 200px;
}

.unit {
  color: #666;
  font-size: 14px;
}

.server-selection {
  width: 100%;
}

.add-server-btn {
  margin-bottom: 12px;
}

.selected-servers {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.server-tag {
  margin: 0;
}

.form-actions {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e8e8e8;
  text-align: left;
}

.form-actions .el-button {
  margin-right: 16px;
  min-width: 80px;
}

.server-dialog {
  max-height: 500px;
}

.server-search {
  margin-bottom: 16px;
}

.server-search .el-input {
  width: 100%;
}
</style>