import React, { useState, useEffect } from 'react'
import { Card, Table, Button, Space, Tag, message, Modal, Form, Input, Select } from 'antd'
import { PlusOutlined, ReloadOutlined, PlayCircleOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { simpleJobsApi, agentApi } from '../utils/api'

const { TextArea } = Input

const SimpleJobs = () => {
  const [loading, setLoading] = useState(false)
  const [jobs, setJobs] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingJob, setEditingJob] = useState(null)
  const [agents, setAgents] = useState([])
  const [form] = Form.useForm()

  useEffect(() => {
    loadJobs()
    loadAgents()
  }, [])

  const loadJobs = async () => {
    try {
      setLoading(true)
      const response = await simpleJobsApi.getJobs()
      setJobs(response.jobs || [])
    } catch (error) {
      message.error('加载作业列表失败')
    } finally {
      setLoading(false)
    }
  }

  const loadAgents = async () => {
    try {
      const response = await agentApi.getAgents()
      setAgents(response.agents || [])
    } catch (error) {
      console.error('加载 Agent 列表失败:', error)
    }
  }

  const handleCreate = () => {
    setEditingJob(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = async (job) => {
    try {
      // 先调用详情接口获取完整的作业信息（包括 steps）
      const response = await simpleJobsApi.getJob(job.id)
      const jobDetails = response.job
      
      setEditingJob(jobDetails)
      
      // 提取第一个步骤的脚本内容
      const firstStep = jobDetails.steps?.[0]
      const script = firstStep?.script_content || jobDetails.script || ''
      const timeout = firstStep?.timeout || jobDetails.timeout || 3600
      
      form.setFieldsValue({
        job_name: jobDetails.name || jobDetails.job_name,  // 兼容两种字段名
        description: jobDetails.description || '',
        target_hosts: jobDetails.target_hosts || (jobDetails.target_agent_id ? [jobDetails.target_agent_id] : []),
        script: script,
        timeout: timeout
      })
      setModalVisible(true)
    } catch (error) {
      console.error('加载作业详情失败:', error)
      message.error('加载作业详情失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      
      // 转换字段名称以匹配后端API
      const payload = {
        name: values.job_name,  // 后端期望 name 字段
        description: values.description || '',
        target_agent_id: values.target_hosts?.[0] || '',  // 后端期望单个 agent ID
        target_hosts: values.target_hosts || [],  // 保留用于多主机支持
        steps: [
          {
            step_name: '执行脚本',
            script_content: values.script,
            timeout: values.timeout || 3600,
            step_order: 1
          }
        ]
      }
      
      if (editingJob) {
        await simpleJobsApi.updateJob(editingJob.id, payload)
        message.success('作业更新成功')
      } else {
        await simpleJobsApi.createJob(payload)
        message.success('作业创建成功')
      }
      
      setModalVisible(false)
      form.resetFields()
      loadJobs()
    } catch (error) {
      if (error.errorFields) {
        message.error('请填写完整信息')
      } else {
        console.error('作业提交错误:', error)
        message.error(error.response?.data?.error || '操作失败')
      }
    }
  }

  const handleExecute = async (jobId) => {
    try {
      await simpleJobsApi.executeJob(jobId)
      message.success('作业已开始执行')
    } catch (error) {
      message.error(error.response?.data?.error || '执行失败')
    }
  }

  const handleDelete = (jobId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个作业吗？',
      onOk: async () => {
        try {
          await simpleJobsApi.deleteJob(jobId)
          message.success('删除成功')
          loadJobs()
        } catch (error) {
          message.error('删除失败')
        }
      }
    })
  }

  const columns = [
    {
      title: '作业名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
      render: (text, record) => record.name || record.job_name  // 兼容两种字段名
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 250,
      ellipsis: {
        showTitle: true,
      },
      render: (text) => text || '-'
    },
    {
      title: '目标主机',
      key: 'target_hosts',
      width: 90,
      align: 'center',
      render: (_, record) => {
        const hosts = record.target_hosts || (record.target_agent_id ? [record.target_agent_id] : [])
        return hosts.length || 0
      }
    },
    {
      title: '步骤数',
      key: 'steps',
      width: 80,
      align: 'center',
      render: (_, record) => record.steps?.length || 0
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
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecute(record.id)}
          >
            执行
          </Button>
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
        title="作业管理"
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              创建作业
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadJobs}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={jobs}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingJob ? '编辑作业' : '创建作业'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        width={700}
        okText="确定"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            job_name: '',
            description: '',
            target_hosts: [],
            script: '',
            timeout: 3600
          }}
        >
          <Form.Item
            name="job_name"
            label="作业名称"
            rules={[
              { required: true, message: '请输入作业名称' },
              { whitespace: true, message: '作业名称不能为空' }
            ]}
          >
            <Input placeholder="请输入作业名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={2} placeholder="请输入作业描述（可选）" />
          </Form.Item>

          <Form.Item
            name="target_hosts"
            label="目标主机"
            rules={[{ required: true, message: '请选择至少一个目标主机' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择目标主机"
              optionFilterProp="label"
              showSearch
              options={agents.map(agent => ({
                label: `${agent.hostname} (${agent.ip_address})`,
                value: agent.id
              }))}
            />
          </Form.Item>

          <Form.Item
            name="script"
            label="执行脚本"
            rules={[
              { required: true, message: '请输入执行脚本' },
              { whitespace: true, message: '脚本内容不能为空' }
            ]}
          >
            <TextArea
              rows={10}
              placeholder="#!/bin/bash&#10;echo 'Hello World'"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item
            name="timeout"
            label="超时时间（秒）"
          >
            <Input type="number" min={60} max={86400} placeholder="默认3600秒" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SimpleJobs

