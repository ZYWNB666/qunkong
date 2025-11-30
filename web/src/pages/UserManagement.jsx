import React, { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, message, Divider, Switch } from 'antd'
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, ProjectOutlined } from '@ant-design/icons'
import { usersApi, projectsApi } from '../utils/api'

const UserManagement = () => {
  const [loading, setLoading] = useState(false)
  const [users, setUsers] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form] = Form.useForm()
  const [allProjects, setAllProjects] = useState([])
  const [loadingProjects, setLoadingProjects] = useState(false)

  useEffect(() => {
    loadUsers()
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoadingProjects(true)
      const response = await projectsApi.getProjects({ page: 1, page_size: 100 })
      setAllProjects(response.projects || [])
    } catch (error) {
      console.error('加载项目列表失败:', error)
    } finally {
      setLoadingProjects(false)
    }
  }

  const loadUsers = async () => {
    try {
      setLoading(true)
      const response = await usersApi.getUsers({ page: 1, page_size: 100 })
      setUsers(response.users || [])
    } catch (error) {
      console.error('加载用户列表失败:', error)
      message.error('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleUserStatus = async (userId, isActive) => {
    try {
      await usersApi.updateUser(userId, { is_active: isActive })
      message.success(`用户已${isActive ? '激活' : '禁用'}`)
      loadUsers()
    } catch (error) {
      message.error('状态更新失败')
      loadUsers() // 刷新列表以恢复原状态
    }
  }

  const handleCreate = () => {
    setEditingUser(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = async (user) => {
    setEditingUser(user)
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      role: user.role
    })
    
    // 加载用户的项目分配
    try {
      const response = await projectsApi.getMyProjects()
      const userProjects = (response.projects || [])
        .filter(p => p.members && p.members.some(m => m.user_id === user.id))
        .map(p => {
          const member = p.members.find(m => m.user_id === user.id)
          return {
            project_id: p.id,
            role: member.role
          }
        })
      
      form.setFieldsValue({
        username: user.username,
        email: user.email,
        role: user.role,
        project_roles: userProjects
      })
    } catch (error) {
      console.error('加载用户项目失败:', error)
    }
    
    setModalVisible(true)
  }

  const handleDelete = (userId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该用户吗？',
      onOk: async () => {
        try {
          await usersApi.deleteUser(userId)
          message.success('删除成功')
          loadUsers()
        } catch (error) {
          message.error('删除失败')
        }
      }
    })
  }

  const handleSubmit = async (values) => {
    try {
      if (editingUser) {
        await usersApi.updateUser(editingUser.id, values)
        message.success('更新成功')
      } else {
        await usersApi.createUser(values)
        message.success('创建成功')
      }
      setModalVisible(false)
      loadUsers()
    } catch (error) {
      message.error(error.response?.data?.error || '操作失败')
    }
  }

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 150
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      width: 200
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 120,
      render: role => {
        const colors = {
          super_admin: 'red',
          admin: 'orange',
          user: 'blue'
        }
        return <Tag color={colors[role]}>{role}</Tag>
      }
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (is_active, record) => (
        <Switch
          checked={is_active}
          checkedChildren="激活"
          unCheckedChildren="禁用"
          onChange={(checked) => handleToggleUserStatus(record.id, checked)}
        />
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
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
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="用户管理"
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              创建用户
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadUsers}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingUser ? '编辑用户' : '创建用户'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>

          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入正确的邮箱格式' }
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          {!editingUser && (
            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password placeholder="请输入密码（至少6位）" />
            </Form.Item>
          )}

          <Form.Item
            label="系统角色"
            name="role"
            rules={[{ required: true, message: '请选择系统角色' }]}
            tooltip="系统角色决定了用户在整个系统中的基本权限"
          >
            <Select placeholder="请选择系统角色">
              <Select.Option value="user">普通用户</Select.Option>
              <Select.Option value="admin">系统管理员</Select.Option>
            </Select>
          </Form.Item>

          <Divider orientation="left">
            <Space>
              <ProjectOutlined />
              <span>项目分配</span>
            </Space>
          </Divider>

          <Form.Item
            label="可见项目及角色"
            tooltip="为用户分配项目访问权限和项目内角色"
          >
            <Form.List name="project_roles">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item
                        {...restField}
                        name={[name, 'project_id']}
                        rules={[{ required: true, message: '请选择项目' }]}
                        style={{ marginBottom: 0, width: 250 }}
                      >
                        <Select
                          placeholder="选择项目"
                          loading={loadingProjects}
                          filterOption={(input, option) =>
                            option.children.toLowerCase().includes(input.toLowerCase())
                          }
                        >
                          {allProjects.map(project => (
                            <Select.Option key={project.id} value={project.id}>
                              {project.project_name}
                            </Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'role']}
                        rules={[{ required: true, message: '请选择角色' }]}
                        style={{ marginBottom: 0, width: 150 }}
                      >
                        <Select placeholder="项目角色">
                          <Select.Option value="admin">项目管理员</Select.Option>
                          <Select.Option value="member">项目成员</Select.Option>
                          <Select.Option value="readonly">只读成员</Select.Option>
                        </Select>
                      </Form.Item>
                      <Button type="link" danger onClick={() => remove(name)}>
                        删除
                      </Button>
                    </Space>
                  ))}
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    添加项目
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                提交
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default UserManagement

