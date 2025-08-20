/**
 * 用户权限管理工具
 * Phase 2 - 权限控制优化
 */

import { stateManager } from '../store'

export interface Permission {
  id: string
  name: string
  description: string
  adminOnly: boolean
}

export const PERMISSIONS: Record<string, Permission> = {
  // 基础权限
  VIEW_PROFILE: {
    id: 'view_profile',
    name: '查看个人资料',
    description: '查看自己的用户信息和统计数据',
    adminOnly: false
  },
  
  MANAGE_ORDERS: {
    id: 'manage_orders',
    name: '管理订单',
    description: '创建、修改、取消个人订单',
    adminOnly: false
  },
  
  VIEW_BALANCE: {
    id: 'view_balance',
    name: '查看余额',
    description: '查看个人余额和变动历史',
    adminOnly: false
  },
  
  // 管理员权限
  ADMIN_MANAGE_MEALS: {
    id: 'admin_manage_meals',
    name: '管理餐次',
    description: '发布、编辑、锁定、取消餐次',
    adminOnly: true
  },
  
  ADMIN_MANAGE_USERS: {
    id: 'admin_manage_users',
    name: '管理用户',
    description: '查看用户列表、充值用户余额',
    adminOnly: true
  },
  
  ADMIN_VIEW_LOGS: {
    id: 'admin_view_logs',
    name: '查看日志',
    description: '查看系统操作日志',
    adminOnly: true
  },
  
  ADMIN_EXPORT_DATA: {
    id: 'admin_export_data',
    name: '导出数据',
    description: '导出餐次订单、用户数据等',
    adminOnly: true
  },
  
  ADMIN_SYSTEM_CONFIG: {
    id: 'admin_system_config',
    name: '系统配置',
    description: '修改系统配置参数',
    adminOnly: true
  }
}

/**
 * 权限管理器
 */
export class PermissionManager {
  /**
   * 检查用户是否有指定权限
   */
  static hasPermission(permissionId: string): boolean {
    const permission = PERMISSIONS[permissionId]
    if (!permission) {
      console.warn(`Unknown permission: ${permissionId}`)
      return false
    }

    // 非管理员权限，所有用户都有
    if (!permission.adminOnly) {
      return true
    }

    // 管理员权限，需要检查用户状态
    const isAdmin = stateManager.getState<boolean>('user.isAdmin')
    const adminViewEnabled = stateManager.getState<boolean>('app.adminViewEnabled')
    
    return isAdmin && adminViewEnabled
  }

  /**
   * 检查用户是否是管理员
   */
  static isAdmin(): boolean {
    return stateManager.getState<boolean>('user.isAdmin')
  }

  /**
   * 检查管理员视图是否启用
   */
  static isAdminViewEnabled(): boolean {
    return stateManager.getState<boolean>('app.adminViewEnabled')
  }

  /**
   * 检查用户是否有管理员权限（管理员且启用了管理视图）
   */
  static hasAdminAccess(): boolean {
    return this.isAdmin() && this.isAdminViewEnabled()
  }

  /**
   * 获取用户的所有权限
   */
  static getUserPermissions(): Permission[] {
    const isAdmin = this.hasAdminAccess()
    
    return Object.values(PERMISSIONS).filter(permission => {
      if (permission.adminOnly) {
        return isAdmin
      }
      return true
    })
  }

  /**
   * 权限守卫 - 检查权限并处理无权限情况
   */
  static guardPermission(permissionId: string, options?: {
    showError?: boolean
    errorMessage?: string
    redirectOnError?: string
  }): boolean {
    const hasPermission = this.hasPermission(permissionId)
    
    if (!hasPermission) {
      const opts = {
        showError: true,
        errorMessage: '您没有权限执行此操作',
        ...options
      }
      
      if (opts.showError) {
        wx.showToast({
          title: opts.errorMessage,
          icon: 'error',
          duration: 2000
        })
      }
      
      if (opts.redirectOnError) {
        wx.redirectTo({
          url: opts.redirectOnError
        })
      }
    }
    
    return hasPermission
  }

  /**
   * 管理员权限守卫
   */
  static guardAdminPermission(options?: {
    showError?: boolean
    errorMessage?: string
    redirectOnError?: string
  }): boolean {
    const hasAccess = this.hasAdminAccess()
    
    if (!hasAccess) {
      const opts = {
        showError: true,
        errorMessage: '需要管理员权限',
        ...options
      }
      
      if (opts.showError) {
        wx.showToast({
          title: opts.errorMessage,
          icon: 'error',
          duration: 2000
        })
      }
      
      if (opts.redirectOnError) {
        wx.redirectTo({
          url: opts.redirectOnError
        })
      }
    }
    
    return hasAccess
  }

  /**
   * 功能可用性检查（不弹出错误提示）
   */
  static canUseFeature(permissionId: string): boolean {
    return this.hasPermission(permissionId)
  }

  /**
   * 获取权限描述文本
   */
  static getPermissionDescription(permissionId: string): string {
    const permission = PERMISSIONS[permissionId]
    return permission ? permission.description : '未知权限'
  }
}

/**
 * 权限装饰器 - 用于页面方法的权限控制
 */
export function requirePermission(permissionId: string, options?: {
  errorMessage?: string
  redirectOnError?: string
}) {
  return function(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value
    
    descriptor.value = function(...args: any[]) {
      if (PermissionManager.guardPermission(permissionId, options)) {
        return originalMethod.apply(this, args)
      }
    }
    
    return descriptor
  }
}

/**
 * 管理员权限装饰器
 */
export function requireAdmin(options?: {
  errorMessage?: string
  redirectOnError?: string
}) {
  return function(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value
    
    descriptor.value = function(...args: any[]) {
      if (PermissionManager.guardAdminPermission(options)) {
        return originalMethod.apply(this, args)
      }
    }
    
    return descriptor
  }
}

/**
 * 便捷的权限检查函数
 */
export const checkPermission = PermissionManager.hasPermission.bind(PermissionManager)
export const checkAdmin = PermissionManager.hasAdminAccess.bind(PermissionManager)
export const guardPermission = PermissionManager.guardPermission.bind(PermissionManager)
export const guardAdmin = PermissionManager.guardAdminPermission.bind(PermissionManager)

export default PermissionManager