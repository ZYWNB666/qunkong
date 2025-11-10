import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Empty, Tag, Space, Spin, Modal, Form, Input, Alert, message } from 'antd'
import {
  BankOutlined,
  UserOutlined,
  RightOutlined,
  PlusOutlined
} from '@ant-design/icons'
import { projectsApi } from '../utils/api'
import './ProjectSelector.css'

const ProjectSelector = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [projects, setProjects] = useState([])
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [createForm] = Form.useForm()

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const response = await projectsApi.getMyProjects()
      setProjects(response.projects)
    } catch (error) {
      message.error(error.response?.data?.error || '加载项目列表失败')
    } finally {
      setLoading(false)
    }
  }

  const selectProject = (project) => {
    localStorage.setItem('qunkong_current_project', JSON.stringify(project))
    message.success(`已进入项目：${project.project_name}`)
    navigate('/agent-management')
  }

  const handleCreateProject = async (values) => {
    try {
      setCreateLoading(true)
      const response = await projectsApi.createProject(values)
      
      message.success('项目创建成功，您已成为项目管理员')
      setCreateModalVisible(false)
      createForm.resetFields()
      
      selectProject(response.project)

    } catch (error) {
      message.error(error.response?.data?.error || '创建项目失败')
    } finally {
      setCreateLoading(false)
    }
  }

  const getRoleLabel = (role) => {
    const labels = {
      admin: '管理员',
      readwrite: '读写',
      readonly: '只读'
    }
    return labels[role] || role
  }

  const getRoleColor = (role) => {
    const colors = {
      admin: 'red',
      readwrite: 'orange',
      readonly: 'blue'
    }
    return colors[role] || 'default'
  }

  return (
    <div className="project-selector-container">
      <Card className="selector-card">
        <div className="header">
          <img src="/logo.svg" alt="Qunkong" className="logo" />
          <h1>选择项目</h1>
          <p className="subtitle">请选择一个项目开始工作</p>
        </div>

        <div className="content">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '50px' }}>
              <Spin size="large" />
            </div>
          ) : projects.length > 0 ? (
            <div className="project-list">
              {projects.map(project => (
                <Card
                  key={project.id}
                  className="project-item"
                  hoverable
                  onClick={() => selectProject(project)}
                >
                  <div className="project-content">
                    <div className="project-icon">
                      <BankOutlined style={{ fontSize: 24, color: '#fff' }} />
                    </div>
                    <div className="project-info">
                      <h3>{project.project_name}</h3>
                      <p className="project-code">{project.project_code}</p>
                      {project.description && (
                        <p className="project-desc">{project.description}</p>
                      )}
                      <Space size="middle">
                        <Tag color={getRoleColor(project.role)}>
                          {getRoleLabel(project.role)}
                        </Tag>
                        <span className="member-count">
                          <UserOutlined /> {project.member_count || 0} 成员
                        </span>
                      </Space>
                    </div>
                    <div className="project-action">
                      <RightOutlined />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Empty description="您还没有加入任何项目">
              <Button type="primary" onClick={() => setCreateModalVisible(true)}>
                创建第一个项目
              </Button>
            </Empty>
          )}
        </div>

        <div className="footer">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            size="large"
            onClick={() => setCreateModalVisible(true)}
          >
            创建新项目
          </Button>
        </div>
      </Card>

      <Modal
        title="创建项目"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={500}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateProject}
        >
          <Form.Item
            label="项目名称"
            name="project_name"
            rules={[
              { required: true, message: '请输入项目名称' },
              { min: 2, max: 50, message: '项目名称长度在 2 到 50 个字符' }
            ]}
          >
            <Input placeholder="请输入项目名称" maxLength={50} showCount />
          </Form.Item>

          <Form.Item
            label="项目描述"
            name="description"
          >
            <Input.TextArea
              placeholder="请输入项目描述（可选）"
              maxLength={200}
              showCount
              rows={3}
            />
          </Form.Item>

          <Alert
            message="项目代码将自动生成"
            description="您将自动成为项目管理员，可以邀请其他成员加入"
            type="info"
            showIcon
            style={{ marginBottom: 20 }}
          />

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={createLoading}>
                创建并进入
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ProjectSelector

