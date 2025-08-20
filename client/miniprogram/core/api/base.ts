/**
 * 基础HTTP请求封装
 * 提供统一的请求处理、错误处理和重试机制
 */

import { API_CONFIG, STORAGE_KEYS, HTTP_STATUS } from '../constants'
import type { BaseResponse } from '../../types'

export interface RequestOptions extends Partial<WechatMiniprogram.RequestOption> {
  showLoading?: boolean
  showError?: boolean
  cache?: boolean
  cacheDuration?: number
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
  private cache: Map<string, { data: any; expires: number }> = new Map()

  constructor() {
    this.baseURL = API_CONFIG.BASE_URL
    this.timeout = API_CONFIG.TIMEOUT
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
   * 生成缓存键
   */
  private getCacheKey(url: string, method: string, data?: any): string {
    const dataString = data ? JSON.stringify(data) : ''
    return `${method}_${url}_${dataString}`
  }

  /**
   * 从缓存获取数据
   */
  private getFromCache(key: string): any {
    const cached = this.cache.get(key)
    if (cached && cached.expires > Date.now()) {
      return cached.data
    }
    this.cache.delete(key)
    return null
  }

  /**
   * 设置缓存
   */
  private setToCache(key: string, data: any, duration: number = 5 * 60 * 1000) {
    this.cache.set(key, {
      data,
      expires: Date.now() + duration
    })
  }

  /**
   * 清除缓存
   */
  clearCache() {
    this.cache.clear()
  }

  /**
   * 清除特定URL的缓存
   */
  clearCacheByUrl(url: string) {
    const keysToDelete = Array.from(this.cache.keys()).filter(key => key.includes(url))
    keysToDelete.forEach(key => this.cache.delete(key))
  }


  /**
   * 执行HTTP请求（简化版，无重试机制）
   */
  private async executeRequest<T = any>(
    url: string, 
    options: RequestOptions = {}
  ): Promise<T> {
    const {
      showLoading = false,
      showError = true,
      cache = false,
      cacheDuration = 5 * 60 * 1000, // 5分钟默认缓存
      ...requestOptions
    } = options

    const method = requestOptions.method || 'GET'
    const cacheKey = cache ? this.getCacheKey(url, method, requestOptions.data) : ''

    // 检查缓存（仅对GET请求且启用缓存时）
    if (cache && method === 'GET') {
      const cachedData = this.getFromCache(cacheKey)
      if (cachedData) {
        return cachedData as T
      }
    }

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
        // 缓存成功的GET请求结果
        if (cache && method === 'GET') {
          this.setToCache(cacheKey, data, cacheDuration)
        }
        
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
      console.error('API请求失败:', error)
      
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
   * 处理错误（简化版）
   */
  private handleError(error: any) {
    let message = '操作失败'

    if (error?.errMsg?.includes('timeout')) {
      message = '请求超时，请检查网络连接'
    } else if (error?.errMsg?.includes('fail')) {
      message = '网络连接失败'
    } else if (error.code === HTTP_STATUS.UNAUTHORIZED) {
      message = '登录已过期，请重新登录'
    } else if (error.code === HTTP_STATUS.FORBIDDEN) {
      message = '访问被拒绝'
    } else if (error.code === HTTP_STATUS.NOT_FOUND) {
      message = '请求的资源不存在'
    } else if (error.code >= 500) {
      message = '服务器错误，请稍后重试'
    } else if (error.message) {
      message = error.message
    }

    wx.showToast({
      title: message,
      icon: 'error',
      duration: 3000
    })
  }

  /**
   * GET请求
   */
  async get<T = any>(url: string, options: RequestOptions = {}): Promise<T> {
    return this.executeRequest<T>(url, {
      cache: true, // GET请求默认启用缓存
      ...options,
      method: 'GET'
    })
  }

  /**
   * POST请求
   */
  async post<T = any>(url: string, data?: any, options: RequestOptions = {}): Promise<T> {
    const result = await this.executeRequest<T>(url, {
      ...options,
      method: 'POST',
      data
    })
    
    // POST操作可能影响相关数据，清理相关缓存
    this.clearCacheByUrl(url)
    
    return result
  }

  /**
   * PUT请求
   */
  async put<T = any>(url: string, data?: any, options: RequestOptions = {}): Promise<T> {
    const result = await this.executeRequest<T>(url, {
      ...options,
      method: 'PUT',
      data
    })
    
    // PUT操作会修改数据，清理相关缓存
    this.clearCacheByUrl(url)
    
    return result
  }

  /**
   * PATCH请求
   */
  async patch<T = any>(url: string, data?: any, options: RequestOptions = {}): Promise<T> {
    const result = await this.executeRequest<T>(url, {
      ...options,
      method: 'PATCH',
      data
    })
    
    // PATCH操作会修改数据，清理相关缓存
    this.clearCacheByUrl(url)
    
    return result
  }

  /**
   * DELETE请求
   */
  async delete<T = any>(url: string, options: RequestOptions = {}): Promise<T> {
    const result = await this.executeRequest<T>(url, {
      ...options,
      method: 'DELETE'
    })
    
    // DELETE操作会删除数据，清理相关缓存
    this.clearCacheByUrl(url)
    
    return result
  }
}

// 导出默认实例
export const httpClient = new HttpClient()