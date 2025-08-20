/**
 * 基础HTTP请求封装
 * 提供统一的请求处理、错误处理和重试机制
 */

import { API_CONFIG, STORAGE_KEYS, HTTP_STATUS } from '../constants'
import type { BaseResponse } from '../../types'

export interface RequestOptions extends Partial<WechatMiniprogram.RequestOption> {
  showLoading?: boolean
  showError?: boolean
  retries?: number
}

export interface ApiError {
  code: number
  message: string
  details?: any
}

/**
 * HTTP请求管理器
 */
export class HttpClient {
  private baseURL: string
  private timeout: number
  private maxRetries: number

  constructor() {
    this.baseURL = API_CONFIG.BASE_URL
    this.timeout = API_CONFIG.TIMEOUT
    this.maxRetries = API_CONFIG.MAX_RETRIES
  }

  /**
   * 获取存储的token
   */
  private getToken(): string | null {
    try {
      return wx.getStorageSync(STORAGE_KEYS.TOKEN) || null
    } catch {
      return null
    }
  }

  /**
   * 获取数据库密钥
   */
  private getDbKey(): string | null {
    try {
      const map = wx.getStorageSync(STORAGE_KEYS.DB_KEY_MAP) || {}
      const openId = wx.getStorageSync(STORAGE_KEYS.CURRENT_OPEN_ID)
      
      if (openId && map[openId]) {
        return map[openId]
      }
      
      // 回退到全局密钥
      const globalKey = wx.getStorageSync(STORAGE_KEYS.DB_KEY_GLOBAL)
      return globalKey || null
    } catch {
      return null
    }
  }

  /**
   * 构建请求头
   */
  private buildHeaders(options: RequestOptions = {}): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }

    // 添加认证token
    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // 添加数据库密钥
    const dbKey = this.getDbKey()
    if (dbKey) {
      headers['X-DB-Key'] = dbKey
    }

    // 合并自定义头
    if (options.header) {
      Object.assign(headers, options.header)
    }

    return headers
  }

  /**
   * 执行HTTP请求
   */
  private async executeRequest<T = any>(
    url: string, 
    options: RequestOptions = {}
  ): Promise<T> {
    const {
      showLoading = false,
      showError = true,
      retries = 0,
      ...requestOptions
    } = options

    if (showLoading) {
      wx.showLoading({ title: '加载中...', mask: true })
    }

    try {
      const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`
      const headers = this.buildHeaders(options)

      const response = await new Promise<WechatMiniprogram.RequestSuccessCallbackResult>((resolve, reject) => {
        wx.request({
          url: fullUrl,
          timeout: this.timeout,
          header: headers,
          ...requestOptions,
          success: resolve,
          fail: reject
        })
      })

      const { statusCode, data } = response

      if (statusCode >= 200 && statusCode < 300) {
        return data as T
      }

      // 处理HTTP错误
      const error: ApiError = {
        code: statusCode,
        message: (data as any)?.message || `HTTP ${statusCode}`,
        details: data
      }

      throw error

    } catch (error: any) {
      // 网络错误重试
      if (retries < this.maxRetries && this.shouldRetry(error)) {
        console.log(`Request failed, retrying... (${retries + 1}/${this.maxRetries})`)
        return this.executeRequest(url, { ...options, retries: retries + 1 })
      }

      if (showError) {
        this.handleError(error)
      }

      throw error

    } finally {
      if (showLoading) {
        wx.hideLoading()
      }
    }
  }

  /**
   * 判断是否应该重试
   */
  private shouldRetry(error: any): boolean {
    // 网络错误重试
    if (error.code === -1 || error.errMsg?.includes('fail')) {
      return true
    }

    // 服务器错误重试
    if (error.code >= 500) {
      return true
    }

    return false
  }

  /**
   * 处理错误
   */
  private handleError(error: any) {
    let message = '请求失败'

    if (error.code === -1) {
      message = '网络连接失败'
    } else if (error.code === HTTP_STATUS.UNAUTHORIZED) {
      message = '登录已过期，请重新登录'
      // 可以在这里触发重新登录
    } else if (error.code === HTTP_STATUS.FORBIDDEN) {
      message = '访问被拒绝'
    } else if (error.code === HTTP_STATUS.NOT_FOUND) {
      message = '请求的资源不存在'
    } else if (error.message) {
      message = error.message
    }

    wx.showToast({
      title: message,
      icon: 'none',
      duration: 2000
    })
  }

  /**
   * GET请求
   */
  async get<T = any>(url: string, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>(url, {
      ...options,
      method: 'GET'
    })
  }

  /**
   * POST请求
   */
  async post<T = any>(url: string, data?: any, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>(url, {
      ...options,
      method: 'POST',
      data
    })
  }

  /**
   * PUT请求
   */
  async put<T = any>(url: string, data?: any, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>(url, {
      ...options,
      method: 'PUT',
      data
    })
  }

  /**
   * PATCH请求
   */
  async patch<T = any>(url: string, data?: any, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>(url, {
      ...options,
      method: 'PATCH',
      data
    })
  }

  /**
   * DELETE请求
   */
  async delete<T = any>(url: string, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>(url, {
      ...options,
      method: 'DELETE'
    })
  }
}

// 导出默认实例
export const httpClient = new HttpClient()