/**
 * 订单相关API接口封装
 * 提供类型安全的订单操作接口
 * 
 * 主要功能：
 * - 订单创建、修改和取消
 * - 统一的错误处理和类型定义
 * - 与后端API的一对一映射
 */

import { httpClient } from './base'
import { API_ENDPOINTS } from '../constants'

/**
 * 订单创建请求参数
 */
export interface CreateOrderRequest {
  /** 餐次ID */
  meal_id: number
  /** 订单数量 */
  qty: number
  /** 选择的配菜选项JSON字符串 */
  options_json: string
  /** 订单备注 */
  notes?: string
}

/**
 * 订单修改请求参数
 */
export interface UpdateOrderRequest {
  /** 订单数量 */
  qty: number
  /** 选择的配菜选项JSON字符串 */
  options_json: string
  /** 订单备注 */
  notes?: string
}

/**
 * 订单响应数据
 */
export interface OrderResponse {
  /** 订单ID */
  order_id: number
  /** 餐次ID */
  meal_id: number
  /** 用户ID */
  user_id: number
  /** 订单数量 */
  qty: number
  /** 订单金额（分） */
  amount_cents: number
  /** 用户余额（分）- 支持负数透支 */
  balance_cents: number
  /** 订单状态 */
  status: string
  /** 透支警告信息 */
  overdraft_warning?: string
  /** 创建时间 */
  created_at: string
}

/**
 * 订单取消响应数据
 */
export interface CancelOrderResponse {
  /** 订单ID */
  order_id: number
  /** 订单状态 */
  status: 'canceled'
  /** 退款金额（分） */
  refund_amount_cents: number
  /** 新的用户余额（分）- 支持负数 */
  new_balance_cents: number
  /** 取消时间 */
  canceled_at: string
}

/**
 * 订单API错误类型
 */
export interface OrderApiError {
  /** 错误代码 */
  code: string | number
  /** 错误消息 */
  message: string
  /** 详细信息 */
  detail?: any
}

/**
 * 订单API服务类
 * 封装所有订单相关的HTTP请求
 */
export class OrderApi {
  /**
   * 创建新订单
   * 
   * @param params 订单创建参数
   * @returns Promise<OrderResponse> 订单信息
   * @throws OrderApiError 当业务逻辑错误时
   */
  static async createOrder(params: CreateOrderRequest): Promise<OrderResponse> {
    return httpClient.post<OrderResponse>(API_ENDPOINTS.ORDER_CREATE, params, {
      retryConfig: {
        maxAttempts: 2, // 订单创建重试次数少，避免重复下单
        baseDelay: 1000,
        maxDelay: 3000,
        backoffFactor: 2,
        retryableErrors: ['timeout', 'NETWORK_ERROR'] // 不重试业务错误
      }
    })
  }

  /**
   * 修改订单
   * 实际上是取消旧订单并创建新订单的原子操作，支持透支
   * 
   * @param orderId 要修改的订单ID
   * @param params 新的订单参数
   * @returns Promise<OrderResponse> 新订单信息
   * @throws OrderApiError 当业务逻辑错误时
   */
  static async updateOrder(orderId: number, params: UpdateOrderRequest): Promise<OrderResponse> {
    return httpClient.put<OrderResponse>(API_ENDPOINTS.ORDER_UPDATE(orderId), params, {
      retryConfig: {
        maxAttempts: 2,
        baseDelay: 1000,
        maxDelay: 3000,
        backoffFactor: 2,
        retryableErrors: ['timeout', 'NETWORK_ERROR']
      }
    })
  }

  /**
   * 取消订单
   * 取消订单并自动退款到用户余额
   * 
   * @param orderId 要取消的订单ID
   * @returns Promise<CancelOrderResponse> 取消结果
   * @throws OrderApiError 当业务逻辑错误时
   */
  static async cancelOrder(orderId: number): Promise<CancelOrderResponse> {
    return httpClient.delete<CancelOrderResponse>(API_ENDPOINTS.ORDER_CANCEL(orderId), {
      retryConfig: {
        maxAttempts: 2,
        baseDelay: 1000,
        maxDelay: 3000,
        backoffFactor: 2,
        retryableErrors: ['timeout', 'NETWORK_ERROR']
      }
    })
  }
}

/**
 * 订单操作的业务逻辑封装
 * 提供更高级的操作接口，包含错误处理和用户提示
 */
