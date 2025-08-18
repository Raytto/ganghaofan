Page({
    data: {
        darkMode: true,
        themeClass: ''
    },
    onShow() {
        const tab = (this as any).getTabBar && (this as any).getTabBar()
        if (tab && typeof (tab as any).updateSelected === 'function') {
            (tab as any).updateSelected()
        }
        
        // 加载当前主题状态
        const app = getApp<IAppOption>()
        if (app && app.globalData) {
            const darkMode = !!app.globalData.darkMode
            this.setData({ 
                darkMode: darkMode,
                themeClass: darkMode ? '' : 'light-theme'
            })
        }
    },
    onToggleDarkMode(e: WechatMiniprogram.SwitchChange) {
        const checked = !!(e && (e.detail as any).value)
        const app = getApp<IAppOption>()
        if (app && app.switchTheme) {
            app.switchTheme(checked)
        }
        this.setData({ 
            darkMode: checked,
            themeClass: checked ? '' : 'light-theme'
        })
        // 反馈
        wx.showToast({ title: checked ? '深色模式已开启' : '浅色模式已开启', icon: 'none' })
    }
})
