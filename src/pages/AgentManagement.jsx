import React, { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Space, message, Modal } from 'antd'
import { ReloadOutlined, DeleteOutlined, DesktopOutlined } from '@ant-design/icons'
import { agentApi } from '../utils/api'

const AgentManagement = () => {
  const [loading, setLoading] = useState(false)
  const [agents, setAgents] = useState([])

  useEffect(() => {
    loadAgents()
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

  const handleRestart = async (agentId) => {
    try {
      await agentApi.restartAgent(agentId)
      message.success('Agent 重启命令已发送')
      loadAgents()
    } catch (error) {
      message.error('重启失败')
    }
  }

  const handleCleanup = () => {
    Modal.confirm({
      title: '清理离线 Agent',
      content: '确定要清理超过24小时离线的 Agent 吗？',
      onOk: async () => {
        try {
          await agentApi.cleanupOfflineAgents(24)
          message.success('清理完成')
          loadAgents()
        } catch (error) {
          message.error('清理失败')
        }
      }
    })
  }

  const columns = [
    {
      title: '主机名',
      dataIndex: 'hostname',
      key: 'hostname',
      width: 200
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 150
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: status => {
        const colors = {
          ONLINE: 'success',
          OFFLINE: 'default'
        }
        const labels = {
          ONLINE: '在线',
          OFFLINE: '离线'
        }
        return <Tag color={colors[status]}>{labels[status] || status}</Tag>
      }
    },
    {
      title: '操作系统',
      dataIndex: 'os_type',
      key: 'os_type',
      width: 120
    },
    {
      title: '版本',
      dataIndex: 'agent_version',
      key: 'agent_version',
      width: 100
    },
    {
      title: '最后心跳',
      dataIndex: 'last_heartbeat',
      key: 'last_heartbeat',
      width: 180
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => handleRestart(record.id)}
          >
            重启
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DesktopOutlined />}
            onClick={() => window.open(`/terminal/${record.id}`, '_blank')}
          >
            终端
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="Agent 管理"
        extra={
          <Space>
            <Button
              icon={<DeleteOutlined />}
              onClick={handleCleanup}
            >
              清理离线
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadAgents}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={agents}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  )
}

export default AgentManagement

