Page({
    data: {},
    onShow() {
        const tab = (this as any).getTabBar && (this as any).getTabBar()
        if (tab && typeof (tab as any).updateSelected === 'function') {
            (tab as any).updateSelected()
        }
    }
})
Page({
    data: {},
    onShow() {
        const tab = (this.getTabBar && this.getTabBar())
        if (tab && typeof tab.updateSelected === 'function') {
            tab.updateSelected()
        }
    }
})
