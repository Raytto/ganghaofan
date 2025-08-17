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
            const cur = pages[pages.length - 1]
            if (!cur || !cur.route) return
            const path = '/' + cur.route
            const idx = this.data.list.findIndex(i => i.pagePath === path)
            if (idx >= 0) this.setData({ selected: idx })
        },
        switchTab(e) {
            const idx = e.currentTarget.dataset.index
            const item = this.data.list[idx]
            if (!item) return
            wx.switchTab({ url: item.pagePath })
        }
    }
})
