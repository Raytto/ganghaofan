// app.ts
import { loginAndGetToken } from './utils/api'

App<IAppOption>({
  globalData: {
    debugMode: true,
    isAdmin: true,
    adminViewEnabled: true,
    darkMode: true, // 默认深色模式开启
  },
  onLaunch() {
    // 环境：develop | trial | release
    const account = wx.getAccountInfoSync && wx.getAccountInfoSync()
    const env = account && account.miniProgram && account.miniProgram.envVersion
    const debugMode = env === 'develop'

    // 本地持久化的管理视图开关
    const adminViewEnabled = !!wx.getStorageSync('admin_view_enabled')
    // 非调试环境下，也可支持手动存一个 is_admin 标记（留作后端鉴权接入前的临时方案）
    const storedAdmin = !!wx.getStorageSync('is_admin')
    const isAdmin = debugMode || storedAdmin

    // 主题模式持久化，默认深色模式
    const storedDarkMode = wx.getStorageSync('dark_mode')
    const darkMode = storedDarkMode !== null ? !!storedDarkMode : true

    this.globalData.debugMode = debugMode
    this.globalData.isAdmin = isAdmin
    this.globalData.adminViewEnabled = adminViewEnabled
    this.globalData.darkMode = darkMode

    // 登录并缓存 token（静态导入，避免动态导入在 appservice 中报错）
    loginAndGetToken().catch(err => {
      console.error('login failed', err)
    })
  },
  // 主题切换方法
  switchTheme(darkMode: boolean) {
    this.globalData.darkMode = darkMode
    wx.setStorageSync('dark_mode', darkMode)
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
  }
})