/**
 * 管理员API - 支持透支功能和用户管理
 */

import { httpClient } from './base'
import { API_ENDPOINTS } from '../constants'

// 类型定义
export interface AdminUser {
  user_id: number
  openid: string
  nickname?: string
  balance_cents: number
  is_admin: boolean
  overdraft_status?: string
  total_orders: number
  total_spent_cents: number
  created_at: string
  last_active: string
}

export interface AdminUsersResponse {
  users: AdminUser[]
  total_count: number
  statistics: {
    total_users: number
    active_users: number
    users_in_overdraft: number
    total_overdraft_amount_cents: number
  }
}

export interface SystemStats {
  user_stats: {
    total_users: number
    active_users: number
    admin_users: number
    users_in_overdraft: number
  }
  financial_stats: {
    total_balance_cents: number
    total_overdraft_cents: number
    total_transactions_today: number
    total_revenue_today_cents: number
  }
  order_stats: {
    total_orders: number
    orders_today: number
    active_orders: number
    completed_orders_today: number
  }
  meal_stats: {
    meals_published: number
    meals_locked: number
    meals_today: number
  }
}

export interface BalanceAdjustRequest {
  user_id: number
  amount_cents: number
  reason: string
}

export interface BalanceAdjustResponse {
  user_id: number
  old_balance_cents: number
  adjustment_cents: number
  new_balance_cents: number
  overdraft_status?: string
  ledger_id: number
  reason: string
}

export interface TransactionRecord {
  ledger_id: number
  user_id: number
  type: string
  amount_cents: number
  balance_after_cents: number
  ref_type?: string
  ref_id?: number
  remark: string
  created_at: string
}

export interface TransactionsResponse {
  transactions: TransactionRecord[]
  total_count: number
  statistics: {
    total_debits_cents: number
    total_credits_cents: number
    net_flow_cents: number
    overdraft_transactions: number
  }
}

/**
 * 管理员API类
 */
export class AdminAPI {
  /**
   * 获取所有用户列表（管理员）
   */
  static async getAllUsers(): Promise<{ success: boolean; data?: AdminUsersResponse; message?: string }> {
    try {
      const response = await httpClient.get<AdminUsersResponse>(
        API_ENDPOINTS.ADMIN_USERS,
        {
          showLoading: true,
          cacheDuration: 30 * 1000, // 30秒缓存
          retryConfig: {
            maxAttempts: 2,
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('获取用户列表失败:', error)
      return { 
        success: false, 
        message: error?.message || '获取用户列表失败' 
      }
    }
  }

  /**
   * 获取系统统计数据（管理员）
   */
  static async getSystemStats(): Promise<{ success: boolean; data?: SystemStats; message?: string }> {
    try {
      const response = await httpClient.get<SystemStats>(
        API_ENDPOINTS.ADMIN_STATS,
        {
          showLoading: true,
          cacheDuration: 60 * 1000, // 1分钟缓存
          retryConfig: {
            maxAttempts: 2,
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('获取系统统计失败:', error)
      return { 
        success: false, 
        message: error?.message || '获取系统统计失败' 
      }
    }
  }

  /**
   * 管理员调整用户余额（透支功能核心API）
   */
  static async adjustUserBalance(
    request: BalanceAdjustRequest
  ): Promise<{ success: boolean; data?: BalanceAdjustResponse; message?: string }> {
    try {
      const response = await httpClient.post<BalanceAdjustResponse>(
        API_ENDPOINTS.ADMIN_BALANCE_ADJUST,
        request,
        {
          showLoading: true,
          retryConfig: {
            maxAttempts: 1, // 余额调整不重试，避免重复操作
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('调整余额失败:', error)
      return { 
        success: false, 
        message: error?.message || '调整余额失败' 
      }
    }
  }

  /**
   * 获取所有用户的余额交易记录（管理员）
   */
  static async getTransactions(params?: {
    user_id?: number
    type?: string
    limit?: number
    offset?: number
  }): Promise<{ success: boolean; data?: TransactionsResponse; message?: string }> {
    try {
      const queryParams = new URLSearchParams()
      
      if (params?.user_id) queryParams.append('user_id', params.user_id.toString())
      if (params?.type) queryParams.append('type', params.type)
      if (params?.limit) queryParams.append('limit', params.limit.toString())
      if (params?.offset) queryParams.append('offset', params.offset.toString())

      const url = `${API_ENDPOINTS.ADMIN_BALANCE_TRANSACTIONS}?${queryParams.toString()}`

      const response = await httpClient.get<TransactionsResponse>(
        url,
        {
          showLoading: params?.offset === 0,
          cacheDuration: 30 * 1000, // 30秒缓存
          retryConfig: {
            maxAttempts: 2,
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('获取交易记录失败:', error)
      return { 
        success: false, 
        message: error?.message || '获取交易记录失败' 
      }
    }
  }

  /**
   * 透支用户快速充值
   */
  static async overdraftUserRecharge(
    userId: number,
    amountCents: number
  ): Promise<{ success: boolean; data?: BalanceAdjustResponse; message?: string }> {
    return this.adjustUserBalance({
      user_id: userId,
      amount_cents: amountCents,
      reason: `管理员为透支用户充值 ${amountCents / 100} 元`
    })
  }

  /**
   * 获取透支用户列表
   */
  static async getOverdraftUsers(): Promise<{ success: boolean; data?: AdminUser[]; message?: string }> {
    try {
      const response = await this.getAllUsers()
      
      if (response.success && response.data) {
        // 筛选出透支用户
        const overdraftUsers = response.data.users.filter(user => user.balance_cents < 0)
        return { 
          success: true, 
          data: overdraftUsers 
        }
      }

      return response
    } catch (error) {
      console.error('获取透支用户失败:', error)
      return { 
        success: false, 
        message: error?.message || '获取透支用户失败' 
      }
    }
  }
}

export default AdminAPI