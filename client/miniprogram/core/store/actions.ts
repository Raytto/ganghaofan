/**
 * 状态操作动作
 * 提供类型安全的状态修改方法
 */

import { stateManager, AppState } from './index'

/**
 * 用户相关操作
 */
export const userActions = {
  /**
   * 设置登录状态
   */
  setLoginState(openId: string, isAdmin = false, balance = 0) {
    stateManager.batchUpdate([
      { path: 'user.isLoggedIn', value: true },
      { path: 'user.openId', value: openId },
      { path: 'user.isAdmin', value: isAdmin },
      { path: 'user.balance', value: balance }
    ])
  },

  /**
   * 更新用户余额
   */
  updateBalance(balance: number) {
    stateManager.setState('user.balance', balance)
  },

  /**
   * 设置管理员状态
   */
  setAdminStatus(isAdmin: boolean) {
    stateManager.setState('user.isAdmin', isAdmin)
  },

  /**
   * 退出登录
   */
  logout() {
    stateManager.batchUpdate([
      { path: 'user.isLoggedIn', value: false },
      { path: 'user.openId', value: null },
      { path: 'user.isAdmin', value: false },
      { path: 'user.balance', value: 0 }
    ])
  }
}

/**
 * 应用配置操作
 */
export const appActions = {
  /**
   * 设置调试模式
   */
  setDebugMode(enabled: boolean) {
    stateManager.setState('app.debugMode', enabled)
  },

  /**
   * 切换暗色模式
   */
  toggleDarkMode() {
    const currentMode = stateManager.getState<boolean>('app.darkMode')
    stateManager.setState('app.darkMode', !currentMode)
  },

  /**
   * 设置暗色模式
   */
  setDarkMode(enabled: boolean) {
    stateManager.setState('app.darkMode', enabled)
  },

  /**
   * 切换管理视图
   */
  toggleAdminView() {
    const currentView = stateManager.getState<boolean>('app.adminViewEnabled')
    stateManager.setState('app.adminViewEnabled', !currentView)
  },

  /**
   * 设置管理视图
   */
  setAdminView(enabled: boolean) {
    stateManager.setState('app.adminViewEnabled', enabled)
  },

  /**
   * 标记应用已初始化
   */
  setInitialized(initialized = true) {
    stateManager.setState('app.initialized', initialized)
  }
}

/**
 * 业务数据操作
 */
export const businessActions = {
  /**
   * 设置当前月份
   */
  setCurrentMonth(month: string) {
    stateManager.setState('business.currentMonth', month)
  },

  /**
   * 设置选中日期
   */
  setSelectedDate(date: string | null) {
    stateManager.setState('business.selectedDate', date)
  },

  /**
   * 更新日历数据
   */
  updateCalendarData(month: string, data: any) {
    const currentData = stateManager.getState<Map<string, any>>('business.calendarData')
    const newData = new Map(currentData)
    newData.set(month, data)
    stateManager.setState('business.calendarData', newData)
  },

  /**
   * 批量更新日历数据
   */
  batchUpdateCalendarData(updates: { month: string, data: any }[]) {
    const currentData = stateManager.getState<Map<string, any>>('business.calendarData')
    const newData = new Map(currentData)
    
    updates.forEach(({ month, data }) => {
      newData.set(month, data)
    })
    
    stateManager.setState('business.calendarData', newData)
  },

  /**
   * 清空日历数据
   */
  clearCalendarData() {
    stateManager.setState('business.calendarData', new Map())
  },

  /**
   * 更新订单缓存
   */
  updateOrdersCache(key: string, data: any) {
    const currentCache = stateManager.getState<Map<string, any>>('business.ordersCache')
    const newCache = new Map(currentCache)
    newCache.set(key, data)
    stateManager.setState('business.ordersCache', newCache)
  },

  /**
   * 清空订单缓存
   */
  clearOrdersCache() {
    stateManager.setState('business.ordersCache', new Map())
  }
}

