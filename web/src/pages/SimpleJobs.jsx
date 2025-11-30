import React, { useState, useEffect } from 'react'
import {
  Card, Table, Button, Space, message, Modal, Form, Input,
  Select, Divider, Tag, Collapse, InputNumber, Popconfirm, Tabs, List
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined,
  ReloadOutlined, MinusCircleOutlined, DesktopOutlined, CodeOutlined,
  SettingOutlined, CopyOutlined, HistoryOutlined
} from '@ant-design/icons'
import { simpleJobsApi, agentApi } from '../utils/api'
import { useNavigate } from 'react-router-dom'
import { usePermissions, PermissionGate } from '../hooks/usePermissions'

const { TextArea } = Input
const { Panel } = Collapse
const { TabPane } = Tabs

const SimpleJobs = () => {
  const navigate = useNavigate()
  const { hasPermission } = usePermissions()
  const [loading, setLoading] = useState(false)
  const [jobs, setJobs] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingJob, setEditingJob] = useState(null)
  const [agents, setAgents] = useState([])
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('basic')
  const [formModified, setFormModified] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [executingJobId, setExecutingJobId] = useState(null)
  const [cloningJobId, setCloningJobId] = useState(null)

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
      console.log('作业管理-加载的agents数据:', response.agents)
      setAgents(response.agents || [])
    } catch (error) {
      console.error('加载主机列表失败:', error)
    }
  }

  const handleCreate = () => {
    setEditingJob(null)
    form.resetFields()
    form.setFieldsValue({
      host_groups: [{ group_name: '默认主机组', host_ids: [] }],
      variables: [],
      steps: [{ step_name: '步骤1', script_content: '#!/bin/bash\necho "Hello World"', timeout: 300 }]
    })
    setActiveTab('basic')
    setFormModified(false)
    setModalVisible(true)
  }

  const handleEdit = async (job) => {
    try {
      const response = await simpleJobsApi.getJob(job.id)
      const jobDetails = response.job
      
      // 处理步骤数据：将 host_group_id 转换为 host_group_index
      const processedSteps = jobDetails.steps?.map((step, stepIndex) => {
        // 找到对应的 host_group_id 在 host_groups 数组中的索引
        let hostGroupIndex = -1
        if (step.host_group_id) {
          hostGroupIndex = jobDetails.host_groups?.findIndex(hg => hg.id === step.host_group_id) ?? -1
        }
        
        return {
          step_name: step.step_name,
          script_content: step.script_content,
          timeout: step.timeout || 300,
          host_group_index: hostGroupIndex >= 0 ? hostGroupIndex : null
        }
      }) || [{ step_name: '步骤1', script_content: '', timeout: 300 }]
      
      setEditingJob(jobDetails)
      form.setFieldsValue({
        name: jobDetails.name,
        description: jobDetails.description || '',
        host_groups: jobDetails.host_groups?.length > 0 ? jobDetails.host_groups : [{ group_name: '默认主机组', host_ids: [] }],
        variables: jobDetails.variables || [],
        steps: processedSteps
      })
      
      setActiveTab('basic')
      setFormModified(false)
      setModalVisible(true)
    } catch (error) {
      console.error('加载作业详情失败:', error)
      message.error('加载作业详情失败')
    }
  }

  const handleModalClose = () => {
    if (formModified) {
      Modal.confirm({
        title: '确认退出',
        content: '您有未保存的修改，确定要退出吗？退出后修改将丢失。',
        okText: '确定退出',
        cancelText: '继续编辑',
        okType: 'danger',
        onOk: () => {
          setModalVisible(false)
          setFormModified(false)
          form.resetFields()
        }
      })
    } else {
      setModalVisible(false)
      form.resetFields()
    }
  }

  const handleSubmit = async () => {
    try {
      setSubmitting(true)
      const values = await form.validateFields()
      
      console.log('提交的表单值:', values)
      
      // 过滤有效的主机组
      const validHostGroups = values.host_groups?.filter(hg => hg.group_name && hg.host_ids?.length > 0) || []
      
      // 确保获取所有步骤，包括新增的
      const allSteps = values.steps?.filter(step => step && step.step_name && step.script_content).map((step, index) => ({
        step_name: step.step_name,
        script_content: step.script_content,
        timeout: step.timeout || 300,
        step_order: index + 1,
        host_group_index: step.host_group_index != null ? step.host_group_index : null
      })) || []
      
      console.log('处理后的步骤:', allSteps)
      
      const payload = {
        name: values.name,
        description: values.description || '',
        host_groups: validHostGroups,
        variables: values.variables?.filter(v => v.var_name) || [],
        steps: allSteps
      }
      
      console.log('发送的payload:', payload)
      
      if (editingJob) {
        // 使用update API直接更新
        await simpleJobsApi.updateJob(editingJob.id, payload)
        message.success('作业更新成功')
      } else {
        await simpleJobsApi.createJob(payload)
        message.success('作业创建成功')
      }
      
      setModalVisible(false)
      setFormModified(false)
      form.resetFields()
      loadJobs()
    } catch (error) {
      if (error.errorFields) {
        message.error('请填写完整信息')
      } else {
        console.error('作业提交错误:', error)
        const errorDetail = error.response?.data?.detail
        let errorMessage = '操作失败'
        
        if (typeof errorDetail === 'string') {
          errorMessage = errorDetail
        } else if (Array.isArray(errorDetail)) {
          errorMessage = errorDetail.map(e => e.msg || JSON.stringify(e)).join('; ')
        } else if (errorDetail) {
          errorMessage = JSON.stringify(errorDetail)
        }
        
        message.error(errorMessage)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleExecute = async (jobId, jobName) => {
    try {
      setExecutingJobId(jobId)
      const response = await simpleJobsApi.executeJob(jobId)
      
      message.success(`作业"${jobName}"已开始执行`)
      
      // 直接跳转到详情页面，带上类型参数
      navigate(`/execution-detail/${response.execution_id}?type=job`)
    } catch (error) {
      message.error(error.response?.data?.detail || '执行失败')
    } finally {
      setExecutingJobId(null)
    }
  }

  const handleClone = async (jobId, jobName) => {
    try {
      setCloningJobId(jobId)
      const response = await simpleJobsApi.cloneJob(jobId)
      message.success(`作业已克隆：${response.new_name}`)
      loadJobs()
    } catch (error) {
      message.error(error.response?.data?.detail || '克隆失败')
    } finally {
      setCloningJobId(null)
    }
  }

  const handleDelete = async (jobId) => {
    try {
      await simpleJobsApi.deleteJob(jobId)
      message.success('作业删除成功')
      loadJobs()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: '作业名称',
      dataIndex: 'name',
      key: 'name',
      width: 200
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      render: desc => desc || '-'
    },
    {
      title: '主机组数',
      dataIndex: 'host_group_count',
      key: 'host_group_count',
      width: 100,
      render: count => <Tag color="blue">{count || 0}</Tag>
    },
    {
      title: '步骤数',
      dataIndex: 'step_count',
      key: 'step_count',
      width: 80,
      render: count => <Tag color="green">{count || 0}</Tag>
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
        <Space size="small" wrap>
          <PermissionGate permission="job.execute">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record.id, record.name)}
              disabled={!record.step_count}
              loading={executingJobId === record.id}
            >
              执行
            </Button>
          </PermissionGate>
          
          <PermissionGate permission="job.edit">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            >
              编辑
            </Button>
          </PermissionGate>
          
          <PermissionGate permission="job.create">
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleClone(record.id, record.name)}
              loading={cloningJobId === record.id}
            >
              克隆
            </Button>
          </PermissionGate>
          
          <PermissionGate permission="job.delete">
            <Popconfirm
              title="确定要删除这个作业吗？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </PermissionGate>
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
            <PermissionGate permission="job.create">
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                创建作业
              </Button>
            </PermissionGate>
            <Button icon={<ReloadOutlined />} onClick={loadJobs} loading={loading}>
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
        onCancel={handleModalClose}
        onOk={handleSubmit}
        confirmLoading={submitting}
        width={900}
        destroyOnHidden
        maskClosable={false}
      >
        <Form 
          form={form} 
          layout="vertical"
          onValuesChange={() => setFormModified(true)}
        >
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            {/* 基本信息 */}
            <TabPane tab={<span><SettingOutlined />基本信息</span>} key="basic">
              <Form.Item
                name="name"
                label="作业名称"
                rules={[{ required: true, message: '请输入作业名称' }]}
              >
                <Input placeholder="请输入作业名称" />
              </Form.Item>
              <Form.Item name="description" label="描述">
                <TextArea rows={2} placeholder="请输入作业描述（可选）" />
              </Form.Item>
            </TabPane>

            {/* 主机组 */}
            <TabPane tab={<span><DesktopOutlined />主机组</span>} key="hosts">
              <Form.List name="host_groups">
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }, index) => (
                      <Card 
                        key={key} 
                        size="small" 
                        title={`主机组 ${index + 1}`}
                        extra={
                          fields.length > 1 && (
                            <Button 
                              type="text" 
                              danger 
                              icon={<MinusCircleOutlined />}
                              onClick={() => remove(name)}
                            />
                          )
                        }
                        style={{ marginBottom: 16 }}
                      >
                        <Form.Item
                          {...restField}
                          name={[name, 'group_name']}
                          label="组名称"
                          rules={[{ required: true, message: '请输入组名称' }]}
                        >
                          <Input placeholder="例如：Web服务器组" />
                        </Form.Item>
                        <Form.Item
                          {...restField}
                          name={[name, 'host_ids']}
                          label="选择主机"
                          rules={[{ required: true, message: '请选择至少一台主机' }]}
                        >
                          <Select
                            mode="multiple"
                            placeholder="选择主机"
                            optionFilterProp="children"
                            tagRender={(props) => {
                              const agent = agents.find(a => a.id === props.value)
                              const isOnline = agent?.status === 'online' || agent?.status === 'connected'
                              return (
                                <Tag
                                  closable={props.closable}
                                  onClose={props.onClose}
                                  color={isOnline ? 'success' : 'default'}
                                  style={{ marginRight: 3 }}
                                >
                                  {agent ? `${isOnline ? '🟢' : '⚫'} ${agent.hostname} (${agent.ip_address || agent.ip})` : props.value}
                                </Tag>
                              )
                            }}
                          >
                            {agents.map(agent => {
                              const isOnline = agent.status === 'online' || agent.status === 'connected'
                              console.log(`Agent ${agent.hostname} status:`, agent.status, 'isOnline:', isOnline)
                              return (
                                <Select.Option key={agent.id} value={agent.id}>
                                  <Space>
                                    <Tag color={isOnline ? 'success' : 'error'} style={{ margin: 0 }}>
                                      {isOnline ? '在线' : '离线'}
                                    </Tag>
                                    <span>{agent.hostname}</span>
                                    <span style={{ color: '#999' }}>({agent.ip_address || agent.ip || 'N/A'})</span>
                                  </Space>
                                </Select.Option>
                              )
                            })}
                          </Select>
                        </Form.Item>
                      </Card>
                    ))}
                    <Button 
                      type="dashed" 
                      onClick={() => add({ group_name: `主机组${fields.length + 1}`, host_ids: [] })} 
                      block 
                      icon={<PlusOutlined />}
                    >
                      添加主机组
                    </Button>
                  </>
                )}
              </Form.List>
            </TabPane>

            {/* 变量 */}
            <TabPane tab={<span><CodeOutlined />变量</span>} key="variables">
              <Form.List name="variables">
                {(fields, { add, remove }) => (
                  <>
                    {fields.map(({ key, name, ...restField }) => (
                      <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                        <Form.Item
                          {...restField}
                          name={[name, 'var_name']}
                          rules={[{ required: true, message: '请输入变量名' }]}
                        >
                          <Input placeholder="变量名" style={{ width: 200 }} />
                        </Form.Item>
                        <Form.Item
                          {...restField}
                          name={[name, 'var_value']}
                        >
                          <Input placeholder="变量值" style={{ width: 300 }} />
                        </Form.Item>
                        <MinusCircleOutlined onClick={() => remove(name)} style={{ color: '#ff4d4f' }} />
                      </Space>
                    ))}
                    <Button 
                      type="dashed" 
                      onClick={() => add({ var_name: '', var_value: '' })} 
                      block 
                      icon={<PlusOutlined />}
                    >
                      添加变量
                    </Button>
                    <div style={{ marginTop: 8, color: '#888', fontSize: 12 }}>
                      提示：在脚本中使用 {'${变量名}'} 或 $变量名 引用变量
                    </div>
                  </>
                )}
              </Form.List>
            </TabPane>

            {/* 步骤 */}
            <TabPane tab={<span><PlayCircleOutlined />执行步骤</span>} key="steps">
              <Form.List name="steps">
                {(fields, { add, remove }) => (
                  <>
                    <Collapse defaultActiveKey={['0']}>
                      {fields.map(({ key, name, ...restField }, index) => (
                        <Panel 
                          header={
                            <Space>
                              <Tag color="blue">步骤 {index + 1}</Tag>
                              <Form.Item
                                noStyle
                                shouldUpdate={(prevValues, curValues) => 
                                  prevValues.steps?.[index]?.step_name !== curValues.steps?.[index]?.step_name
                                }
                              >
                                {({ getFieldValue }) => 
                                  getFieldValue(['steps', index, 'step_name']) || '未命名步骤'
                                }
                              </Form.Item>
                            </Space>
                          }
                          key={index}
                          extra={
                            fields.length > 1 && (
                              <Button 
                                type="text" 
                                danger 
                                size="small"
                                icon={<DeleteOutlined />}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  remove(name)
                                }}
                              />
                            )
                          }
                        >
                          <Form.Item
                            {...restField}
                            name={[name, 'step_name']}
                            label="步骤名称"
                            rules={[{ required: true, message: '请输入步骤名称' }]}
                          >
                            <Input placeholder="例如：安装依赖" />
                          </Form.Item>
                          <Form.Item noStyle shouldUpdate>
                            {({ getFieldValue }) => {
                              const hostGroups = getFieldValue('host_groups') || []
                              return (
                                <Form.Item
                                  {...restField}
                                  name={[name, 'host_group_index']}
                                  label="绑定主机组"
                                >
                                  <Select
                                    placeholder="选择要执行的主机组（不选则使用第一个主机组）"
                                    allowClear
                                  >
                                    {hostGroups.map((hg, idx) => (
                                      <Select.Option key={idx} value={idx}>
                                        {hg?.group_name || `主机组${idx + 1}`}
                                      </Select.Option>
                                    ))}
                                  </Select>
                                </Form.Item>
                              )
                            }}
                          </Form.Item>
                          <Form.Item
                            {...restField}
                            name={[name, 'script_content']}
                            label="执行脚本"
                            rules={[{ required: true, message: '请输入脚本内容' }]}
                          >
                            <TextArea 
                              rows={6} 
                              placeholder={"#!/bin/bash\necho 'Hello World'"} 
                              style={{ fontFamily: 'monospace' }}
                            />
                          </Form.Item>
                          <Form.Item
                            {...restField}
                            name={[name, 'timeout']}
                            label="超时时间（秒）"
                            initialValue={300}
                          >
                            <InputNumber min={10} max={86400} style={{ width: 200 }} />
                          </Form.Item>
                        </Panel>
                      ))}
                    </Collapse>
                    <Button 
                      type="dashed" 
                      onClick={() => add({ 
                        step_name: `步骤${fields.length + 1}`, 
                        script_content: '#!/bin/bash\n', 
                        timeout: 300 
                      })} 
                      block 
                      icon={<PlusOutlined />}
                      style={{ marginTop: 16 }}
                    >
                      添加步骤
                    </Button>
                  </>
                )}
              </Form.List>
            </TabPane>
          </Tabs>
        </Form>
      </Modal>
    </div>
  )
}

export default SimpleJobs
