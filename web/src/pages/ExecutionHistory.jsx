import React, { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Space, message, Radio, Input } from 'antd'
import { ReloadOutlined, EyeOutlined, SearchOutlined } from '@ant-design/icons'
import { scriptApi, simpleJobsApi } from '../utils/api'
import { useNavigate } from 'react-router-dom'

const ExecutionHistory = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [tasks, setTasks] = useState([])
  const [filteredTasks, setFilteredTasks] = useState([])
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
        const jobResponse = await simpleJobsApi.getExecutions()
        const jobTasks = (jobResponse.executions || []).map(exec => ({
          task_id: exec.id || exec.execution_id,
          script_name: exec.job_name || exec.name || '未命名作业',
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

  const viewDetails = (task) => {
    // 直接跳转到详情页面
    const type = task.task_type === 'script' ? 'script' : 'job'
    navigate(`/execution-detail/${task.task_id}?type=${type}`)
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
          <Button icon={<ReloadOutlined />} onClick={loadTasks} loading={loading}>
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
    </div>
  )
}

export default ExecutionHistory
