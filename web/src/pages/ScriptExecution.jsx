import React, { useState, useEffect } from 'react'
import { Card, Button, Select, Input, Spin, message, Table, Tag, Space } from 'antd'
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { scriptApi, agentApi } from '../utils/api'

const ScriptExecution = () => {
  const [loading, setLoading] = useState(false)
  const [agents, setAgents] = useState([])
  const [selectedAgents, setSelectedAgents] = useState([])
  const [scriptContent, setScriptContent] = useState('#!/bin/bash\n\necho "Hello World"\n')
  const [scriptType, setScriptType] = useState('shell')
  const [executing, setExecuting] = useState(false)
  const [tasks, setTasks] = useState([])

  useEffect(() => {
    loadAgents()
    loadTasks()
  }, [])

  const loadAgents = async () => {
    try {
      setLoading(true)
      const response = await agentApi.getAgents()
      setAgents(response.agents || [])
    } catch (error) {
      message.error('加载 Agent 列表失败')
    } finally {
      setLoading(false)
    }
  }

  const loadTasks = async () => {
    try {
      const response = await scriptApi.getTasks()
      setTasks(response.tasks || [])
    } catch (error) {
      console.error('加载任务列表失败:', error)
    }
  }

  const handleExecute = async () => {
    if (!selectedAgents.length) {
      message.warning('请选择至少一个 Agent')
      return
    }

    if (!scriptContent.trim()) {
      message.warning('请输入脚本内容')
      return
    }

    try {
      setExecuting(true)
      await scriptApi.executeScript({
        target_hosts: selectedAgents,  // 后端期望的参数名
        script: scriptContent,          // 后端期望的参数名
        script_name: `脚本执行-${new Date().toLocaleString()}`,
        script_params: '',
        timeout: 3600,
        execution_user: 'root'
      })
      message.success('脚本执行任务已创建')
      setSelectedAgents([])  // 清空选择
      loadTasks()
    } catch (error) {
      message.error(error.response?.data?.error || '脚本执行失败')
    } finally {
      setExecuting(false)
    }
  }

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 280
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: status => {
        const colors = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error'
        }
        return <Tag color={colors[status]}>{status}</Tag>
      }
    },
    {
      title: 'Agent 数量',
      dataIndex: 'agent_count',
      key: 'agent_count',
      width: 120
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card title="脚本执行" extra={
        <Button icon={<ReloadOutlined />} onClick={loadTasks}>
          刷新
        </Button>
      }>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <div style={{ marginBottom: 8 }}>选择 Agent:</div>
            <Select
              mode="multiple"
              style={{ width: '100%' }}
              placeholder="请选择要执行脚本的 Agent"
              value={selectedAgents}
              onChange={setSelectedAgents}
              loading={loading}
              options={agents.map(agent => ({
                label: `${agent.hostname} (${agent.ip_address})`,
                value: agent.id
              }))}
            />
          </div>

          <div>
            <div style={{ marginBottom: 8 }}>脚本类型:</div>
            <Select
              style={{ width: 200 }}
              value={scriptType}
              onChange={setScriptType}
              options={[
                { label: 'Shell', value: 'shell' },
                { label: 'Python', value: 'python' },
                { label: 'PowerShell', value: 'powershell' }
              ]}
            />
          </div>

          <div>
            <div style={{ marginBottom: 8 }}>脚本内容:</div>
            <div style={{ border: '1px solid #d9d9d9', borderRadius: 4 }}>
              <Editor
                height="300px"
                language={scriptType === 'powershell' ? 'powershell' : scriptType}
                value={scriptContent}
                onChange={value => setScriptContent(value)}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14
                }}
              />
            </div>
          </div>

          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            size="large"
            onClick={handleExecute}
            loading={executing}
          >
            执行脚本
          </Button>
        </Space>
      </Card>

      <Card title="最近任务" style={{ marginTop: 24 }}>
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="task_id"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  )
}

export default ScriptExecution