/**
 * UI 状态操作
 */
export const uiActions = {
  /**
   * 显示加载状态
   */
  showLoading(key: string) {
    const currentLoading = stateManager.getState<Set<string>>('ui.loading')
    const newLoading = new Set(currentLoading)
    newLoading.add(key)
    stateManager.setState('ui.loading', newLoading)
  },

  /**
   * 隐藏加载状态
   */
  hideLoading(key: string) {
    const currentLoading = stateManager.getState<Set<string>>('ui.loading')
    const newLoading = new Set(currentLoading)
    newLoading.delete(key)
    stateManager.setState('ui.loading', newLoading)
  },

  /**
   * 检查是否在加载
   */
  isLoading(key: string): boolean {
    const currentLoading = stateManager.getState<Set<string>>('ui.loading')
    return currentLoading.has(key)
  },

  /**
   * 清空所有加载状态
   */
  clearAllLoading() {
    stateManager.setState('ui.loading', new Set())
  },

  /**
   * 设置 Tabbar 可见性
   */
  setTabbarVisible(visible: boolean) {
    stateManager.setState('ui.tabbarVisible', visible)
  },

  /**
   * 设置导航栏高度
   */
  setNavbarHeight(height: number) {
    stateManager.setState('ui.navbarHeight', height)
  },

  /**
   * 设置状态栏高度
   */
  setStatusBarHeight(height: number) {
    stateManager.setState('ui.statusBarHeight', height)
  },

  /**
   * 初始化系统信息
   */
  initSystemInfo() {
    try {
      const systemInfo = wx.getSystemInfoSync()
      stateManager.batchUpdate([
        { path: 'ui.statusBarHeight', value: systemInfo.statusBarHeight || 20 },
        { path: 'ui.navbarHeight', value: 44 } // 标准导航栏高度
      ])
    } catch (error) {
      console.warn('Failed to get system info:', error)
    }
  }
}

/**
 * 组合操作
 */
export const combinedActions = {
  /**
   * 应用启动初始化
   */
  async initializeApp() {
    // 初始化系统信息
    uiActions.initSystemInfo()
    
    // 检查登录状态
    try {
      const token = wx.getStorageSync('auth_token')
      if (token) {
        // 这里可以验证 token 有效性
        // 暂时假设有效
        const openId = wx.getStorageSync('user_openid')
        const isAdmin = wx.getStorageSync('is_admin') || false
        
        if (openId) {
          userActions.setLoginState(openId, isAdmin)
        }
      }
    } catch (error) {
      console.warn('Failed to restore login state:', error)
    }

    // 标记初始化完成
    appActions.setInitialized(true)
  },

  /**
   * 用户登录完成后的状态更新
   */
  completeLogin(userData: {
    openId: string
    isAdmin: boolean
    balance: number
    token: string
  }) {
    // 保存到本地存储
    try {
      wx.setStorageSync('auth_token', userData.token)
      wx.setStorageSync('user_openid', userData.openId)
      wx.setStorageSync('is_admin', userData.isAdmin)
    } catch (error) {
      console.warn('Failed to save user data to storage:', error)
    }

    // 更新状态
    userActions.setLoginState(userData.openId, userData.isAdmin, userData.balance)
  },

  /**
   * 用户退出登录
   */
  completeLogout() {
    // 清理本地存储
    try {
      wx.removeStorageSync('auth_token')
      wx.removeStorageSync('user_openid')
      wx.removeStorageSync('is_admin')
    } catch (error) {
      console.warn('Failed to clear user data from storage:', error)
    }

    // 清理状态
    userActions.logout()
    businessActions.clearCalendarData()
    businessActions.clearOrdersCache()
    uiActions.clearAllLoading()
  }
}

/**
 * 导出所有操作
 */
export const actions = {
  user: userActions,
  app: appActions,
  business: businessActions,
  ui: uiActions,
  combined: combinedActions
}

export default actions