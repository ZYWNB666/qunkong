import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Checkbox, Modal, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '../utils/api'
import './Login.css'

const Login = () => {
  const navigate = useNavigate()
  const [loginForm] = Form.useForm()
  const [registerForm] = Form.useForm()
  const [loginLoading, setLoginLoading] = useState(false)
  const [registerLoading, setRegisterLoading] = useState(false)
  const [showRegisterModal, setShowRegisterModal] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('qunkong_token')
    if (token) {
      authApi.verifyToken()
        .then(() => navigate('/'))
        .catch(() => {
          localStorage.removeItem('qunkong_token')
          localStorage.removeItem('qunkong_user')
        })
    }
  }, [navigate])

  const handleLogin = async (values) => {
    try {
      setLoginLoading(true)
      const response = await authApi.login({
        username: values.username,
        password: values.password
      })

      localStorage.removeItem('qunkong_user')
      localStorage.removeItem('qunkong_current_project')
      
      localStorage.setItem('qunkong_token', response.token)
      localStorage.setItem('qunkong_user', JSON.stringify(response.user))

      if (values.remember) {
        localStorage.setItem('qunkong_remember', 'true')
      }

      message.success('登录成功')
      navigate('/')

    } catch (error) {
      message.error(error.response?.data?.error || '登录失败')
    } finally {
      setLoginLoading(false)
    }
  }

  const handleRegister = async (values) => {
    try {
      setRegisterLoading(true)
      await authApi.register({
        username: values.username,
        email: values.email,
        password: values.password,
        confirm_password: values.confirmPassword
      })

      message.success('注册成功，请登录')
      setShowRegisterModal(false)
      registerForm.resetFields()

    } catch (error) {
      message.error(error.response?.data?.error || '注册失败')
    } finally {
      setRegisterLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <div className="logo-container">
            <img src="/logo.svg" alt="Qunkong" className="logo" />
            <h1 className="title">Qunkong</h1>
          </div>
          <p className="subtitle">分布式脚本执行系统</p>
        </div>

        <Form
          form={loginForm}
          className="login-form"
          onFinish={handleLogin}
          autoComplete="off"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名或邮箱' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名或邮箱"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              size="large"
            />
          </Form.Item>

          <Form.Item>
            <div className="login-options">
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>记住我</Checkbox>
              </Form.Item>
              <a onClick={() => setShowRegisterModal(true)}>注册账号</a>
            </div>
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              loading={loginLoading}
              block
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="login-footer">
          <p>默认管理员账户: admin / admin123</p>
        </div>
      </div>

      <Modal
        title="注册账号"
        open={showRegisterModal}
        onCancel={() => setShowRegisterModal(false)}
        footer={null}
        width={400}
      >
        <Form
          form={registerForm}
          labelCol={{ span: 6 }}
          wrapperCol={{ span: 18 }}
          onFinish={handleRegister}
          autoComplete="off"
        >
          <Form.Item
            label="用户名"
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符' }
            ]}
          >
            <Input placeholder="请输入用户名" maxLength={20} />
          </Form.Item>

          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入正确的邮箱地址' }
            ]}
          >
            <Input type="email" placeholder="请输入邮箱地址" />
          </Form.Item>

          <Form.Item
            label="密码"
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码长度不能少于 6 个字符' }
            ]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>

          <Form.Item
            label="确认密码"
            name="confirmPassword"
            dependencies={['password']}
            rules={[
              { required: true, message: '请再次输入密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                }
              })
            ]}
          >
            <Input.Password placeholder="请再次输入密码" />
          </Form.Item>

          <Form.Item wrapperCol={{ offset: 6, span: 18 }}>
            <Button type="primary" htmlType="submit" loading={registerLoading} block>
              注册
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Login

