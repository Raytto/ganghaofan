import { api } from '../../utils/api'

Page({
    data: {
        darkMode: true,
        themeClass: '',
        balance: 0,
        loadingBalance: false
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
        
        // 加载用户余额
        this.loadBalance()
    },
    async loadBalance() {
        this.setData({ loadingBalance: true })
        try {
            const response = await api.request<{ user_id: number, balance_cents: number }>('/users/me/balance')
            this.setData({ 
                balance: response.balance_cents / 100 // 转换为元
            })
        } catch (error) {
            console.error('加载余额失败:', error)
            wx.showToast({ 
                title: '加载余额失败', 
                icon: 'none',
                duration: 2000
            })
        } finally {
            this.setData({ loadingBalance: false })
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
    },
    onGoToLogs() {
        wx.navigateTo({
            url: '/pages/logs/logs'
        })
    }
})
