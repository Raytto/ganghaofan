/**
 * 认证相关API封装
 */

import { httpClient } from './base'
import { API_ENDPOINTS, STORAGE_KEYS } from '../constants'
import type { 
  LoginRequest, 
  LoginResponse, 
  PassphraseRequest, 
  PassphraseResponse
} from '../../types'

export class AuthAPI {
  /**
   * 微信登录
   */
  async login(code: string): Promise<LoginResponse> {
    const request: LoginRequest = { code }
    const response = await httpClient.post<LoginResponse>(
      API_ENDPOINTS.LOGIN, 
      request,
      { 
        showLoading: true,
        retryConfig: {
          maxAttempts: 3, // 登录重试次数稍多
          baseDelay: 1000,
          maxDelay: 5000,
          backoffFactor: 2,
          retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
        }
      }
    )
    
    // 自动保存token
    if (response.token) {
      this.saveToken(response.token)
    }
    
    return response
  }

  /**
   * 微信登录（完整流程）
   */
  async loginWithWechat(): Promise<LoginResponse> {
    try {
      // 获取微信登录code
      const loginResult = await new Promise<WechatMiniprogram.LoginSuccessCallbackResult>((resolve, reject) => {
        wx.login({ success: resolve, fail: reject })
      })

      // 调用后端登录接口
      const response = await this.login(loginResult.code)
      
      // 获取当前用户的open_id并缓存
      try {
        await this.ensureCurrentOpenId()
      } catch (error) {
        console.warn('Failed to cache current open_id:', error)
      }

      return response

    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  /**
   * 解析口令
   */
  async resolvePassphrase(passphrase: string): Promise<PassphraseResponse> {
    const request: PassphraseRequest = { passphrase }
    return httpClient.post<PassphraseResponse>(
      API_ENDPOINTS.RESOLVE_PASSPHRASE, 
      request,
      {
        retryConfig: {
          maxAttempts: 2,
          baseDelay: 1000,
          maxDelay: 3000,
          backoffFactor: 2,
          retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
        }
      }
    )
  }

  /**
   * 获取Mock配置
   */
  async getMockConfig(): Promise<any> {
    return httpClient.get(API_ENDPOINTS.MOCK_CONFIG)
  }

  /**
   * 保存token
   */
  saveToken(token: string) {
    try {
      wx.setStorageSync(STORAGE_KEYS.TOKEN, token)
      // 清除缓存的open_id，强制重新获取
      try {
        wx.removeStorageSync(STORAGE_KEYS.CURRENT_OPEN_ID)
      } catch {}
    } catch (error) {
      console.error('Failed to save token:', error)
    }
  }

  /**
   * 获取token
   */
  getToken(): string | null {
    try {
      return wx.getStorageSync(STORAGE_KEYS.TOKEN) || null
    } catch {
      return null
    }
  }

  /**
   * 清除token
   */
  clearToken() {
    try {
      wx.removeStorageSync(STORAGE_KEYS.TOKEN)
      wx.removeStorageSync(STORAGE_KEYS.CURRENT_OPEN_ID)
    } catch {}
  }

  /**
   * 检查是否已登录
   */
  isLoggedIn(): boolean {
    return !!this.getToken()
  }

  /**
   * 确保获取当前用户的open_id
   */
  private async ensureCurrentOpenId(): Promise<string | null> {
    let openId = this.getCurrentOpenId()
    if (openId) return openId

    try {
      // 通过用户信息接口获取open_id
      const userInfo = await httpClient.get('/users/me')
      openId = userInfo?.open_id
      
      if (openId) {
        this.saveCurrentOpenId(openId)
        // 迁移全局DB Key到用户作用域
        this.migrateGlobalDbKey(openId)
      }
      
      return openId
    } catch (error) {
      console.warn('Failed to get current open_id:', error)
      return null
    }
  }

  /**
   * 获取当前缓存的open_id
   */
  getCurrentOpenId(): string | null {
    try {
      return wx.getStorageSync(STORAGE_KEYS.CURRENT_OPEN_ID) || null
    } catch {
      return null
    }
  }

  /**
   * 保存当前open_id
   */
  private saveCurrentOpenId(openId: string) {
    try {
      wx.setStorageSync(STORAGE_KEYS.CURRENT_OPEN_ID, openId)
    } catch {}
  }

  /**
   * 迁移全局DB Key到用户作用域
   */
  private migrateGlobalDbKey(openId: string) {
    try {
      const globalKey = wx.getStorageSync(STORAGE_KEYS.DB_KEY_GLOBAL)
      if (globalKey) {
        const keyMap = wx.getStorageSync(STORAGE_KEYS.DB_KEY_MAP) || {}
        keyMap[openId] = globalKey
        wx.setStorageSync(STORAGE_KEYS.DB_KEY_MAP, keyMap)
        wx.removeStorageSync(STORAGE_KEYS.DB_KEY_GLOBAL)
      }
    } catch {}
  }

  /**
   * 设置数据库密钥
   */
  setDbKey(key: string | null) {
    try {
      const openId = this.getCurrentOpenId()
      
      if (openId) {
        // 用户作用域存储
        const keyMap = wx.getStorageSync(STORAGE_KEYS.DB_KEY_MAP) || {}
        if (key) {
          keyMap[openId] = key
        } else {
          delete keyMap[openId]
        }
        wx.setStorageSync(STORAGE_KEYS.DB_KEY_MAP, keyMap)
      } else {
        // 全局临时存储
        if (key) {
          wx.setStorageSync(STORAGE_KEYS.DB_KEY_GLOBAL, key)
        } else {
          wx.removeStorageSync(STORAGE_KEYS.DB_KEY_GLOBAL)
        }
      }
    } catch (error) {
      console.error('Failed to set DB key:', error)
    }
  }

  /**
   * 获取数据库密钥
   */
  getDbKey(): string | null {
    try {
      const keyMap = wx.getStorageSync(STORAGE_KEYS.DB_KEY_MAP) || {}
      const openId = this.getCurrentOpenId()
      
      if (openId && keyMap[openId]) {
        return keyMap[openId]
      }
      
      // 回退到全局密钥
      return wx.getStorageSync(STORAGE_KEYS.DB_KEY_GLOBAL) || null
    } catch {
      return null
    }
  }
}

// 导出默认实例
export const authAPI = new AuthAPI()