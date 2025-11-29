import React, { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Space, message, Modal, Descriptions, Radio, Input } from 'antd'
import { ReloadOutlined, EyeOutlined, SearchOutlined, DesktopOutlined } from '@ant-design/icons'
import { scriptApi, simpleJobsApi } from '../utils/api'

const ExecutionHistory = () => {
  const [loading, setLoading] = useState(false)
  const [tasks, setTasks] = useState([])
  const [filteredTasks, setFilteredTasks] = useState([])
  const [detailsVisible, setDetailsVisible] = useState(false)
  const [currentTask, setCurrentTask] = useState(null)
  const [filterType, setFilterType] = useState('all') // all, script, job
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    loadTasks()
  }, [])

  useEffect(() => {
    filterTasks()
  }, [tasks, filterType, searchText])

  const loadTasks = async () => {
    try {
      setLoading(true)
      // 加载脚本执行历史
      const scriptResponse = await scriptApi.getTasks()
      const scriptTasks = (scriptResponse.tasks || []).map(task => ({
        ...task,
        task_type: 'script'
      }))
      
      // 加载作业执行历史
      try {
        const jobResponse = await simpleJobsApi.getExecutions({ project_id: 1 })
        const jobTasks = (jobResponse.executions || []).map(exec => ({
          task_id: exec.id || exec.execution_id,
          script_name: exec.job_name || exec.name || '未命名作业',  // 兼容多种字段名
          status: exec.status?.toLowerCase() || 'unknown',
          created_at: exec.created_at || exec.started_at,
          completed_at: exec.completed_at,
          agent_count: 1,
          task_type: 'job',
          ...exec
        }))
        
        // 合并两种类型的任务
        const allTasks = [...scriptTasks, ...jobTasks]
        allTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        setTasks(allTasks)
      } catch (error) {
        // 如果作业API失败，只显示脚本任务
        console.error('加载作业执行历史失败:', error)
        setTasks(scriptTasks)
      }
    } catch (error) {
      message.error('加载任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  const filterTasks = () => {
    let filtered = tasks

    // 按类型过滤
    if (filterType !== 'all') {
      filtered = filtered.filter(task => task.task_type === filterType)
    }

    // 按关键词搜索
    if (searchText) {
      filtered = filtered.filter(task =>
        task.script_name?.toLowerCase().includes(searchText.toLowerCase()) ||
        task.task_id?.toLowerCase().includes(searchText.toLowerCase())
      )
    }

    setFilteredTasks(filtered)
  }

  const viewDetails = async (task) => {
    try {
      if (task.task_type === 'script') {
        const details = await scriptApi.getTaskDetails(task.task_id)
        setCurrentTask(details)
      } else {
        const details = await simpleJobsApi.getExecution(task.task_id)
        setCurrentTask(details.execution || details)
      }
      setDetailsVisible(true)
    } catch (error) {
      message.error('加载任务详情失败')
    }
  }

  const columns = [
    {
      title: '类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 80,
      render: type => (
        <Tag color={type === 'script' ? 'blue' : 'green'}>
          {type === 'script' ? '脚本' : '作业'}
        </Tag>
      )
    },
    {
      title: '任务名称',
      dataIndex: 'script_name',
      key: 'script_name',
      width: 200,
      ellipsis: true
    },
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 200,
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: status => {
        // 统一转换为小写进行匹配
        const statusLower = status?.toLowerCase() || ''
        const colors = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error',
          completed: 'success'
        }
        const labels = {
          pending: '待执行',
          running: '执行中',
          success: '已完成',
          failed: '失败',
          completed: '已完成'
        }
        return <Tag color={colors[statusLower] || 'default'}>{labels[statusLower] || status}</Tag>
      }
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
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => viewDetails(record)}
        >
          详情
        </Button>
      )
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="执行历史"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadTasks}>
            刷新
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }} size="middle">
          <Space>
            <span>类型筛选：</span>
            <Radio.Group value={filterType} onChange={e => setFilterType(e.target.value)}>
              <Radio.Button value="all">全部</Radio.Button>
              <Radio.Button value="script">脚本执行</Radio.Button>
              <Radio.Button value="job">作业执行</Radio.Button>
            </Radio.Group>
          </Space>
          <Input
            placeholder="搜索任务名称或ID"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
        </Space>

        <Table
          columns={columns}
          dataSource={filteredTasks}
          rowKey="task_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title="任务详情"
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailsVisible(false)}>
            关闭
          </Button>
        ]}
        width={1000}
      >
        {currentTask && (
          <>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="任务ID" span={2}>
                {currentTask.task_id || currentTask.id || currentTask.execution_id}
              </Descriptions.Item>
              <Descriptions.Item label="任务名称" span={2}>
                {currentTask.script_name || currentTask.job_name}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {(() => {
                  const statusLower = currentTask.status?.toLowerCase() || ''
                  const statusMap = {
                    pending: { color: 'default', text: '待执行' },
                    running: { color: 'processing', text: '执行中' },
                    success: { color: 'success', text: '已完成' },
                    completed: { color: 'success', text: '已完成' },
                    failed: { color: 'error', text: '失败' }
                  }
                  const statusInfo = statusMap[statusLower] || { color: 'default', text: currentTask.status }
                  return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
                })()}
              </Descriptions.Item>
              <Descriptions.Item label="目标数量">
                {currentTask.agent_count || (currentTask.target_hosts?.length) || 1}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {currentTask.created_at}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {currentTask.completed_at || '未完成'}
              </Descriptions.Item>
              {currentTask.script && (
                <Descriptions.Item label="脚本内容" span={2}>
                  <pre style={{
                    background: '#f5f5f5',
                    padding: 8,
                    borderRadius: 4,
                    maxHeight: 300,
                    overflow: 'auto'
                  }}>
                    {currentTask.script}
                  </pre>
                </Descriptions.Item>
              )}
              {currentTask.error_message && (
                <Descriptions.Item label="错误信息" span={2}>
                  <span style={{ color: 'red' }}>{currentTask.error_message}</span>
                </Descriptions.Item>
              )}
              {currentTask.log && (
                <Descriptions.Item label="执行日志" span={2}>
                  <pre style={{
                    background: '#f5f5f5',
                    padding: 8,
                    borderRadius: 4,
                    maxHeight: 300,
                    overflow: 'auto'
                  }}>
                    {currentTask.log}
                  </pre>
                </Descriptions.Item>
              )}
            </Descriptions>

            {currentTask.results && Object.keys(currentTask.results).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ 
                  fontSize: 14, 
                  fontWeight: 'bold', 
                  marginBottom: 12,
                  color: '#000'
                }}>
                  执行结果
                </div>
                <div style={{ 
                  background: '#fafafa', 
                  padding: 16, 
                  borderRadius: 4,
                  border: '1px solid #e8e8e8'
                }}>
                  {Object.entries(currentTask.results).map(([stepKey, stepData]) => {
                    // 作业执行的results是 { step_1: { step_name: "xxx", results: {host_id: result} } }
                    // 脚本执行的results是 { host_id: result }
                    const isJobExecution = stepData.step_name && stepData.results
                    const resultsToRender = isJobExecution ? stepData.results : { [stepKey]: stepData }
                    
                    return (
                      <div key={stepKey}>
                        {isJobExecution && (
                          <div style={{ 
                            fontSize: 14, 
                            fontWeight: 'bold', 
                            marginBottom: 12,
                            color: '#1890ff',
                            padding: '8px 12px',
                            background: '#e6f7ff',
                            borderLeft: '3px solid #1890ff',
                            borderRadius: 2
                          }}>
                            {stepData.step_name}
                          </div>
                        )}
                        {Object.entries(resultsToRender).map(([hostId, result]) => {
                    // 根据 exit_code 判断成功还是失败
                    const isSuccess = result.exit_code === 0
                          const hostname = result.agent_hostname || result.hostname || '未知主机'
                          const ip = result.agent_ip || result.ip || ''
                    
                    // 合并所有输出
                    const stdout = result.stdout || result.output || ''
                    const stderr = result.stderr || result.error || ''
                    const combinedOutput = [stdout, stderr].filter(Boolean).join('\n')
                    
                    return (
                      <div key={hostId} style={{ 
                        marginBottom: 16,
                        background: '#fff',
                        padding: 12,
                        borderRadius: 4,
                        border: '1px solid #e8e8e8'
                      }}>
                        <div style={{ 
                          fontWeight: 'bold', 
                          marginBottom: 12,
                          borderBottom: '2px solid #e8e8e8',
                          paddingBottom: 8,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <div>
                            <DesktopOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                            <span style={{ fontSize: 16 }}>{hostname}</span>
                            {ip && (
                              <span style={{ marginLeft: 12, fontSize: 12, color: '#999', fontWeight: 'normal' }}>
                                ({ip})
                              </span>
                            )}
                          </div>
                          <div>
                            <Tag 
                              color={isSuccess ? 'success' : 'error'}
                              style={{ fontSize: 14, padding: '4px 12px' }}
                            >
                              {isSuccess ? '✓ 成功' : '✗ 失败'}
                            </Tag>
                            <span style={{ marginLeft: 12, fontSize: 12, color: '#999' }}>
                                    退出码: {result.exit_code !== undefined ? result.exit_code : 'N/A'}
                            </span>
                            {result.execution_time && (
                              <span style={{ marginLeft: 12, fontSize: 12, color: '#999' }}>
                                耗时: {result.execution_time.toFixed(2)}s
                              </span>
                            )}
                          </div>
                        </div>
                        {combinedOutput ? (
                          <div>
                            <div style={{ 
                              fontSize: 13, 
                              color: '#666', 
                              marginBottom: 6,
                              fontWeight: 'bold'
                            }}>
                              📋 执行输出:
                            </div>
                            <pre style={{
                              background: isSuccess ? '#f5f5f5' : '#fff1f0',
                              padding: 12,
                              borderRadius: 4,
                              maxHeight: 500,
                              overflow: 'auto',
                              margin: 0,
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              fontSize: 13,
                              lineHeight: 1.6,
                              border: `1px solid ${isSuccess ? '#d9d9d9' : '#ffccc7'}`,
                              color: isSuccess ? '#000' : '#cf1322'
                            }}>
                              {combinedOutput}
                            </pre>
                          </div>
                        ) : (
                          <div style={{ 
                            color: '#999', 
                            fontStyle: 'italic',
                            textAlign: 'center',
                            padding: 20
                          }}>
                            📭 无输出内容
                          </div>
                        )}
                            </div>
                          )
                        })}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </Modal>
    </div>
  )
}

export default ExecutionHistory

