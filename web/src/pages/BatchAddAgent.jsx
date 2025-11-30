import React, { useState } from 'react'
import { Card, Form, Input, Button, Radio, Upload, message, Table, Tag, Space, Divider, Result } from 'antd'
import { UploadOutlined, PlusOutlined, LockOutlined } from '@ant-design/icons'
import api from '../utils/api'
import { usePermissions } from '../hooks/usePermissions'

const { TextArea } = Input

function BatchAddAgent() {
  // 所有Hooks必须在顶部调用,不能有条件性提前return
  const { hasPermission, loading: permissionLoading } = usePermissions()
  const [form] = Form.useForm()
  const [authType, setAuthType] = useState('password')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [sshKey, setSshKey] = useState(null)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('install')

  const columns = [
    {
      title: '主机IP',
      dataIndex: 'ip',
      key: 'ip',
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        if (status === 'success') {
          return <Tag color="success">安装成功</Tag>
        } else if (status === 'running') {
          return <Tag color="processing">安装中...</Tag>
        } else if (status === 'failed') {
          return <Tag color="error">安装失败</Tag>
        } else {
          return <Tag color="default">等待中</Tag>
        }
      },
    },
    {
      title: 'Agent ID',
      dataIndex: 'agent_id',
      key: 'agent_id',
      render: (text) => text || '-',
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
  ]

  const historyColumns = [
    {
      title: 'Batch ID',
      dataIndex: 'batch_id',
      key: 'batch_id',
      width: 180,
    },
    {
      title: '主机IP',
      dataIndex: 'ip',
      key: 'ip',
      width: 140,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 100,
    },
    {
      title: 'Agent ID',
      dataIndex: 'agent_id',
      key: 'agent_id',
      width: 180,
      render: (text) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const colorMap = {
          'success': 'success',
          'failed': 'error',
          'running': 'processing',
          'pending': 'default'
        }
        const labelMap = {
          'success': '成功',
          'failed': '失败',
          'running': '安装中',
          'pending': '等待中'
        }
        return <Tag color={colorMap[status]}>{labelMap[status]}</Tag>
      },
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '安装时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
  ]

  const loadHistory = async () => {
    try {
      setHistoryLoading(true)
      const currentProject = JSON.parse(localStorage.getItem('qunkong_current_project') || '{}')
      const response = await api.get('/agents/install-history', {
        params: { project_id: currentProject.id || 1 }
      })
      setHistory(response.history || [])
    } catch (error) {
      console.error('加载历史记录失败:', error)
      message.error('加载历史记录失败')
    } finally {
      setHistoryLoading(false)
    }
  }

  // 组件加载时获取历史记录
  React.useEffect(() => {
    if (activeTab === 'history') {
      loadHistory()
    }
  }, [activeTab])

  const handleSubmit = async (values) => {
    try {
      setLoading(true)
      setResults([])

      // 解析主机列表
      const hosts = values.hosts.split('\n').filter(line => line.trim())
      const hostList = []

      for (const line of hosts) {
        const parts = line.trim().split('|')
        if (parts.length < 3) {
          message.error(`格式错误: ${line}`)
          continue
        }

        const host = {
          username: parts[0].trim(),
          ip: parts[1].trim(),
          port: parseInt(parts[2].trim()) || 22,
        }

        if (authType === 'password') {
          if (parts.length < 4) {
            message.error(`缺少密码: ${line}`)
            continue
          }
          host.password = parts[3].trim()
        }

        hostList.push(host)
      }

      if (hostList.length === 0) {
        message.error('没有有效的主机配置')
        setLoading(false)
        return
      }

      // 初始化结果列表
      const initialResults = hostList.map(host => ({
        ...host,
        key: host.ip,
        status: 'pending',
        agent_id: null,
        message: '等待安装...',
      }))
      setResults(initialResults)

      // 构建请求数据
      const formData = new FormData()
      formData.append('auth_type', authType)
      formData.append('hosts', JSON.stringify(hostList))
      
      if (authType === 'key' && sshKey) {
        formData.append('ssh_key', sshKey)
      }
      
      // 添加Agent下载URL和MD5
      formData.append('agent_download_url', values.agent_download_url)
      formData.append('agent_md5', values.agent_md5)
      
      // 添加自定义Server URL（如果提供）
      if (values.server_url) {
        formData.append('server_url', values.server_url)
      }
      
      // 添加项目ID
      const currentProject = JSON.parse(localStorage.getItem('qunkong_current_project') || '{}')
      const projectId = currentProject.id || 1
      
      // 调试：打印FormData内容
      console.log('提交数据:', {
        auth_type: authType,
        hosts_count: hostList.length,
        agent_download_url: values.agent_download_url,
        agent_md5: values.agent_md5,
        server_url: values.server_url || '未设置',
        project_id: projectId
      })
      
      // 调试：验证FormData内容
      for (let pair of formData.entries()) {
        console.log('FormData字段:', pair[0], '=', pair[1])
      }

      // 使用原生fetch API，project_id作为query参数
      const token = localStorage.getItem('qunkong_token')
      const fetchResponse = await fetch(`/api/agents/batch-install?project_id=${projectId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
          // 不设置Content-Type，让浏览器自动添加boundary
        },
        body: formData
      })

      if (!fetchResponse.ok) {
        const errorData = await fetchResponse.json()
        throw new Error(JSON.stringify(errorData.detail || errorData))
      }

      const response = await fetchResponse.json()

      // 更新结果
      if (response && response.results) {
        const updatedResults = response.results.map(result => ({
          key: result.ip,
          username: result.username,
          ip: result.ip,
          port: result.port,
          status: result.success ? 'success' : 'failed',
          agent_id: result.agent_id || null,
          message: result.message || '',
        }))
        setResults(updatedResults)
        
        const successCount = updatedResults.filter(r => r.status === 'success').length
        message.success(`批量安装完成！成功: ${successCount}/${updatedResults.length}`)
      }

    } catch (error) {
      console.error('批量安装失败:', error)
      // 确保错误消息是字符串
      let errorMessage = '批量安装失败'
      if (error.response?.data) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail
        } else if (typeof error.response.data.detail === 'object') {
          // 如果detail是对象（比如验证错误），转换为字符串
          errorMessage = JSON.stringify(error.response.data.detail)
        } else if (error.response.data.message) {
          errorMessage = error.response.data.message
        }
      } else if (error.message) {
        errorMessage = error.message
      }
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleUploadChange = (info) => {
    if (info.file.status === 'done') {
      setSshKey(info.file.originFileObj)
      message.success('SSH密钥上传成功')
    } else if (info.file.status === 'error') {
      message.error('SSH密钥上传失败')
    }
  }

  const beforeUpload = (file) => {
    // 不自动上传，只保存文件对象
    setSshKey(file)
    return false
  }

  // 权限检查 - 在所有Hooks之后进行
  if (permissionLoading) {
    return <div style={{ padding: 24 }}>加载中...</div>
  }

  if (!hasPermission('agent.batch_add')) {
    return (
      <div style={{ padding: 24 }}>
        <Result
          status="403"
          title="权限不足"
          subTitle="您没有批量添加主机的权限，请联系项目管理员为您开启此权限。"
          icon={<LockOutlined />}
        />
      </div>
    )
  }

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title="批量添加主机"
        variant="borderless"
        tabList={[
          { key: 'install', tab: '添加主机' },
          { key: 'history', tab: '历史记录' },
        ]}
        activeTabKey={activeTab}
        onTabChange={setActiveTab}
      >
        {activeTab === 'install' && (
          <>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{
                auth_type: 'password',
              }}
            >
              <Form.Item
                label="认证方式"
                name="auth_type"
                rules={[{ required: true, message: '请选择认证方式' }]}
              >
                <Radio.Group onChange={(e) => setAuthType(e.target.value)}>
                  <Radio value="password">密码认证</Radio>
                  <Radio value="key">密钥认证</Radio>
                </Radio.Group>
              </Form.Item>

              {authType === 'key' && (
                <Form.Item
                  label="SSH私钥文件"
                  extra="请上传SSH私钥文件（id_rsa）"
                >
                  <Upload
                    beforeUpload={beforeUpload}
                    onChange={handleUploadChange}
                    maxCount={1}
                    accept=".pem,.key,id_rsa"
                  >
                    <Button icon={<UploadOutlined />}>选择SSH密钥文件</Button>
                  </Upload>
                </Form.Item>
              )}

              <Form.Item
                label="主机列表"
                name="hosts"
                rules={[{ required: true, message: '请输入主机列表' }]}
                extra={
                  authType === 'password'
                    ? '每行一个主机，格式：用户名|IP地址|端口|密码，例如：root|192.168.1.100|22|yourpassword'
                    : '每行一个主机，格式：用户名|IP地址|端口，例如：root|192.168.1.100|22'
                }
              >
                <TextArea
                  rows={8}
                  placeholder={
                    authType === 'password'
                      ? 'root|192.168.1.100|22|password123\nroot|192.168.1.101|22|password456'
                      : 'root|192.168.1.100|22\nroot|192.168.1.101|22'
                  }
                />
              </Form.Item>

              <Form.Item
                label="Agent下载URL"
                name="agent_download_url"
                rules={[{ required: true, message: '请输入Agent下载URL' }]}
                extra="指定qunkong-agent程序的下载地址"
              >
                <Input
                  placeholder="例如：http://your-server.com/downloads/qunkong-agent-latest"
                />
              </Form.Item>

              <Form.Item
                label="Agent MD5校验值"
                name="agent_md5"
                rules={[{ required: true, message: '请输入Agent的MD5校验值' }]}
                extra="用于验证下载的Agent程序完整性"
              >
                <Input
                  placeholder="例如：d41d8cd98f00b204e9800998ecf8427e"
                />
              </Form.Item>

              <Form.Item
                label="Server URL（可选）"
                name="server_url"
                extra="Agent注册的服务器地址（-s参数），不填则使用默认配置"
              >
                <Input
                  placeholder="例如：http://your-qunkong-server.com:8000"
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={loading} icon={<PlusOutlined />}>
                    开始批量安装
                  </Button>
                  <Button onClick={() => form.resetFields()}>
                    重置
                  </Button>
                </Space>
              </Form.Item>
            </Form>

            {results.length > 0 && (
              <>
                <Divider>安装结果</Divider>
                <Table
                  columns={columns}
                  dataSource={results}
                  pagination={false}
                  size="middle"
                />
              </>
            )}
          </>
        )}

        {activeTab === 'history' && (
          <Table
            columns={historyColumns}
            dataSource={history}
            rowKey="id"
            loading={historyLoading}
            pagination={{ pageSize: 20 }}
            scroll={{ x: 1200 }}
          />
        )}
      </Card>
    </div>
  )
}

export default BatchAddAgent