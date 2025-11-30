import React, { useState, useEffect, useRef } from 'react'
import { Card, Descriptions, Tag, Button, Space, message, Spin } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, DesktopOutlined } from '@ant-design/icons'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { simpleJobsApi, scriptApi } from '../utils/api'

const JobExecutionDetail = () => {
  const navigate = useNavigate()
  const { executionId } = useParams()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [execution, setExecution] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const timerRef = useRef(null)
  const executionType = searchParams.get('type') // 'job' or 'script'

  useEffect(() => {
    loadExecutionDetail()
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [executionId])

  useEffect(() => {
    if (autoRefresh && execution && ['RUNNING', 'PENDING', 'running', 'pending'].includes(execution.status)) {
      // 每2秒自动刷新
      timerRef.current = setInterval(() => {
        loadExecutionDetail(true)
      }, 2000)
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [autoRefresh, execution?.status])

  const loadExecutionDetail = async (silent = false) => {
    try {
      if (!silent) {
        setLoading(true)
      }
      
      // 根据type参数决定调用哪个API，避免不必要的404
      if (executionType === 'script') {
        // 脚本执行
        const response = await scriptApi.getTaskDetails(executionId)
        setExecution(response)
      } else if (executionType === 'job') {
        // 作业执行
        const response = await simpleJobsApi.getExecution(executionId)
        setExecution(response.execution || response)
      } else {
        // 如果没有指定类型，先尝试作业执行API
        try {
          const response = await simpleJobsApi.getExecution(executionId)
          setExecution(response.execution || response)
        } catch (jobError) {
          // 如果失败，尝试脚本执行API
          const response = await scriptApi.getTaskDetails(executionId)
          setExecution(response)
        }
      }
    } catch (error) {
      if (!silent) {
        message.error('加载执行详情失败')
      }
      console.error('加载执行详情失败:', error)
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  const getStatusInfo = (status) => {
    const statusLower = status?.toLowerCase() || ''
    const statusMap = {
      pending: { color: 'default', text: '待执行' },
      running: { color: 'processing', text: '执行中' },
      success: { color: 'success', text: '已完成' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' }
    }
    return statusMap[statusLower] || { color: 'default', text: status }
  }

  if (loading && !execution) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  if (!execution) {
    return (
      <div style={{ padding: 24 }}>
        <Card>
          <p>未找到执行记录</p>
          <Button onClick={() => navigate('/execution-history')}>返回执行历史</Button>
        </Card>
      </div>
    )
  }

  const statusInfo = getStatusInfo(execution.status)
  const isRunning = ['RUNNING', 'PENDING', 'running', 'pending'].includes(execution.status)

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <Button 
              type="text" 
              icon={<ArrowLeftOutlined />} 
              onClick={() => navigate('/execution-history')}
            >
              返回
            </Button>
            <span>执行详情</span>
            {isRunning && <Tag color="processing">自动刷新中...</Tag>}
          </Space>
        }
        extra={
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={() => loadExecutionDetail()}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Descriptions bordered column={2}>
          <Descriptions.Item label="任务ID" span={2}>
            {execution.task_id || execution.id || execution.execution_id}
          </Descriptions.Item>
          <Descriptions.Item label="任务名称" span={2}>
            {execution.script_name || execution.job_name}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="目标数量">
            {execution.agent_count || (execution.target_hosts?.length) || execution.total_steps || 1}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {execution.created_at || execution.started_at}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {execution.completed_at || '未完成'}
          </Descriptions.Item>
          {execution.current_step && execution.total_steps && (
            <Descriptions.Item label="执行进度" span={2}>
              步骤 {execution.current_step} / {execution.total_steps}
            </Descriptions.Item>
          )}
          {execution.script && (
            <Descriptions.Item label="脚本内容" span={2}>
              <pre style={{
                background: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                maxHeight: 300,
                overflow: 'auto',
                margin: 0
              }}>
                {execution.script}
              </pre>
            </Descriptions.Item>
          )}
          {execution.error_message && (
            <Descriptions.Item label="错误信息" span={2}>
              <span style={{ color: 'red' }}>{execution.error_message}</span>
            </Descriptions.Item>
          )}
        </Descriptions>

        {/* 执行日志 */}
        {execution.execution_log && execution.execution_log.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 12 }}>
              执行日志
            </div>
            <div style={{ 
              background: '#f5f5f5', 
              padding: 12, 
              borderRadius: 4,
              maxHeight: 400,
              overflow: 'auto'
            }}>
              {execution.execution_log.map((log, index) => (
                <div key={index} style={{ marginBottom: 8 }}>
                  <span style={{ color: '#999', marginRight: 12 }}>
                    {log.time}
                  </span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 执行结果 */}
        {execution.results && Object.keys(execution.results).length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 12 }}>
              执行结果
            </div>
            <div style={{ 
              background: '#fafafa', 
              padding: 16, 
              borderRadius: 4,
              border: '1px solid #e8e8e8'
            }}>
              {Object.entries(execution.results).map(([stepKey, stepData]) => {
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
                      const isSuccess = result.exit_code === 0
                      const hostname = result.agent_hostname || result.hostname || '未知主机'
                      const ip = result.agent_ip || result.ip || ''
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
      </Card>
    </div>
  )
}

export default JobExecutionDetail