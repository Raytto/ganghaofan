/**
 * 个人中心页面 - Phase 2 增强版
 * 集成新的状态管理和用户API
 */
import { UserAPI } from '../../core/api/user'
import { createPageReactive, stateManager, actions } from '../../core/store'
import { formatCurrency, formatDate } from '../../utils/date'

Page({
  // 混入响应式功能
  ...createPageReactive(),

  data: {
    userInfo: null,
    userStats: null,
    balanceHistory: [],
    orderHistory: [],
    theme: null,
    loading: true,
    
    // 标签页状态
    activeTab: 'overview', // overview, orders, balance
    
    // 分页状态
    orderPage: { limit: 20, offset: 0, hasMore: true },
    balancePage: { limit: 20, offset: 0, hasMore: true },
    
    // 状态数据
    darkMode: false,
    isAdmin: false,
    balance: 0
  },

  onLoad() {
    // 绑定状态
    this.bindState({
      darkMode: 'app.darkMode',
      isAdmin: 'user.isAdmin',
      balance: 'user.balance'
    })
    
    this.initPage()
  },

  onShow() {
    const tab = (this as any).getTabBar && (this as any).getTabBar()
    if (tab && typeof (tab as any).updateSelected === 'function') {
      (tab as any).updateSelected()
    }

    this.refreshData()
  },

  onPullDownRefresh() {
    this.refreshData().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  onReachBottom() {
    this.loadMoreData()
  },

  async initPage() {
    // 主题类名根据状态自动更新
    const darkMode = stateManager.getState<boolean>('app.darkMode')
    this.setData({
      themeClass: darkMode ? '' : 'light-theme'
    })

    await this.refreshData()
  },

  async refreshData() {
    try {
      this.setData({ loading: true })

      // 并行加载数据
      const [profileResult, orderResult, balanceResult] = await Promise.all([
        this.loadUserProfile(),
        this.loadOrderHistory(true),
        this.loadBalanceHistory(true)
      ])

      this.setData({
        loading: false
      })

    } catch (error) {
      console.error('加载用户数据失败:', error)
      this.setData({ loading: false })
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      })
    }
  },

  async loadUserProfile() {
    const result = await UserAPI.getUserProfile()
    if (result.success) {
      this.setData({
        userInfo: result.data.user_info,
        userStats: {
          recent: result.data.recent_activity,
          lifetime: result.data.lifetime_stats
        }
      })
      
      // 更新全局用户信息
      actions.user.updateBalance(result.data.user_info.balance_cents)
      actions.user.setAdminStatus(result.data.user_info.is_admin)
    }
    return result
  },

  async loadOrderHistory(refresh = false) {
    const { orderPage } = this.data
    
    if (refresh) {
      orderPage.offset = 0
      orderPage.hasMore = true
    }

    if (!orderPage.hasMore) return

    const result = await UserAPI.getOrderHistory({
      limit: orderPage.limit,
      offset: orderPage.offset
    })

    if (result.success) {
      const newOrders = result.data.orders
      const existingOrders = refresh ? [] : this.data.orderHistory
      
      this.setData({
        orderHistory: [...existingOrders, ...newOrders],
        orderPage: {
          ...orderPage,
          offset: orderPage.offset + newOrders.length,
          hasMore: result.data.page_info.has_more
        }
      })
    }

    return result
  },

  async loadBalanceHistory(refresh = false) {
    const { balancePage } = this.data
    
    if (refresh) {
      balancePage.offset = 0
      balancePage.hasMore = true
    }

    if (!balancePage.hasMore) return

    const result = await UserAPI.getBalanceHistory({
      limit: balancePage.limit,
      offset: balancePage.offset
    })

    if (result.success) {
      const newHistory = result.data.history
      const existingHistory = refresh ? [] : this.data.balanceHistory
      
      this.setData({
        balanceHistory: [...existingHistory, ...newHistory],
        balancePage: {
          ...balancePage,
          offset: balancePage.offset + newHistory.length,
          hasMore: result.data.page_info.has_more
        }
      })
    }

    return result
  },

  async loadMoreData() {
    if (this.data.loading) return

    switch (this.data.activeTab) {
      case 'orders':
        await this.loadOrderHistory(false)
        break
      case 'balance':
        await this.loadBalanceHistory(false)
        break
    }
  },

  onTabSwitch(e: any) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })

    // 懒加载数据
    if (tab === 'orders' && this.data.orderHistory.length === 0) {
      this.loadOrderHistory(true)
    } else if (tab === 'balance' && this.data.balanceHistory.length === 0) {
      this.loadBalanceHistory(true)
    }
  },

  onToggleTheme() {
    actions.app.toggleDarkMode()
    
    // 更新主题类名
    const darkMode = stateManager.getState<boolean>('app.darkMode')
    this.setData({
      themeClass: darkMode ? '' : 'light-theme'
    })
  },

  onViewOrderDetail(e: any) {
    const orderId = e.currentTarget.dataset.orderId
    wx.navigateTo({
      url: `/pages/order/detail?orderId=${orderId}`
    })
  },

  onExportData() {
    wx.showActionSheet({
      itemList: ['导出订单历史', '导出余额记录'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.exportOrderHistory()
        } else if (res.tapIndex === 1) {
          this.exportBalanceHistory()
        }
      }
    })
  },

  async exportOrderHistory() {
    wx.showLoading({ title: '导出中...' })
    
    try {
      const result = await UserAPI.exportOrderHistory()
      if (result.success) {
        wx.showToast({
          title: '导出成功',
          icon: 'success'
        })
      }
    } catch (error) {
      wx.showToast({
        title: '导出失败',
        icon: 'error'
      })
    } finally {
      wx.hideLoading()
    }
  },

  async exportBalanceHistory() {
    wx.showLoading({ title: '导出中...' })
    
    try {
      const result = await UserAPI.exportBalanceHistory()
      if (result.success) {
        wx.showToast({
          title: '导出成功',
          icon: 'success'
        })
      }
    } catch (error) {
      wx.showToast({
        title: '导出失败',
        icon: 'error'
      })
    } finally {
      wx.hideLoading()
    }
  },

  onShareProfile() {
    return {
      title: '我的罡好饭账户',
      path: '/pages/index/index'
    }
  },

  // 格式化货币显示
  formatCurrency(cents: number): string {
    return `¥${(cents / 100).toFixed(2)}`
  },

  // 格式化日期显示
  formatDate(dateString: string): string {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) return '今天'
    if (days === 1) return '昨天'
    if (days < 7) return `${days}天前`
    
    return formatDate(date, 'MM-DD')
  },

  // 获取订单状态文本
  getOrderStatusText(status: string): string {
    const statusMap = {
      'active': '已下单',
      'locked': '已锁定',
      'canceled': '已取消',
      'completed': '已完成',
      'refunded': '已退款'
    }
    return statusMap[status] || status
  },

  // 获取余额变动类型文本
  getBalanceTypeText(amount: number, description: string): string {
    if (amount > 0) {
      return description.includes('充值') ? '充值' : '退款'
    } else {
      return description.includes('订单') ? '消费' : '扣费'
    }
  }
})