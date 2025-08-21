// app.ts
import { loginAndGetToken } from './utils/api'
import { stateManager, actions } from './core/store/index'
import { API_CONFIG } from './core/constants/api'

// 调试信息 - 确认API配置
console.log('=== 应用启动调试信息 ===')
console.log('API_CONFIG.BASE_URL:', API_CONFIG.BASE_URL)
console.log('时间戳:', new Date().toISOString())
console.log('========================')

App<IAppOption>({
  globalData: {
    // 保留兼容性，逐步迁移到新状态管理
    debugMode: true,
    isAdmin: true,
    adminViewEnabled: true,
    darkMode: false, // 默认浅色模式，与状态管理保持一致
  },
  
  async onLaunch() {
    // 初始化状态管理系统
    await actions.combined.initializeApp()
    
    // 环境：develop | trial | release
    const account = wx.getAccountInfoSync && wx.getAccountInfoSync()
    const env = account && account.miniProgram && account.miniProgram.envVersion
    const debugMode = env === 'develop'

    // 更新应用状态
    actions.app.setDebugMode(debugMode)

    // 同步到 globalData 保持兼容性
    this.syncStateToGlobalData()
    
    // 监听状态变化，同步到 globalData
    stateManager.onStateChange((state, changedPath) => {
      this.syncStateToGlobalData()
      
      // 处理主题切换
      if (changedPath === 'app.darkMode') {
        this.handleThemeChange(state.app.darkMode)
      }
    })

    // 登录并缓存 token
    try {
      await loginAndGetToken()
    } catch (err) {
      console.error('login failed', err)
    }
  },

  // 同步状态到 globalData
  syncStateToGlobalData() {
    const state = stateManager.getState()
    this.globalData.debugMode = state.app.debugMode
    this.globalData.isAdmin = state.user.isAdmin
    this.globalData.adminViewEnabled = state.app.adminViewEnabled
    this.globalData.darkMode = state.app.darkMode
  },

  // 处理主题变化
  handleThemeChange(darkMode: boolean) {
    // 通知所有页面更新主题
    const pages = getCurrentPages()
    pages.forEach(page => {
      if (page.setData) {
        page.setData({
          themeClass: darkMode ? '' : 'light-theme',
          darkMode: darkMode
        })
      }
      // 更新自定义tab bar主题
      const tabbar = (page as any).getTabBar && (page as any).getTabBar()
      if (tabbar && tabbar.setData) {
        tabbar.setData({
          themeClass: darkMode ? '' : 'light-theme',
          darkMode: darkMode
        })
      }
    })
  },

  // 主题切换方法（保持向后兼容）
  switchTheme(darkMode: boolean) {
    actions.app.setDarkMode(darkMode)
  }
})