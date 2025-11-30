import React, { useState, useEffect } from 'react'
import { Card, Button, Select, Input, Spin, message, Table, Tag, Space, Modal, Checkbox } from 'antd'
import { PlayCircleOutlined, ReloadOutlined, PlusOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { scriptApi, agentApi } from '../utils/api'
import { useNavigate } from 'react-router-dom'

const ScriptExecution = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [agents, setAgents] = useState([])
  const [selectedAgents, setSelectedAgents] = useState([])
  const [scriptContent, setScriptContent] = useState('#!/bin/bash\n\necho "Hello World"\n')
  const [scriptType, setScriptType] = useState('shell')
  const [executing, setExecuting] = useState(false)
  const [tasks, setTasks] = useState([])
  const [agentModalVisible, setAgentModalVisible] = useState(false)

  useEffect(() => {
    loadAgents()
    loadTasks()
  }, [])

  const loadAgents = async () => {
    try {
      setLoading(true)
      const response = await agentApi.getAgents()
      console.log('加载的agents数据:', response.agents)
      setAgents(response.agents || [])
    } catch (error) {
      message.error('加载 Agent 列表失败')
      console.error('加载agents错误:', error)
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
      const response = await scriptApi.executeScript({
        target_hosts: selectedAgents,
        script: scriptContent,
        script_name: `脚本执行-${new Date().toLocaleString()}`,
        script_params: '',
        timeout: 3600,
        execution_user: 'root'
      })
      
      message.success('脚本已开始执行')
      
      // 直接跳转到详情页面，带上类型参数
      if (response.task_id) {
        navigate(`/execution-detail/${response.task_id}?type=script`)
      } else {
        // 如果没有返回task_id，跳转到执行历史
        navigate('/execution-history')
      }
      
      setSelectedAgents([])
    } catch (error) {
      message.error(error.response?.data?.error || '脚本执行失败')
    } finally {
      setExecuting(false)
    }
  }

  const handleAgentModalOk = () => {
    setAgentModalVisible(false)
  }

  const handleAgentSelect = (agentId, checked) => {
    if (checked) {
      setSelectedAgents([...selectedAgents, agentId])
    } else {
      setSelectedAgents(selectedAgents.filter(id => id !== agentId))
    }
  }

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedAgents(agents.map(a => a.id))
    } else {
      setSelectedAgents([])
    }
  }

  const getSelectedAgentsText = () => {
    if (selectedAgents.length === 0) {
      return '未选择 Agent'
    }
    const selectedNames = agents
      .filter(a => selectedAgents.includes(a.id))
      .map(a => a.hostname)
      .slice(0, 3)
      .join(', ')
    
    if (selectedAgents.length > 3) {
      return `${selectedNames} 等 ${selectedAgents.length} 台主机`
    }
    return selectedNames
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
        <Button icon={<ReloadOutlined />} onClick={loadTasks} loading={loading}>
          刷新
        </Button>
      }>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <div style={{ marginBottom: 8 }}>选择 Agent:</div>
            <Space style={{ width: '100%' }}>
              <Input
                readOnly
                placeholder="请选择要执行脚本的 Agent"
                value={getSelectedAgentsText()}
                style={{ flex: 1, minWidth: 400 }}
              />
              <Button
                icon={<PlusOutlined />}
                onClick={() => setAgentModalVisible(true)}
              >
                选择 Agent ({selectedAgents.length})
              </Button>
            </Space>
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
            disabled={!selectedAgents.length || !scriptContent.trim()}
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

      {/* Agent选择弹窗 */}
      <Modal
        title="选择 Agent"
        open={agentModalVisible}
        onOk={handleAgentModalOk}
        onCancel={() => setAgentModalVisible(false)}
        width={800}
      >
        <div style={{ marginBottom: 16 }}>
          <Checkbox
            checked={selectedAgents.length === agents.length && agents.length > 0}
            indeterminate={selectedAgents.length > 0 && selectedAgents.length < agents.length}
            onChange={(e) => handleSelectAll(e.target.checked)}
          >
            全选 ({selectedAgents.length}/{agents.length})
          </Checkbox>
        </div>
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {agents.map(agent => (
            <div
              key={agent.id}
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid #f0f0f0',
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                backgroundColor: selectedAgents.includes(agent.id) ? '#f0f7ff' : 'transparent'
              }}
              onClick={() => handleAgentSelect(agent.id, !selectedAgents.includes(agent.id))}
            >
              <Checkbox
                checked={selectedAgents.includes(agent.id)}
                onChange={(e) => handleAgentSelect(agent.id, e.target.checked)}
                onClick={(e) => e.stopPropagation()}
              />
              <div style={{ marginLeft: 12, flex: 1 }}>
                <div style={{ fontWeight: 500 }}>{agent.hostname}</div>
                <div style={{ color: '#888', fontSize: 12 }}>
                  {agent.ip_address || agent.ip} • {agent.os_type || 'Unknown OS'}
                  {(agent.status === 'online' || agent.status === 'connected') && (
                    <Tag color="success" style={{ marginLeft: 8 }}>在线</Tag>
                  )}
                  {(agent.status === 'offline' || agent.status === 'disconnected' || !agent.status) && (
                    <Tag color="error" style={{ marginLeft: 8 }}>离线</Tag>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Modal>
    </div>
  )
}

export default ScriptExecution

