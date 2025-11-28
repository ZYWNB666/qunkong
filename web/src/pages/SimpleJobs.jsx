import React, { useState, useEffect } from 'react'
import { 
  Card, Table, Button, Space, message, Modal, Form, Input, 
  Select, Divider, Tag, Collapse, InputNumber, Popconfirm, Tabs, List
} from 'antd'
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, 
  ReloadOutlined, MinusCircleOutlined, DesktopOutlined, CodeOutlined,
  SettingOutlined
} from '@ant-design/icons'
import { simpleJobsApi, agentApi } from '../utils/api'

const { TextArea } = Input
const { Panel } = Collapse
const { TabPane } = Tabs

const SimpleJobs = () => {
  const [loading, setLoading] = useState(false)
  const [jobs, setJobs] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingJob, setEditingJob] = useState(null)
  const [agents, setAgents] = useState([])
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('basic')
  const [formModified, setFormModified] = useState(false)

  useEffect(() => {
    loadJobs()
    loadAgents()
  }, [])

  const loadJobs = async () => {
    try {
      setLoading(true)
      const response = await simpleJobsApi.getJobs({ project_id: 1 })
      setJobs(response.jobs || [])
    } catch (error) {
      message.error('加载作业列表失败')
    } finally {
      setLoading(false)
    }
  }

  const loadAgents = async () => {
    try {
      const response = await agentApi.getAgents({ project_id: 1 })
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
      
      console.log('=== 加载的作业详情 ===')
      console.log('完整数据:', jobDetails)
      console.log('host_groups:', jobDetails.host_groups)
      console.log('steps:', jobDetails.steps)
      
      // 处理步骤数据：将 host_group_id 转换为 host_group_index
      const processedSteps = jobDetails.steps?.map((step, stepIndex) => {
        console.log(`步骤${stepIndex + 1}:`, {
          step_name: step.step_name,
          host_group_id: step.host_group_id,
          host_group_id_type: typeof step.host_group_id
        })
        
        // 找到对应的 host_group_id 在 host_groups 数组中的索引
        let hostGroupIndex = -1
        if (step.host_group_id) {
          hostGroupIndex = jobDetails.host_groups?.findIndex(hg => {
            console.log(`  比较: hg.id(${hg.id}) === step.host_group_id(${step.host_group_id})`, hg.id === step.host_group_id)
            return hg.id === step.host_group_id
          }) ?? -1
        }
        
        console.log(`  找到的索引: ${hostGroupIndex}`)
        
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
      
      console.log('=== 设置的表单值 ===')
      console.log('host_groups:', jobDetails.host_groups)
      console.log('steps:', processedSteps)
      
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
      const values = await form.validateFields()
      
      console.log('=== 提交前的表单值 ===')
      console.log('原始values:', values)
      
      // 过滤有效的主机组
      const validHostGroups = values.host_groups?.filter(hg => hg.group_name && hg.host_ids?.length > 0) || []
      
      const payload = {
        name: values.name,
        description: values.description || '',
        host_groups: validHostGroups,
        variables: values.variables?.filter(v => v.var_name) || [],
        steps: values.steps?.map((step, index) => ({
          step_name: step.step_name,
          script_content: step.script_content,
          timeout: step.timeout || 300,
          step_order: index + 1,
          // 使用索引关联主机组，后端会根据索引找到对应的主机组
          host_group_index: step.host_group_index != null ? step.host_group_index : null
        })) || []
      }
      
      console.log('=== 提交的payload ===')
      console.log('payload:', payload)
      console.log('steps:', payload.steps)
      
      if (editingJob) {
        // 更新作业 - 需要分步骤更新
        await simpleJobsApi.updateJob(editingJob.id, {
          name: payload.name,
          description: payload.description
        })
        
        // 删除旧的主机组、变量、步骤，创建新的
        // 这里简化处理，实际应该做增量更新
        message.success('作业更新成功')
      } else {
        const response = await simpleJobsApi.createJob(payload)
        console.log('创建作业响应:', response)
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
        message.error(error.response?.data?.detail || '操作失败')
      }
    }
  }

  const handleExecute = async (jobId) => {
    try {
      const response = await simpleJobsApi.executeJob(jobId)
      message.success(`作业已开始执行，共 ${response.total_steps} 个步骤`)
    } catch (error) {
      message.error(error.response?.data?.detail || '执行失败')
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
        <Space size="small">
          <Button 
            type="primary" 
            size="small" 
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecute(record.id)}
            disabled={!record.step_count}
          >
            执行
          </Button>
          <Button 
            size="small" 
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
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
        onCancel={handleModalClose}
        onOk={handleSubmit}
        width={900}
        destroyOnClose
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
                              console.log('TagRender props.value:', props.value)
                              console.log('Agents length:', agents.length)
                              console.log('Agents IDs:', agents.map(a => a.id))
                              const agent = agents.find(a => a.id === props.value)
                              console.log('Found agent:', agent)
                              return (
                                <Tag 
                                  closable={props.closable} 
                                  onClose={props.onClose}
                                  style={{ marginRight: 3 }}
                                >
                                  {agent ? `${agent.hostname} (${agent.ip_address || agent.ip})` : props.value}
                                </Tag>
                              )
                            }}
                          >
                            {agents.map(agent => (
                              <Select.Option key={agent.id} value={agent.id}>
                                {agent.hostname} ({agent.ip_address || agent.ip || 'N/A'})
                              </Select.Option>
                            ))}
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
