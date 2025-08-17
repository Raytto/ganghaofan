Component({
    data: {
        selected: 0,
        list: [
            { pagePath: '/pages/admin/index', text: '管理' },
            { pagePath: '/pages/index/index', text: '点餐' },
            { pagePath: '/pages/profile/index', text: '我的' }
        ]
    },
    lifetimes: {
        attached() {
            this.updateSelected()
        }
    },
    methods: {
        updateSelected() {
            const pages = getCurrentPages()
            if (!pages || pages.length === 0) return
            const cur = pages[pages.length - 1] as any
            if (!cur || !cur.route) return
            const path = '/' + cur.route
            const idx = (this.data as any).list.findIndex((i: any) => i.pagePath === path)
            if (idx >= 0) this.setData({ selected: idx })
        },
        switchTab(e: WechatMiniprogram.TouchEvent) {
            const { index } = (e.currentTarget.dataset || {}) as any
            const item = (this.data as any).list[index]
            if (!item) return
            if (item.pagePath === '/pages/admin/index') {
                const app = getApp<IAppOption>()
                const canAdmin = !!(app.globalData && (app.globalData.debugMode || app.globalData.isAdmin))
                if (!canAdmin) {
                    wx.showToast({ title: '没有管理权限', icon: 'none' })
                    return
                }
            }
            wx.switchTab({ url: item.pagePath })
        }
    }
})
