// index-page.ts - 首页页面包装器
import { stateManager, actions } from '../../core/store/index'

Page({
  data: {
    // 主题相关
    themeClass: '',
    darkMode: true,
  },

  onLoad() {
    // 初始化主题
    const app = getApp<IAppOption>()
    const darkMode = app?.globalData?.darkMode !== false

    this.setData({
      themeClass: darkMode ? '' : 'light-theme',
      darkMode: darkMode
    })
  },

  onShow() {
    // 更新自定义tabbar
    const tab = (this as any).getTabBar && (this as any).getTabBar()
    if (tab && typeof tab.updateSelected === 'function') {
      tab.updateSelected()
    }
  }
})