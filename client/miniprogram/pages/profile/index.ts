Page({
    data: {
        darkMode: true
    },
    onShow() {
        const tab = (this as any).getTabBar && (this as any).getTabBar()
        if (tab && typeof (tab as any).updateSelected === 'function') {
            (tab as any).updateSelected()
        }
        
        // 加载当前主题状态
        const app = getApp<IAppOption>()
        if (app && app.globalData) {
            this.setData({ darkMode: !!app.globalData.darkMode })
        }
    },
    onToggleDarkMode(e: WechatMiniprogram.SwitchChange) {
        const checked = !!(e && (e.detail as any).value)
        const app = getApp<IAppOption>()
        if (app && app.globalData) {
            app.globalData.darkMode = checked
            wx.setStorageSync('dark_mode', checked)
        }
        this.setData({ darkMode: checked })
        // 反馈
        wx.showToast({ title: checked ? '深色模式已开启' : '浅色模式已开启', icon: 'none' })
    }
})
