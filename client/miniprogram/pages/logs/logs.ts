import { api } from '../../utils/api'

type LogItem = {
  log_id: number
  action: string
  detail: any
  created_at: string
}

Component({
  data: {
    logs: [] as LogItem[],
    loading: false,
    hasMore: true,
    nextCursor: null as number | null,
    darkMode: true,
    themeClass: ''
  },
  lifetimes: {
    attached() {
      // 加载主题状态
      const app = getApp<IAppOption>()
      if (app && app.globalData) {
        const darkMode = !!app.globalData.darkMode
        this.setData({ 
          darkMode: darkMode,
          themeClass: darkMode ? '' : 'light-theme'
        })
      }
      
      this.loadLogs(true)
    }
  },
  methods: {
    async loadLogs(reset = false) {
      if (this.data.loading) return
      
      this.setData({ loading: true })
      
      try {
        const cursor = reset ? null : this.data.nextCursor
        const limit = 200  // 根据需求，默认展示200条
        
        const response = await api.request<{
          items: LogItem[],
          next: number | null
        }>(`/logs/my?limit=${limit}${cursor ? `&cursor=${cursor}` : ''}`)
        
        const newLogs = reset ? response.items : [...this.data.logs, ...response.items]
        
        this.setData({
          logs: newLogs,
          hasMore: !!response.next,
          nextCursor: response.next
        })
      } catch (error) {
        console.error('加载日志失败:', error)
        wx.showToast({ 
          title: '加载日志失败', 
          icon: 'none',
          duration: 2000
        })
      } finally {
        this.setData({ loading: false })
      }
    },
    
    onScrollToLower() {
      if (this.data.hasMore && !this.data.loading) {
        this.loadLogs(false)
      }
    }
  }
})
