import { useState, useEffect, useCallback, useRef } from 'react'
import { projectsApi } from '../utils/api'

// 全局权限缓存（避免多个组件重复请求）
const permissionCache = {
  data: null,
  projectId: null,
  userId: null,
  timestamp: 0,
  loading: false,
  subscribers: new Set(),
  TTL: 60000, // 缓存有效期60秒
}

// 检查缓存是否有效
const isCacheValid = (projectId, userId) => {
  const now = Date.now()
  return (
    permissionCache.data !== null &&
    permissionCache.projectId === projectId &&
    permissionCache.userId === userId &&
    now - permissionCache.timestamp < permissionCache.TTL
  )
}

// 通知所有订阅者
const notifySubscribers = () => {
  permissionCache.subscribers.forEach(callback => callback())
}

/**
 * 权限管理Hook（带缓存优化）
 * 用于检查用户是否拥有特定权限
 */
export const usePermissions = () => {
  const [permissions, setPermissions] = useState(permissionCache.data?.permissions || [])
  const [loading, setLoading] = useState(!permissionCache.data)
  const [isAdmin, setIsAdmin] = useState(permissionCache.data?.isAdmin || false)
  const mountedRef = useRef(true)

  // 加载用户权限
  const loadPermissions = useCallback(async (force = false) => {
    // 获取当前用户信息
    const userStr = localStorage.getItem('qunkong_user')
    const projectStr = localStorage.getItem('qunkong_current_project')
    
    if (!userStr || !projectStr) {
      setPermissions([])
      setIsAdmin(false)
      setLoading(false)
      return
    }

    const user = JSON.parse(userStr)
    const project = JSON.parse(projectStr)

    // 检查缓存是否有效
    if (!force && isCacheValid(project.id, user.user_id)) {
      // 使用缓存数据
      setPermissions(permissionCache.data.permissions)
      setIsAdmin(permissionCache.data.isAdmin)
      setLoading(false)
      return
    }

    // 如果另一个组件正在请求，等待它完成
    if (permissionCache.loading) {
      return
    }

    try {
      permissionCache.loading = true
      setLoading(true)

      // 检查是否是系统管理员
      const adminRole = ['admin', 'super_admin'].includes(user.role)

      let perms = []
      if (adminRole) {
        perms = ['*'] // 通配符表示所有权限
      } else {
        // 获取项目中的用户权限
        const response = await projectsApi.getUserPermissions(project.id, user.user_id)
        perms = response.permissions || []
      }

      // 更新缓存
      permissionCache.data = {
        permissions: perms,
        isAdmin: adminRole,
      }
      permissionCache.projectId = project.id
      permissionCache.userId = user.user_id
      permissionCache.timestamp = Date.now()

      // 更新本组件状态
      if (mountedRef.current) {
        setPermissions(perms)
        setIsAdmin(adminRole)
      }

      // 通知其他订阅者
      notifySubscribers()
      
    } catch (error) {
      console.error('加载权限失败:', error)
      if (mountedRef.current) {
        setPermissions([])
        setIsAdmin(false)
      }
    } finally {
      permissionCache.loading = false
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  // 订阅缓存更新
  useEffect(() => {
    mountedRef.current = true

    const handleCacheUpdate = () => {
      if (permissionCache.data && mountedRef.current) {
        setPermissions(permissionCache.data.permissions)
        setIsAdmin(permissionCache.data.isAdmin)
        setLoading(false)
      }
    }

    permissionCache.subscribers.add(handleCacheUpdate)
    
    // 初始加载
    loadPermissions()

    return () => {
      mountedRef.current = false
      permissionCache.subscribers.delete(handleCacheUpdate)
    }
  }, [loadPermissions])

  // 检查是否有指定权限
  const hasPermission = useCallback((permissionKey) => {
    if (!permissionKey) return true
    
    // 系统管理员拥有所有权限
    if (isAdmin || permissions.includes('*')) {
      return true
    }

    // 检查是否有该权限
    return permissions.includes(permissionKey)
  }, [permissions, isAdmin])

  // 检查是否有任意一个权限
  const hasAnyPermission = useCallback((permissionKeys) => {
    if (!permissionKeys || permissionKeys.length === 0) return true
    
    if (isAdmin || permissions.includes('*')) {
      return true
    }

    return permissionKeys.some(key => permissions.includes(key))
  }, [permissions, isAdmin])

  // 检查是否拥有所有权限
  const hasAllPermissions = useCallback((permissionKeys) => {
    if (!permissionKeys || permissionKeys.length === 0) return true
    
    if (isAdmin || permissions.includes('*')) {
      return true
    }

    return permissionKeys.every(key => permissions.includes(key))
  }, [permissions, isAdmin])

  // 强制刷新权限
  const reload = useCallback(() => {
    // 清除缓存
    permissionCache.data = null
    permissionCache.timestamp = 0
    loadPermissions(true)
  }, [loadPermissions])

  return {
    permissions,
    loading,
    isAdmin,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    reload,
  }
}

/**
 * 清除权限缓存（在登出或切换项目时调用）
 */
export const clearPermissionCache = () => {
  permissionCache.data = null
  permissionCache.projectId = null
  permissionCache.userId = null
  permissionCache.timestamp = 0
  permissionCache.loading = false
}

/**
 * 权限组件 - 根据权限显示/隐藏子组件
 */
export const PermissionGate = ({ permission, permissions, requireAll = false, fallback = null, children }) => {
  const { hasPermission, hasAnyPermission, hasAllPermissions, loading } = usePermissions()

  if (loading) {
    return null // 或者返回加载指示器
  }

  let allowed = false

  if (permission) {
    // 单个权限检查
    allowed = hasPermission(permission)
  } else if (permissions) {
    // 多个权限检查
    allowed = requireAll 
      ? hasAllPermissions(permissions)
      : hasAnyPermission(permissions)
  } else {
    // 没有指定权限,默认允许
    allowed = true
  }

  return allowed ? children : fallback
}

export default usePermissions
