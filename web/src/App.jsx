import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Input, Dropdown, Avatar, Space, message } from 'antd'
import {
  UserOutlined,
  LockOutlined,
  LogoutOutlined,
  DownOutlined,
  SearchOutlined,
  BankOutlined,
  FileTextOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  DesktopOutlined
} from '@ant-design/icons'
import { authApi, setPermissionCacheClearer } from './utils/api'
import { clearPermissionCache } from './hooks/usePermissions'

// 注册权限缓存清除器到 API 模块（避免循环依赖）
setPermissionCacheClearer(clearPermissionCache)
import Login from './pages/Login'
import ProjectSelector from './pages/ProjectSelector'
import ScriptExecution from './pages/ScriptExecution'
import ExecutionHistory from './pages/ExecutionHistory'
import JobExecutionDetail from './pages/JobExecutionDetail'
import AgentManagement from './pages/AgentManagement'
import BatchAddAgent from './pages/BatchAddAgent'
import SimpleJobs from './pages/SimpleJobs'
import Terminal from './pages/Terminal'
import UserManagement from './pages/UserManagement'
import ProjectManagement from './pages/ProjectManagement'
import UserProfile from './pages/UserProfile'
import './App.css'

const { Header, Sider, Content } = Layout

// 路由守卫组件
const ProtectedRoute = ({ children, requiresProject = true }) => {
  const navigate = useNavigate()
  const token = localStorage.getItem('qunkong_token')
  const currentProject = localStorage.getItem('qunkong_current_project')

  useEffect(() => {
    if (!token) {
      message.warning('请先登录')
      navigate('/login')
      return
    }
    
    if (requiresProject && !currentProject) {
      message.warning('请先选择项目')
      navigate('/select-project')
    }
  }, [token, currentProject, requiresProject, navigate])

  if (!token) return null
  if (requiresProject && !currentProject) return null

  return children
}

