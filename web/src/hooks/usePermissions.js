import { useState, useEffect, useCallback } from 'react'
import { projectsApi } from '../utils/api'

/**
 * 权限管理Hook
 * 用于检查用户是否拥有特定权限
 */
export const usePermissions = () => {
  const [permissions, setPermissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)

  // 加载用户权限
  const loadPermissions = useCallback(async () => {
    try {
      setLoading(true)
      
      // 获取当前用户信息
      const userStr = localStorage.getItem('qunkong_user')
      const projectStr = localStorage.getItem('qunkong_current_project')
      
      if (!userStr || !projectStr) {
        setPermissions([])
        setIsAdmin(false)
        return
      }

      const user = JSON.parse(userStr)
      const project = JSON.parse(projectStr)

      // 检查是否是系统管理员
      const adminRole = ['admin', 'super_admin'].includes(user.role)
      setIsAdmin(adminRole)

      // 系统管理员拥有所有权限
      if (adminRole) {
        setPermissions(['*']) // 通配符表示所有权限
        return
      }

      // 获取项目中的用户权限
      const response = await projectsApi.getUserPermissions(project.id, user.user_id)
      setPermissions(response.permissions || [])
      
    } catch (error) {
      console.error('加载权限失败:', error)
      setPermissions([])
    } finally {
      setLoading(false)
    }
  }, [])

  // 组件挂载时加载权限
  useEffect(() => {
    loadPermissions()
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

  return {
    permissions,
    loading,
    isAdmin,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    reload: loadPermissions
  }
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