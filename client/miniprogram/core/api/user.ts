/**
 * 用户相关API - Phase 2增强版
 */

import { httpClient } from './base'
import { API_ENDPOINTS } from '../constants'

// 类型定义
export interface UserProfileSummary {
  user_info: {
    user_id: number
    openid: string
    nickname?: string
    avatar_url?: string
    balance_cents: number
    is_admin: boolean
    created_at: string
  }
  recent_activity: {
    recent_orders: number
    recent_spent_cents: number
    recent_meal_days: number
  }
  lifetime_stats: {
    total_orders: number
    total_spent_cents: number
  }
}

export interface OrderHistoryItem {
  order_id: number
  meal_id: number
  quantity: number
  selected_options: any[]
  total_price_cents: number
  order_status: string
  order_time: string
  meal_date: string
  meal_slot: string
  meal_description: string
  meal_status: string
}

export interface OrderHistoryResponse {
  orders: OrderHistoryItem[]
  total_count: number
  page_info: {
    limit: number
    offset: number
    has_more: boolean
  }
  statistics: {
    general: {
      total_orders: number
      total_spent_cents: number
      total_meals: number
      total_days: number
    }
    by_status: Array<{
      status: string
      count: number
      total_cents: number
    }>
    by_slot: Array<{
      slot: string
      count: number
      total_cents: number
    }>
    recent_trend: Array<{
      date: string
      orders_count: number
      daily_spent_cents: number
    }>
  }
}

export interface BalanceHistoryItem {
  ledger_id: number
  user_id: number
  amount_cents: number
  description: string
  related_order_id?: number
  created_at: string
  balance_after_cents: number
}

export interface BalanceHistoryResponse {
  history: BalanceHistoryItem[]
  total_count: number
  page_info: {
    limit: number
    offset: number
    has_more: boolean
  }
}

export interface OrderHistoryParams {
  start_date?: string
  end_date?: string
  status?: string
  limit?: number
  offset?: number
}

export interface BalanceHistoryParams {
  limit?: number
  offset?: number
}

/**
 * 用户API类
 */
export class UserAPI {
  /**
   * 获取用户资料摘要
   */
  static async getUserProfile(): Promise<{ success: boolean; data?: UserProfileSummary; message?: string }> {
    try {
      const response = await httpClient.get<UserProfileSummary>(
        API_ENDPOINTS.USER_PROFILE_SUMMARY,
        {
          showLoading: true,
          cacheDuration: 2 * 60 * 1000, // 2分钟缓存
          retryConfig: {
            maxAttempts: 2,
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('获取用户资料失败:', error)
      return { 
        success: false, 
        message: error?.message || '获取用户资料失败' 
      }
    }
  }

  /**
   * 获取用户订单历史
   */
  static async getOrderHistory(params: OrderHistoryParams = {}): Promise<{ success: boolean; data?: OrderHistoryResponse; message?: string }> {
    try {
      const queryParams = new URLSearchParams()
      
      if (params.start_date) queryParams.append('start_date', params.start_date)
      if (params.end_date) queryParams.append('end_date', params.end_date)
      if (params.status) queryParams.append('status', params.status)
      if (params.limit) queryParams.append('limit', params.limit.toString())
      if (params.offset) queryParams.append('offset', params.offset.toString())

      const url = `${API_ENDPOINTS.USER_ORDER_HISTORY}?${queryParams.toString()}`

      const response = await httpClient.get<OrderHistoryResponse>(
        url,
        {
          showLoading: params.offset === 0, // 只在首次加载时显示loading
          cacheDuration: 1 * 60 * 1000, // 1分钟缓存
          retryConfig: {
            maxAttempts: 2,
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('获取订单历史失败:', error)
      return { 
        success: false, 
        message: error?.message || '获取订单历史失败' 
      }
    }
  }

  /**
   * 获取余额变动历史
   */
  static async getBalanceHistory(params: BalanceHistoryParams = {}): Promise<{ success: boolean; data?: BalanceHistoryResponse; message?: string }> {
    try {
      const queryParams = new URLSearchParams()
      
      if (params.limit) queryParams.append('limit', params.limit.toString())
      if (params.offset) queryParams.append('offset', params.offset.toString())

      const url = `${API_ENDPOINTS.USER_BALANCE_HISTORY}?${queryParams.toString()}`

      const response = await httpClient.get<BalanceHistoryResponse>(
        url,
        {
          showLoading: params.offset === 0, // 只在首次加载时显示loading
          cacheDuration: 30 * 1000, // 30秒缓存
          retryConfig: {
            maxAttempts: 2,
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('获取余额历史失败:', error)
      return { 
        success: false, 
        message: error?.message || '获取余额历史失败' 
      }
    }
  }

  /**
   * 管理员充值用户余额
   */
  static async rechargeBalance(
    userId: number, 
    amountCents: number
  ): Promise<{ success: boolean; data?: any; message?: string }> {
    try {
      const response = await httpClient.post(
        API_ENDPOINTS.USER_BALANCE_RECHARGE,
        {
          user_id: userId,
          amount_cents: amountCents
        },
        {
          showLoading: true,
          retryConfig: {
            maxAttempts: 1, // 充值操作不重试，避免重复扣费
            baseDelay: 1000,
            maxDelay: 3000,
            backoffFactor: 2,
            retryableErrors: ['timeout', 'NETWORK_ERROR']
          }
        }
      )

      return { success: true, data: response }
    } catch (error) {
      console.error('充值失败:', error)
      return { 
        success: false, 
        message: error?.message || '充值失败' 
      }
    }
  }

  /**
   * 导出订单历史
   */
  static async exportOrderHistory(): Promise<{ success: boolean; message?: string }> {
    try {
      // 这里应该调用导出API，返回文件或链接
      // 由于小程序限制，可能需要服务端生成导出文件
      wx.showToast({
        title: '导出功能开发中',
        icon: 'none',
        duration: 2000
      })

      return { success: true }
    } catch (error) {
      console.error('导出订单历史失败:', error)
      return { 
        success: false, 
        message: error?.message || '导出失败' 
      }
    }
  }

  /**
   * 导出余额历史
   */
  static async exportBalanceHistory(): Promise<{ success: boolean; message?: string }> {
    try {
      // 这里应该调用导出API，返回文件或链接
      wx.showToast({
        title: '导出功能开发中',
        icon: 'none',
        duration: 2000
      })

      return { success: true }
    } catch (error) {
      console.error('导出余额历史失败:', error)
      return { 
        success: false, 
        message: error?.message || '导出失败' 
      }
    }
  }
}

export default UserAPI