// 主布局组件
const MainLayout = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [currentUser, setCurrentUser] = useState(null)
  const [currentProject, setCurrentProject] = useState(null)
  const [searchKeyword, setSearchKeyword] = useState('')

  useEffect(() => {
    loadUserInfo()
  }, [location.pathname])

  const loadUserInfo = () => {
    const userStr = localStorage.getItem('qunkong_user')
    if (userStr) {
      try {
        setCurrentUser(JSON.parse(userStr))
      } catch (error) {
        console.error('解析用户信息失败:', error)
      }
    }
    
    const projectStr = localStorage.getItem('qunkong_current_project')
    if (projectStr) {
      try {
        setCurrentProject(JSON.parse(projectStr))
      } catch (error) {
        console.error('解析项目信息失败:', error)
      }
    }
  }

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('登出失败:', error)
    }

    // 清除所有本地存储和缓存
    localStorage.removeItem('qunkong_token')
    localStorage.removeItem('qunkong_user')
    localStorage.removeItem('qunkong_remember')
    clearPermissionCache()  // 清除权限缓存
    message.success('已退出登录')
    navigate('/login')
  }

  const switchProject = () => {
    localStorage.removeItem('qunkong_current_project')
    clearPermissionCache()  // 切换项目时清除权限缓存
    navigate('/select-project')
  }

  const isAdmin = currentUser && ['admin', 'super_admin'].includes(currentUser.role)
  const isProjectAdmin = currentProject && currentProject.role === 'admin'

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人设置',
      onClick: () => navigate('/profile')
    },
    {
      key: 'changePassword',
      icon: <LockOutlined />,
      label: '修改密码',
      onClick: () => navigate('/profile')
    },
    {
      type: 'divider'
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout
    }
  ]

  const menuItems = [
    {
      key: 'quick',
      label: '快速执行',
      type: 'group',
      children: [
        {
          key: '/script-execution',
          icon: <FileTextOutlined />,
          label: '脚本执行'
        }
      ]
    },
    {
      key: 'task',
      label: '任务编排',
      type: 'group',
      children: [
        {
          key: '/jobs',
          icon: <SettingOutlined />,
          label: '作业'
        },
        {
          key: '/execution-history',
          icon: <ClockCircleOutlined />,
          label: '执行历史'
        }
      ]
    },
    {
      key: 'node',
      label: '节点管理',
      type: 'group',
      children: [
        {
          key: '/agent-management',
          icon: <DesktopOutlined />,
          label: 'Agent管理'
        },
        {
          key: '/batch-add-agent',
          icon: <DesktopOutlined />,
          label: '批量添加主机'
        }
      ]
    },
    ...(isAdmin ? [{
      key: 'system',
      label: '系统管理',
      type: 'group',
      children: [
        {
          key: '/user-management',
          icon: <UserOutlined />,
          label: '用户管理'
        },
        {
          key: '/project-management',
          icon: <BankOutlined />,
          label: '项目管理'
        }
      ]
    }] : []),
    ...(!isAdmin && isProjectAdmin ? [{
      key: 'project-admin',
      label: '项目管理',
      type: 'group',
      children: [
        {
          key: '/project-management',
          icon: <BankOutlined />,
          label: '项目管理'
        }
      ]
    }] : [])
  ]

  return (
    <Layout style={{ height: '100vh' }}>
      <Header className="header">
        <div className="header-left">
          <div className="logo-container">
            <img src="/logo.svg" alt="Qunkong" className="logo" />
            <span className="title">Qunkong</span>
          </div>
        </div>
        <div className="header-center">
          <Input
            placeholder="搜索功能..."
            prefix={<SearchOutlined />}
            value={searchKeyword}
            onChange={e => setSearchKeyword(e.target.value)}
            style={{ width: 200 }}
          />
        </div>
        <div className="header-right">
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" trigger={['click']}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <span>{currentUser?.username || currentUser?.email || '未登录'}</span>
              <DownOutlined />
            </Space>
          </Dropdown>
        </div>
      </Header>
      <Layout>
        <Sider width={240} className="sidebar">
          {currentProject && (
            <div className="current-project-sidebar" onClick={switchProject}>
              <BankOutlined />
              <div className="project-info">
                <div className="project-name">{currentProject.project_name}</div>
                <div className="project-code">{currentProject.project_code}</div>
              </div>
              <DownOutlined className="switch-icon" />
            </div>
          )}
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <Content className="main-content">
          <Routes>
            <Route path="/script-execution" element={<ProtectedRoute><ScriptExecution /></ProtectedRoute>} />
            <Route path="/execution-history" element={<ProtectedRoute><ExecutionHistory /></ProtectedRoute>} />
            <Route path="/execution-detail/:executionId" element={<ProtectedRoute><JobExecutionDetail /></ProtectedRoute>} />
            <Route path="/agent-management" element={<ProtectedRoute><AgentManagement /></ProtectedRoute>} />
            <Route path="/batch-add-agent" element={<ProtectedRoute><BatchAddAgent /></ProtectedRoute>} />
            <Route path="/jobs" element={<ProtectedRoute><SimpleJobs /></ProtectedRoute>} />
            <Route path="/user-management" element={<ProtectedRoute><UserManagement /></ProtectedRoute>} />
            <Route path="/project-management" element={<ProtectedRoute><ProjectManagement /></ProtectedRoute>} />
            <Route path="/profile" element={<ProtectedRoute requiresProject={false}><UserProfile /></ProtectedRoute>} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

// 根路由重定向组件
const RootRedirect = () => {
  const token = localStorage.getItem('qunkong_token')
  
  if (!token) {
    return <Navigate to="/login" replace />
  }
  
  return <Navigate to="/select-project" replace />
}

// 主应用
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/select-project" element={
          <ProtectedRoute requiresProject={false}>
            <ProjectSelector />
          </ProtectedRoute>
        } />
        <Route path="/terminal" element={
          <ProtectedRoute>
            <Terminal />
          </ProtectedRoute>
        } />
        <Route path="/terminal/:agentId" element={
          <ProtectedRoute>
            <Terminal />
          </ProtectedRoute>
        } />
        <Route path="/" element={<RootRedirect />} />
        <Route path="/*" element={<MainLayout />} />
      </Routes>
    </Router>
  )
}

export default App

