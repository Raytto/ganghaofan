Page({
    data: {
        adminViewEnabled: false,
        canAdmin: false,
    },
    onShow() {
        // tab selected state
        const tab = (this as any).getTabBar && (this as any).getTabBar()
        if (tab && typeof (tab as any).updateSelected === 'function') {
            (tab as any).updateSelected()
        }
        // permission check and load toggle
        const app = getApp<IAppOption>()
        const canAdmin = !!(app.globalData && (app.globalData.debugMode || app.globalData.isAdmin))
        this.setData({
            canAdmin,
            adminViewEnabled: !!(app.globalData && app.globalData.adminViewEnabled)
        })
        if (!canAdmin) {
            wx.showToast({ title: '没有管理权限', icon: 'none' })
        }
    },
    onToggleAdminView(e: WechatMiniprogram.SwitchChange) {
        const checked = !!(e && (e.detail as any).value)
        const app = getApp<IAppOption>()
        if (app && app.globalData) {
            app.globalData.adminViewEnabled = checked
            wx.setStorageSync('admin_view_enabled', checked)
        }
        this.setData({ adminViewEnabled: checked })
        // 反馈
        wx.showToast({ title: checked ? '管理视图已开启' : '管理视图已关闭', icon: 'none' })
    }
})
