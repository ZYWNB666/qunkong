import React, { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Space, message, Modal, Descriptions, Row, Col, Statistic } from 'antd'
import { ReloadOutlined, DeleteOutlined, DesktopOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { agentApi } from '../utils/api'
import { usePermissions, PermissionGate } from '../hooks/usePermissions'

const AgentManagement = () => {
  const [loading, setLoading] = useState(false)
  const [agents, setAgents] = useState([])
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const { hasPermission } = usePermissions()

  useEffect(() => {
    loadAgents()
  }, [])

  const loadAgents = async () => {
    try {
      setLoading(true)
      // API拦截器会自动添加project_id参数
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
      content: '确定要清理所有离线状态的 Agent 吗？此操作不可恢复！',
      onOk: async () => {
        try {
          await agentApi.cleanupOfflineAgents(0)
          message.success('清理完成')
          loadAgents()
        } catch (error) {
          message.error('清理失败')
        }
      }
    })
  }

  const loadAgentDetails = async (agentId) => {
    try {
      setDetailLoading(true)
      const details = await agentApi.getAgentDetails(agentId)
      console.log('Agent详情数据:', details) // 调试日志
      // 完整更新agent信息，确保包括last_heartbeat和disk_info
      setSelectedAgent(prev => {
        // 保留agent的id，其他字段全部用details覆盖
        const updated = {
          id: prev?.id || agentId,
          ...details
        }
        console.log('更新后的selectedAgent:', updated) // 调试日志
        return updated
      })
    } catch (error) {
      message.error('获取详细信息失败')
      console.error('获取详情失败:', error)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleViewDetails = async (agent) => {
    setDetailVisible(true)
    setSelectedAgent(agent)
    await loadAgentDetails(agent.id)
  }

  // 详情页面自动刷新
  useEffect(() => {
    let refreshTimer = null
    
    if (detailVisible && selectedAgent?.id) {
      // 每3秒刷新一次详情数据
      refreshTimer = setInterval(() => {
        loadAgentDetails(selectedAgent.id)
      }, 3000)
    }
    
    return () => {
      if (refreshTimer) {
        clearInterval(refreshTimer)
      }
    }
  }, [detailVisible, selectedAgent?.id])

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const columns = [
    {
      title: '主机名',
      dataIndex: 'hostname',
      key: 'hostname',
      width: 180
    },
    {
      title: '内网IP',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140
    },
    {
      title: '公网IP',
      dataIndex: 'external_ip',
      key: 'external_ip',
      width: 140,
      render: (external_ip) => external_ip || '-'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: status => {
        const isOnline = status === 'online' || status === 'ONLINE' || status === 'connected'
        return (
          <Tag color={isOnline ? 'success' : 'error'}>
            {isOnline ? '在线' : '离线'}
          </Tag>
        )
      }
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 150,
      render: (tags) => (
        <>
          {tags && tags.length > 0 ? (
            tags.map((tag, index) => (
              <Tag color="blue" key={index} style={{ marginBottom: 4 }}>
                {tag}
              </Tag>
            ))
          ) : (
            '-'
          )}
        </>
      )
    },
    {
      title: '租户ID',
      dataIndex: 'tenant_id',
      key: 'tenant_id',
      width: 100,
      render: (tenant_id) => tenant_id || '-'
    },
    {
      title: '项目ID',
      dataIndex: 'project_id',
      key: 'project_id',
      width: 100,
      render: (project_id) => project_id || '-'
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
      width: 280,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<InfoCircleOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            详情
          </Button>
          
          <PermissionGate permission="agent.restart">
            <Button
              type="link"
              size="small"
              onClick={() => handleRestart(record.id)}
            >
              重启
            </Button>
          </PermissionGate>
          
          <PermissionGate permission="terminal.access">
            <Button
              type="link"
              size="small"
              icon={<DesktopOutlined />}
              onClick={() => window.open(`/terminal/${record.id}`, '_blank')}
            >
              终端
            </Button>
          </PermissionGate>
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
            <PermissionGate permission="agent.delete">
              <Button
                icon={<DeleteOutlined />}
                onClick={handleCleanup}
              >
                清理离线
              </Button>
            </PermissionGate>
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

      {/* Agent详情弹窗 */}
      <Modal
        title="Agent 详细信息"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>
        ]}
        width={900}
      >
        {selectedAgent && (
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            {/* 基本信息 */}
            <Card size="small" title="基本信息" style={{ marginBottom: 16 }}>
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Agent ID">{selectedAgent.id}</Descriptions.Item>
                <Descriptions.Item label="主机名">{selectedAgent.hostname}</Descriptions.Item>
                <Descriptions.Item label="内网IP">{selectedAgent.ip_address}</Descriptions.Item>
                <Descriptions.Item label="外网IP">{selectedAgent.external_ip || '未知'}</Descriptions.Item>
                <Descriptions.Item label="操作系统">
                  {selectedAgent.system_info?.os || selectedAgent.os_type || 'Unknown'}
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={selectedAgent.status === 'online' || selectedAgent.status === 'ONLINE' || selectedAgent.status === 'connected' ? 'success' : 'error'}>
                    {selectedAgent.status === 'online' || selectedAgent.status === 'ONLINE' || selectedAgent.status === 'connected' ? '在线' : '离线'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="注册时间">{selectedAgent.register_time || '-'}</Descriptions.Item>
                <Descriptions.Item label="最后心跳">{selectedAgent.last_heartbeat || '无数据'}</Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 系统信息 */}
            {selectedAgent.system_info && (
              <>
                <Card size="small" title="系统资源" style={{ marginBottom: 16 }} loading={detailLoading}>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title="CPU核心数"
                        value={selectedAgent.cpu_info?.cpu_count || selectedAgent.system_info?.cpu_count || 0}
                        suffix="核"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="CPU使用率"
                        value={selectedAgent.cpu_info?.cpu_percent || selectedAgent.system_info?.cpu_usage || 0}
                        suffix="%"
                        precision={1}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="内存使用率"
                        value={selectedAgent.memory_info?.percent || selectedAgent.system_info?.memory_usage || 0}
                        suffix="%"
                        precision={1}
                      />
                    </Col>
                  </Row>
                  <Row gutter={16} style={{ marginTop: 16 }}>
                    <Col span={8}>
                      <Statistic
                        title="总内存"
                        value={formatBytes(selectedAgent.memory_info?.total || 0)}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="已用内存"
                        value={formatBytes(selectedAgent.memory_info?.used || 0)}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="可用内存"
                        value={formatBytes(selectedAgent.memory_info?.available || selectedAgent.memory_info?.free || 0)}
                      />
                    </Col>
                  </Row>
                </Card>

                <Card size="small" title="操作系统详情" style={{ marginBottom: 16 }} loading={detailLoading}>
                  <Descriptions bordered column={2} size="small">
                    <Descriptions.Item label="操作系统">
                      {selectedAgent.system_info?.os || 'Unknown'}
                    </Descriptions.Item>
                    <Descriptions.Item label="内核版本">
                      {selectedAgent.system_info?.kernel || 'Unknown'}
                    </Descriptions.Item>
                    <Descriptions.Item label="系统架构">
                      {selectedAgent.system_info?.architecture || 'Unknown'}
                    </Descriptions.Item>
                    <Descriptions.Item label="运行时间">
                      {selectedAgent.system_info?.uptime || 'Unknown'}
                    </Descriptions.Item>
                    <Descriptions.Item label="系统负载">
                      {selectedAgent.system_info?.load_average || 'Unknown'}
                    </Descriptions.Item>
                    <Descriptions.Item label="CPU型号" span={2}>
                      {selectedAgent.system_info?.cpu || selectedAgent.cpu_info?.model || 'Unknown CPU'}
                    </Descriptions.Item>
                  </Descriptions>
                </Card>

                {/* 磁盘信息 */}
                {selectedAgent.disk_info && selectedAgent.disk_info.length > 0 && (
                  <Card size="small" title="磁盘信息" loading={detailLoading}>
                    <Table
                      dataSource={selectedAgent.disk_info}
                      columns={[
                        { title: '设备', dataIndex: 'device', key: 'device' },
                        { title: '挂载点', dataIndex: 'mountpoint', key: 'mountpoint' },
                        { title: '文件系统', dataIndex: 'fstype', key: 'fstype' },
                        {
                          title: '总容量',
                          dataIndex: 'total',
                          key: 'total',
                          render: (val) => formatBytes(val)
                        },
                        {
                          title: '已用',
                          dataIndex: 'used',
                          key: 'used',
                          render: (val) => formatBytes(val)
                        },
                        {
                          title: '可用',
                          dataIndex: 'free',
                          key: 'free',
                          render: (val) => formatBytes(val)
                        },
                        {
                          title: '使用率',
                          dataIndex: 'percent',
                          key: 'percent',
                          render: (val) => `${val}%`
                        }
                      ]}
                      size="small"
                      pagination={false}
                      rowKey="device"
                    />
                  </Card>
                )}
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default AgentManagement

