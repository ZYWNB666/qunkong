import React, { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Tag, message } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { tenantsApi } from '../utils/api'

const TenantManagement = () => {
  const [loading, setLoading] = useState(false)
  const [tenants, setTenants] = useState([])

  useEffect(() => {
    loadTenants()
  }, [])

  const loadTenants = async () => {
    try {
      setLoading(true)
      const response = await tenantsApi.getTenants()
      setTenants(response.tenants || [])
    } catch (error) {
      message.error('加载租户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '租户名称',
      dataIndex: 'tenant_name',
      key: 'tenant_name',
      width: 200
    },
    {
      title: '租户代码',
      dataIndex: 'tenant_code',
      key: 'tenant_code',
      width: 150
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: status => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '激活' : '禁用'}
        </Tag>
      )
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
      <Card
        title="租户管理"
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />}>
              创建租户
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadTenants}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={tenants}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  )
}

export default TenantManagement

