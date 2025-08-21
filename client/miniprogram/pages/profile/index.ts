import { api, getDbKey } from '../../utils/api'
import { promptPassphrase } from '../../utils/passphrase'
import { createPageReactive, stateManager, actions } from '../../core/store/index'

Page({
    // 混入响应式功能
    ...createPageReactive(),

    data: {
        darkMode: true,
        themeClass: '',
        balance: 0,
        loadingBalance: false,
        dbKey: '',
        user: {} as any,
        isAdmin: false
    },
    onLoad() {
        // 绑定状态
        this.bindState({
            darkMode: 'app.darkMode',
            isAdmin: 'user.isAdmin',
            balance: 'user.balance'
        })
    },

    onShow() {
        const tab = (this as any).getTabBar && (this as any).getTabBar()
        if (tab && typeof (tab as any).updateSelected === 'function') {
            (tab as any).updateSelected()
        }

        // 主题类名根据状态自动更新
        const darkMode = stateManager.getState<boolean>('app.darkMode')
        this.setData({
            themeClass: darkMode ? '' : 'light-theme'
        })

        // 加载用户信息和余额
        this.loadUser()
        this.loadBalance()

        // 显示当前DB key
        const dbKey = getDbKey() || ''
        this.setData({ dbKey })
        if (!dbKey) {
            promptPassphrase().then(key => { if (key) this.setData({ dbKey: key }) })
        }
    },
    async loadUser() {
        try {
            const u = await api.request<any>('/users/me')
            // 兼容开发：如果后端开启mock但未返回昵称，可从/env/mock补齐
            if (!u?.nickname) {
                try {
                    const mock = await api.request<any>('/env/mock', { method: 'GET' })
                    if (mock?.mock_enabled && mock?.nickname) {
                        u.nickname = mock.nickname
                    }
                } catch { }
            }
            this.setData({ user: u })
        } catch (e) {
            console.warn('加载用户信息失败', e)
        }
    },
    async loadBalance() {
        this.setData({ loadingBalance: true })
        try {
            const response = await api.request<{ user_id: number, balance_cents: number }>('/users/me/balance')
            const balanceInYuan = response.balance_cents / 100
            
            // 更新全局状态
            actions.user.updateBalance(balanceInYuan)
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
    async onSetPassphrase() {
        const key = await promptPassphrase()
        if (key) this.setData({ dbKey: key })
    },
    onToggleDarkMode(e: WechatMiniprogram.SwitchChange) {
        const checked = !!(e && (e.detail as any).value)
        
        // 使用新的状态管理
        actions.app.setDarkMode(checked)
        
        // 更新主题类名
        this.setData({
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
