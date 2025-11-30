import React, { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Tag, Modal, Form, Input, message, Select, Divider, Switch } from 'antd'
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, UserOutlined } from '@ant-design/icons'
import { projectsApi, usersApi } from '../utils/api'

const ProjectManagement = () => {
  const [loading, setLoading] = useState(false)
  const [projects, setProjects] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingProject, setEditingProject] = useState(null)
  const [form] = Form.useForm()
  const [allUsers, setAllUsers] = useState([])
  const [loadingUsers, setLoadingUsers] = useState(false)

  useEffect(() => {
    loadProjects()
    loadUsers()
  }, [])

  const loadUsers = async () => {
    try {
      setLoadingUsers(true)
      const response = await usersApi.getUsers({ page: 1, page_size: 100 })
      setAllUsers(response.users || [])
    } catch (error) {
      console.error('加载用户列表失败:', error)
    } finally {
      setLoadingUsers(false)
    }
  }

  const loadProjects = async () => {
    try {
      setLoading(true)
      const response = await projectsApi.getMyProjects()
      setProjects(response.projects || [])
    } catch (error) {
      message.error('加载项目列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingProject(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = async (project) => {
    setEditingProject(project)
    
    // 加载项目成员
    try {
      const response = await projectsApi.getProjectMembers(project.id)
      const members = response.members || []
      
      const adminIds = members.filter(m => m.role === 'admin').map(m => m.user_id)
      const memberIds = members.filter(m => m.role === 'member').map(m => m.user_id)
      
      form.setFieldsValue({
        project_name: project.project_name,
        description: project.description,
        admin_ids: adminIds,
        member_ids: memberIds
      })
    } catch (error) {
      console.error('加载项目成员失败:', error)
      form.setFieldsValue({
        project_name: project.project_name,
        description: project.description
      })
    }
    
    setModalVisible(true)
  }
  
  const handleToggleProjectStatus = async (projectId, isActive) => {
    const newStatus = isActive ? 'active' : 'inactive'
    try {
      await projectsApi.updateProject(projectId, { status: newStatus })
      message.success(`项目已${isActive ? '启用' : '禁用'}`)
      loadProjects()
    } catch (error) {
      message.error('状态更新失败')
      loadProjects() // 刷新列表以恢复原状态
    }
  }

  const handleDelete = (projectId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该项目吗？',
      onOk: async () => {
        try {
          await projectsApi.deleteProject(projectId)
          message.success('删除成功')
          loadProjects()
        } catch (error) {
          message.error('删除失败')
        }
      }
    })
  }

  const handleSubmit = async (values) => {
    try {
      if (editingProject) {
        await projectsApi.updateProject(editingProject.id, values)
        message.success('更新成功')
      } else {
        await projectsApi.createProject(values)
        message.success('创建成功')
      }
      setModalVisible(false)
      loadProjects()
    } catch (error) {
      message.error(error.response?.data?.error || '操作失败')
    }
  }

  const columns = [
    {
      title: '项目名称',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 200
    },
    {
      title: '项目代码',
      dataIndex: 'project_code',
      key: 'project_code',
      width: 150
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status, record) => (
        record.role === 'admin' ? (
          <Switch
            checked={status === 'active'}
            checkedChildren="启用"
            unCheckedChildren="禁用"
            onChange={(checked) => handleToggleProjectStatus(record.id, checked)}
          />
        ) : (
          <Tag color={status === 'active' ? 'success' : 'default'}>
            {status === 'active' ? '启用' : '禁用'}
          </Tag>
        )
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description'
    },
    {
      title: '我的角色',
      dataIndex: 'role',
      key: 'role',
      width: 120,
      render: role => {
        const colors = {
          admin: 'red',
          readwrite: 'orange',
          readonly: 'blue'
        }
        const labels = {
          admin: '管理员',
          readwrite: '读写',
          readonly: '只读'
        }
        return <Tag color={colors[role]}>{labels[role]}</Tag>
      }
    },
    {
      title: '成员数',
      dataIndex: 'member_count',
      key: 'member_count',
      width: 100
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          {record.role === 'admin' && (
            <>
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              >
                编辑
              </Button>
              <Button
                type="link"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record.id)}
              >
                删除
              </Button>
            </>
          )}
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="项目管理"
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              创建项目
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadProjects}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingProject ? '编辑项目' : '创建项目'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            label="项目名称"
            name="project_name"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input maxLength={50} showCount placeholder="请输入项目名称" />
          </Form.Item>

          <Form.Item
            label="项目描述"
            name="description"
          >
            <Input.TextArea rows={3} maxLength={200} showCount placeholder="请输入项目描述（可选）" />
          </Form.Item>

          <Divider orientation="left">
            <Space>
              <UserOutlined />
              <span>成员配置</span>
            </Space>
          </Divider>

          <Form.Item
            label="项目管理员"
            name="admin_ids"
            tooltip="项目管理员拥有项目的完全控制权限"
          >
            <Select
              mode="multiple"
              placeholder={editingProject ? "选择项目管理员" : "选择项目管理员（可选，默认创建者为管理员）"}
              loading={loadingUsers}
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase())
              }
              optionFilterProp="children"
            >
              {allUsers.map(user => (
                <Select.Option key={user.id} value={user.id}>
                  {user.username} ({user.email})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="项目成员"
            name="member_ids"
            tooltip="项目成员具有基本的访问权限，可以后续调整具体权限"
          >
            <Select
              mode="multiple"
              placeholder="选择项目成员（可选）"
              loading={loadingUsers}
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase())
              }
              optionFilterProp="children"
            >
              {allUsers.map(user => (
                <Select.Option key={user.id} value={user.id}>
                  {user.username} ({user.email})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                {editingProject ? '保存' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ProjectManagement

