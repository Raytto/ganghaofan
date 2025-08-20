/**
 * 应用状态管理中心
 * 提供响应式状态管理、持久化和页面同步功能
 */

import { STORAGE_KEYS } from '../constants'

// 状态接口定义
export interface AppState {
  // 用户相关状态
  user: {
    isLoggedIn: boolean
    openId: string | null
    isAdmin: boolean
    balance: number
  }
  
  // 应用配置状态
  app: {
    debugMode: boolean
    darkMode: boolean
    adminViewEnabled: boolean
    initialized: boolean
  }
  
  // 业务数据状态
  business: {
    currentMonth: string
    selectedDate: string | null
    calendarData: Map<string, any>
    ordersCache: Map<string, any>
  }
  
  // UI状态
  ui: {
    loading: Set<string>
    tabbarVisible: boolean
    navbarHeight: number
    statusBarHeight: number
  }
}

// 状态监听器类型
type StateListener<T = any> = (newValue: T, oldValue: T, path: string) => void
type StateChangeHandler = (state: AppState, changedPath: string) => void

// 状态持久化配置
interface PersistConfig {
  key: string
  paths: string[] // 需要持久化的状态路径
  throttle?: number // 持久化节流时间
}

/**
 * 响应式状态管理器
 */
export class StateManager {
  private state: AppState
  private listeners: Map<string, Set<StateListener>> = new Map()
  private changeHandlers: Set<StateChangeHandler> = new Set()
  private persistConfig: PersistConfig[] = []
  private throttleTimers: Map<string, number> = new Map()

  constructor() {
    this.state = this.createInitialState()
    this.setupPersistence()
    this.loadPersistedState()
  }

  /**
   * 创建初始状态
   */
  private createInitialState(): AppState {
    return {
      user: {
        isLoggedIn: false,
        openId: null,
        isAdmin: false,
        balance: 0
      },
      app: {
        debugMode: false,
        darkMode: true,
        adminViewEnabled: false,
        initialized: false
      },
      business: {
        currentMonth: this.getCurrentMonth(),
        selectedDate: null,
        calendarData: new Map(),
        ordersCache: new Map()
      },
      ui: {
        loading: new Set(),
        tabbarVisible: true,
        navbarHeight: 44,
        statusBarHeight: 20
      }
    }
  }

  /**
   * 配置状态持久化
   */
  private setupPersistence() {
    this.persistConfig = [
      {
        key: 'app_state',
        paths: ['app.darkMode', 'app.adminViewEnabled'],
        throttle: 1000
      },
      {
        key: 'user_state',
        paths: ['user.openId'],
        throttle: 500
      },
      {
        key: 'business_state',
        paths: ['business.currentMonth'],
        throttle: 2000
      }
    ]
  }

  /**
   * 加载持久化状态
   */
  private loadPersistedState() {
    this.persistConfig.forEach(config => {
      try {
        const stored = wx.getStorageSync(config.key)
        if (stored) {
          const data = JSON.parse(stored)
          config.paths.forEach(path => {
            const value = this.getValueByPath(data, path)
            if (value !== undefined) {
              this.setValueByPath(this.state, path, value)
            }
          })
        }
      } catch (error) {
        console.warn(`Failed to load persisted state for ${config.key}:`, error)
      }
    })

    // 兼容旧的存储方式
    this.migrateOldStorage()
  }

  /**
   * 迁移旧的存储方式
   */
  private migrateOldStorage() {
    try {
      // 迁移主题设置
      const oldDarkMode = wx.getStorageSync('dark_mode')
      if (oldDarkMode !== null) {
        this.state.app.darkMode = !!oldDarkMode
        wx.removeStorageSync('dark_mode')
      }

      // 迁移管理视图设置
      const oldAdminView = wx.getStorageSync('admin_view_enabled')
      if (oldAdminView !== null) {
        this.state.app.adminViewEnabled = !!oldAdminView
        wx.removeStorageSync('admin_view_enabled')
      }

      // 迁移管理员设置
      const oldIsAdmin = wx.getStorageSync('is_admin')
      if (oldIsAdmin !== null) {
        this.state.user.isAdmin = !!oldIsAdmin
        wx.removeStorageSync('is_admin')
      }

      // 保存迁移后的状态
      this.persistState()
    } catch (error) {
      console.warn('Failed to migrate old storage:', error)
    }
  }

  /**
   * 持久化状态
   */
  private persistState() {
    this.persistConfig.forEach(config => {
      const dataToStore: any = {}
      let hasData = false

      config.paths.forEach(path => {
        const value = this.getValueByPath(this.state, path)
        if (value !== undefined) {
          this.setValueByPath(dataToStore, path, value)
          hasData = true
        }
      })

      if (hasData) {
        try {
          wx.setStorageSync(config.key, JSON.stringify(dataToStore))
        } catch (error) {
          console.warn(`Failed to persist state for ${config.key}:`, error)
        }
      }
    })
  }

  /**
   * 节流持久化
   */
  private throttlePersist(config: PersistConfig) {
    if (!config.throttle) {
      this.persistState()
      return
    }

    const existingTimer = this.throttleTimers.get(config.key)
    if (existingTimer) {
      clearTimeout(existingTimer)
    }

    const timer = setTimeout(() => {
      this.persistState()
      this.throttleTimers.delete(config.key)
    }, config.throttle)

    this.throttleTimers.set(config.key, timer)
  }

