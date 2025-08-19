Component({
    data: {
        selected: 0,
        list: [
            { pagePath: '/pages/admin/index', text: '管理' },
            { pagePath: '/pages/calender/index', text: '点餐' },
            { pagePath: '/pages/profile/index', text: '我的' }
        ] as Array<{ pagePath: string; text: string }>,
        themeClass: '',
        darkMode: true,
    },
    lifetimes: {
        attached(this: any) {
            this.updateSelected()
            // 初始化主题
            const app = getApp<IAppOption>()
            const darkMode = app?.globalData?.darkMode !== false
            this.setData({
                darkMode: darkMode,
                themeClass: darkMode ? '' : 'light-theme'
            })
        }
    },
    methods: {
        updateSelected(this: any) {
            const pages = getCurrentPages()
            if (!pages || pages.length === 0) return
            const cur = pages[pages.length - 1] as any
            const path = '/' + (cur?.route ?? '')
            if (!path || path === '/') return
            const idx = this.data.list.findIndex((i: { pagePath: string }) => i.pagePath === path)
            if (idx >= 0) this.setData({ selected: idx })
        },
        switchTab(this: any, e: WechatMiniprogram.TouchEvent) {
            const idxRaw = (e.currentTarget as any).dataset.index
            const idx = typeof idxRaw === 'number' ? idxRaw : Number(idxRaw)
            const item = this.data.list[idx]
            if (!item) return
            wx.switchTab({ url: item.pagePath })
        }
    }
})
Component({
    data: {
        selected: 0,
        list: [
            { pagePath: '/pages/admin/index', text: '管理' },
            { pagePath: '/pages/calender/index', text: '点餐' },
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