export class OrderService {
  /**
   * 下单操作
   * 包含完整的错误处理、透支提醒和用户提示
   * 
   * @param params 订单参数
   * @returns Promise<OrderResponse | null> 成功时返回订单信息，失败时返回null
   */
  static async placeOrder(params: CreateOrderRequest): Promise<OrderResponse | null> {
    try {
      wx.showLoading({ title: '下单中...' })
      const result = await OrderApi.createOrder(params)
      wx.hideLoading()
      
      // 检查是否触发透支
      if (result.balance_cents < 0) {
        // 透支提醒
        const overdraftAmount = Math.abs(result.balance_cents) / 100
        await new Promise<void>((resolve) => {
          wx.showModal({
            title: '透支提醒',
            content: `下单成功！\n当前余额：${result.balance_cents / 100}元\n您已透支${overdraftAmount}元${result.overdraft_warning ? '\n' + result.overdraft_warning : ''}`,
            showCancel: false,
            confirmText: '我知道了',
            success: () => resolve(),
            fail: () => resolve()
          })
        })
      } else {
        wx.showToast({
          title: '下单成功',
          icon: 'success',
          duration: 2000
        })
      }
      
      return result
    } catch (error: any) {
      wx.hideLoading()
      
      // 业务错误处理
      const message = this.getErrorMessage(error)
      wx.showToast({
        title: message,
        icon: 'none',
        duration: 3000
      })
      
      return null
    }
  }

  /**
   * 修改订单操作
   * 支持透支状态下的订单修改
   * 
   * @param orderId 订单ID
   * @param params 新的订单参数
   * @returns Promise<OrderResponse | null> 成功时返回订单信息，失败时返回null
   */
  static async modifyOrder(orderId: number, params: UpdateOrderRequest): Promise<OrderResponse | null> {
    try {
      wx.showLoading({ title: '修改中...' })
      const result = await OrderApi.updateOrder(orderId, params)
      wx.hideLoading()
      
      // 检查修改后是否进入透支状态
      if (result.balance_cents < 0) {
        const overdraftAmount = Math.abs(result.balance_cents) / 100
        await new Promise<void>((resolve) => {
          wx.showModal({
            title: '订单修改成功',
            content: `修改成功！\n当前余额：${result.balance_cents / 100}元\n您已透支${overdraftAmount}元${result.overdraft_warning ? '\n' + result.overdraft_warning : ''}`,
            showCancel: false,
            confirmText: '我知道了',
            success: () => resolve(),
            fail: () => resolve()
          })
        })
      } else {
        wx.showToast({
          title: '修改成功',
          icon: 'success',
          duration: 2000
        })
      }
      
      return result
    } catch (error: any) {
      wx.hideLoading()
      
      const message = this.getErrorMessage(error)
      wx.showToast({
        title: message,
        icon: 'none',
        duration: 3000
      })
      
      return null
    }
  }

  /**
   * 取消订单操作
   * 包含二次确认和完整的错误处理
   * 
   * @param orderId 订单ID
   * @returns Promise<boolean> 是否成功取消
   */
  static async cancelOrder(orderId: number): Promise<boolean> {
    try {
      // 二次确认
      const confirmResult = await new Promise<boolean>((resolve) => {
        wx.showModal({
          title: '确认取消',
          content: '确定要取消这个订单吗？款项将自动退回余额。',
          success: (res) => resolve(res.confirm),
          fail: () => resolve(false)
        })
      })

      if (!confirmResult) {
        return false
      }

      wx.showLoading({ title: '取消中...' })
      await OrderApi.cancelOrder(orderId)
      wx.hideLoading()
      
      wx.showToast({
        title: '已取消订单',
        icon: 'success',
        duration: 2000
      })
      
      return true
    } catch (error: any) {
      wx.hideLoading()
      
      const message = this.getErrorMessage(error)
      wx.showToast({
        title: message,
        icon: 'none',
        duration: 3000
      })
      
      return false
    }
  }

  /**
   * 统一的错误消息处理
   * 将后端错误码转换为用户友好的消息，包含透支相关错误
   * 
   * @param error 错误对象
   * @returns string 用户友好的错误消息
   */
  private static getErrorMessage(error: any): string {
    const message = error?.message || error?.detail?.message || '操作失败'
    
    // 常见错误的友好提示
    if (message.includes('already ordered')) {
      return '您已在此餐次下单'
    }
    if (message.includes('capacity exceeded')) {
      return '餐次容量已满，请选择其他餐次'
    }
    if (message.includes('meal not open')) {
      return '此餐次暂不接受订单'
    }
    if (message.includes('meal not found')) {
      return '餐次不存在'
    }
    if (message.includes('order not found')) {
      return '订单不存在'
    }
    if (message.includes('cannot cancel after lock')) {
      return '餐次已锁定，无法取消订单'
    }
    if (message.includes('qty must be 1')) {
      return '每人每餐只能订一份'
    }
    if (message.includes('insufficient balance')) {
      return '余额不足（可继续使用透支功能）'
    }
    if (message.includes('overdraft limit exceeded')) {
      return '透支额度不足，请先充值'
    }
    if (message.includes('PERMISSION_DENIED')) {
      return '权限不足，请联系管理员'
    }
    if (message.includes('VALIDATION_ERROR')) {
      return '请求参数错误，请重试'
    }
    
    return message
  }
}

// 默认导出
export default OrderService