  /**
   * 获取状态值（支持路径）
   */
  getState<T = any>(path?: string): T {
    if (!path) return this.state as T
    return this.getValueByPath(this.state, path) as T
  }

  /**
   * 设置状态值（支持路径）
   */
  setState(path: string, value: any) {
    const oldValue = this.getValueByPath(this.state, path)
    
    if (oldValue === value) return // 值未变化，不触发更新

    this.setValueByPath(this.state, path, value)

    // 触发监听器
    this.notifyListeners(path, value, oldValue)
    
    // 触发全局变化处理器
    this.changeHandlers.forEach(handler => {
      try {
        handler(this.state, path)
      } catch (error) {
        console.error('State change handler error:', error)
      }
    })

    // 检查是否需要持久化
    this.persistConfig.forEach(config => {
      if (config.paths.some(p => path.startsWith(p))) {
        this.throttlePersist(config)
      }
    })
  }

  /**
   * 批量更新状态
   */
  batchUpdate(updates: { path: string; value: any }[]) {
    const changes: { path: string; newValue: any; oldValue: any }[] = []

    // 收集所有变化
    updates.forEach(({ path, value }) => {
      const oldValue = this.getValueByPath(this.state, path)
      if (oldValue !== value) {
        this.setValueByPath(this.state, path, value)
        changes.push({ path, newValue: value, oldValue })
      }
    })

    if (changes.length === 0) return

    // 批量触发监听器
    changes.forEach(({ path, newValue, oldValue }) => {
      this.notifyListeners(path, newValue, oldValue)
    })

    // 触发全局变化处理器
    this.changeHandlers.forEach(handler => {
      changes.forEach(({ path }) => {
        try {
          handler(this.state, path)
        } catch (error) {
          console.error('State change handler error:', error)
        }
      })
    })

    // 持久化
    this.persistState()
  }

  /**
   * 订阅状态变化
   */
  subscribe(path: string, listener: StateListener): () => void {
    if (!this.listeners.has(path)) {
      this.listeners.set(path, new Set())
    }
    
    const pathListeners = this.listeners.get(path)!
    pathListeners.add(listener)

    // 返回取消订阅函数
    return () => {
      pathListeners.delete(listener)
      if (pathListeners.size === 0) {
        this.listeners.delete(path)
      }
    }
  }

  /**
   * 订阅全局状态变化
   */
  onStateChange(handler: StateChangeHandler): () => void {
    this.changeHandlers.add(handler)
    return () => this.changeHandlers.delete(handler)
  }

  /**
   * 通知监听器
   */
  private notifyListeners(path: string, newValue: any, oldValue: any) {
    // 通知精确路径监听器
    const exactListeners = this.listeners.get(path)
    if (exactListeners) {
      exactListeners.forEach(listener => {
        try {
          listener(newValue, oldValue, path)
        } catch (error) {
          console.error('State listener error:', error)
        }
      })
    }

    // 通知父路径监听器
    const pathParts = path.split('.')
    for (let i = pathParts.length - 1; i > 0; i--) {
      const parentPath = pathParts.slice(0, i).join('.')
      const parentListeners = this.listeners.get(parentPath)
      if (parentListeners) {
        const parentNewValue = this.getValueByPath(this.state, parentPath)
        parentListeners.forEach(listener => {
          try {
            listener(parentNewValue, oldValue, path)
          } catch (error) {
            console.error('State listener error:', error)
          }
        })
      }
    }
  }

  /**
   * 通过路径获取值
   */
  private getValueByPath(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : undefined
    }, obj)
  }

  /**
   * 通过路径设置值
   */
  private setValueByPath(obj: any, path: string, value: any) {
    const keys = path.split('.')
    const lastKey = keys.pop()!
    const target = keys.reduce((current, key) => {
      if (!current[key] || typeof current[key] !== 'object') {
        current[key] = {}
      }
      return current[key]
    }, obj)
    target[lastKey] = value
  }

  /**
   * 获取当前月份
   */
  private getCurrentMonth(): string {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  }

  /**
   * 重置状态
   */
  reset() {
    const newState = this.createInitialState()
    Object.keys(this.state).forEach(key => {
      (this.state as any)[key] = (newState as any)[key]
    })
    this.persistState()
  }

  /**
   * 清理资源
   */
  destroy() {
    this.listeners.clear()
    this.changeHandlers.clear()
    this.throttleTimers.forEach(timer => clearTimeout(timer))
    this.throttleTimers.clear()
  }
}

// 创建全局状态管理器实例
export const stateManager = new StateManager()

// 导出便捷的状态访问函数
export const getState = <T = any>(path?: string): T => stateManager.getState<T>(path)
export const setState = (path: string, value: any) => stateManager.setState(path, value)
export const subscribe = (path: string, listener: StateListener) => stateManager.subscribe(path, listener)
export const onStateChange = (handler: StateChangeHandler) => stateManager.onStateChange(handler)

// 导出状态类型
export type { AppState, StateListener, StateChangeHandler }

// 导出所有相关模块
export * from './reactive'
export * from './actions'