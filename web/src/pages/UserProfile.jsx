import React, { useState, useEffect } from 'react'
import { Card, Form, Input, Button, message, Tabs } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '../utils/api'

const UserProfile = () => {
  const [profileForm] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = () => {
    const userStr = localStorage.getItem('qunkong_user')
    if (userStr) {
      try {
        const user = JSON.parse(userStr)
        setCurrentUser(user)
        profileForm.setFieldsValue({
          username: user.username,
          email: user.email
        })
      } catch (error) {
        console.error('解析用户信息失败:', error)
      }
    }
  }

  const handleChangePassword = async (values) => {
    try {
      setLoading(true)
      await authApi.changePassword({
        old_password: values.oldPassword,
        new_password: values.newPassword
      })
      message.success('密码修改成功，请重新登录')
      passwordForm.resetFields()
      
      setTimeout(() => {
        localStorage.removeItem('qunkong_token')
        localStorage.removeItem('qunkong_user')
        window.location.href = '/login'
      }, 1500)
    } catch (error) {
      message.error(error.response?.data?.error || '密码修改失败')
    } finally {
      setLoading(false)
    }
  }

  const items = [
    {
      key: 'profile',
      label: '基本信息',
      icon: <UserOutlined />,
      children: (
        <Card>
          <Form
            form={profileForm}
            layout="vertical"
            style={{ maxWidth: 600 }}
          >
            <Form.Item label="用户名" name="username">
              <Input disabled />
            </Form.Item>

            <Form.Item label="邮箱" name="email">
              <Input disabled />
            </Form.Item>

            <Form.Item label="角色">
              <Input value={currentUser?.role} disabled />
            </Form.Item>
          </Form>
        </Card>
      )
    },
    {
      key: 'password',
      label: '修改密码',
      icon: <LockOutlined />,
      children: (
        <Card>
          <Form
            form={passwordForm}
            layout="vertical"
            onFinish={handleChangePassword}
            style={{ maxWidth: 600 }}
          >
            <Form.Item
              label="旧密码"
              name="oldPassword"
              rules={[{ required: true, message: '请输入旧密码' }]}
            >
              <Input.Password />
            </Form.Item>

            <Form.Item
              label="新密码"
              name="newPassword"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 6, message: '密码长度不能少于 6 个字符' }
              ]}
            >
              <Input.Password />
            </Form.Item>

            <Form.Item
              label="确认密码"
              name="confirmPassword"
              dependencies={['newPassword']}
              rules={[
                { required: true, message: '请再次输入新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('newPassword') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  }
                })
              ]}
            >
              <Input.Password />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading}>
                修改密码
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card title="个人设置">
        <Tabs items={items} />
      </Card>
    </div>
  )
}

export default UserProfile

