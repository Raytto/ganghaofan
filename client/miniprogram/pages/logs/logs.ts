import { api } from '../../utils/api'

type LogItem = {
  log_id: number
  action: string
  detail: any
  created_at: string
}

type UILogItem = LogItem & {
  dateStr: string
  timeStr: string
  actionLabel: string
  detailText: string
  operatorName: string
  operatorId: string
}

function formatTimeParts(iso: string): { date: string; time: string } {
  if (!iso) return { date: '', time: '' }
  const d = new Date(iso)
  const pad = (n: number) => (n < 10 ? '0' + n : '' + n)
  const date = `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())}`
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  return { date, time }
}

function formatAction(action: string): string {
  const map: Record<string, string> = {
    order_create: '下单',
    order_cancel: '取消订单',
    order_modify: '修改订单',
    recharge: '充值',
    meal_publish: '发布餐次',
    meal_cancel: '取消餐次',
    meal_lock: '锁定餐次',
    meal_unlock: '解锁餐次',
    meal_complete: '完成餐次',
    meal_edit: '编辑餐次',
  }
  return map[action] || action
}

function formatLogContent(action: string, detail: any): string {
  if (!detail) return '操作详情'
  try {
    const d = typeof detail === 'string' ? JSON.parse(detail) : detail
    const yuan = (cents?: number) => {
      const v = Number(cents || 0) / 100
      return (Number.isInteger(v) ? v.toFixed(0) : v.toFixed(2))
    }
    const slotLabel = (s?: string) => (s === 'lunch' ? '午餐' : '晚餐')
    const mealTime = () => {
      const date = (d.date || d.meal_date || '').replace(/-/g, '/')
      const slot = slotLabel(d.slot || d.meal_slot)
      return `${date} ${slot}`
    }
    const listOptions = () => {
      const arr = (d.options || d.meal_options || d.selected_options || []) as any[]
      if (!Array.isArray(arr) || arr.length === 0) return '无'
      return arr
        .map((op: any) => {
          const name = op?.name || op?.option_name || ''
          const price = op?.price_cents ?? op?.priceCent ?? op?.price
          return `${name}${price != null ? ` ¥${yuan(Number(price))}` : ''}`
        })
        .join('、')
    }

    switch (action) {
      case 'order_create': {
        const amount = d.total_amount_cents ?? d.amount_cents
        const before = d.balance_before_cents ?? d.balance_before
        const after = d.balance_after_cents ?? d.balance_after
        const opts = listOptions()
        return `订餐：${mealTime()} · 选项：${opts} · 金额¥${yuan(amount)} · 余额：¥${yuan(before)} → ¥${yuan(after)}`
      }
      case 'order_cancel': {
        const amount = d.total_amount_cents ?? d.amount_cents ?? d.refund_cents
        const before = d.balance_before_cents ?? d.balance_before
        const after = d.balance_after_cents ?? d.balance_after
        const opts = listOptions()
        return `取消订单：${mealTime()} · 选项：${opts} · 金额¥${yuan(amount)} · 余额：¥${yuan(before)} → ¥${yuan(after)}`
      }
      case 'recharge': {
        const amt = d.amount_cents ?? d.recharge_cents
        const bal = d.balance_after_cents ?? d.balance
        const name = d.user_nickname || d.nickname || ''
        const oid = d.user_open_id || d.open_id || ''
        return `充值：¥${yuan(amt)} · 余额：¥${yuan(bal)} · 用户：${name}${oid ? `（${oid}）` : ''}`
      }
      case 'meal_publish': {
        const price = d.base_price_cents ?? d.price_cents
        const cap = d.capacity
        const desc = d.description || d.desc || ''
        const opts = listOptions()
        return `发布餐次：${mealTime()} · 描述：${desc} · 价格：¥${yuan(price)} · 限制：${cap}份 · 选项：${opts}`
      }
      case 'meal_edit': {
        const price = d.base_price_cents ?? d.price_cents
        const cap = d.capacity
        const desc = d.description || d.desc || ''
        const opts = listOptions()
        return `编辑餐次(修改)：${mealTime()} · 描述：${desc} · 价格：¥${yuan(price)} · 限制：${cap}份 · 选项：${opts}`
      }
      case 'meal_cancel': {
        const affected = (d.affected_users || d.affected || []) as any[]
        const names = Array.isArray(affected)
          ? affected.map((u: any) => u?.nickname || u?.user_nickname || u?.name || '').filter(Boolean)
          : []
        const count = d.affected_count ?? names.length
        const list = names.length ? `：${names.join('、')}` : ''
        return `取消餐次：${mealTime()} · 受影响${count}人${list}`
      }
      case 'meal_lock':
        return `锁定餐次：${mealTime()}`
      case 'meal_unlock':
        return `解锁餐次：${mealTime()}`
      case 'meal_complete':
        return `完成餐次：${mealTime()}`
      default:
        return typeof d === 'object' ? JSON.stringify(d) : String(d)
    }
  } catch (e) {
    return String(detail)
  }
}

Page({
  data: {
    logs: [] as UILogItem[],
    loading: false,
    hasMore: true,
    nextCursor: null as number | null,
    darkMode: true,
    themeClass: ''
  },
  onShow() {
    // 加载主题状态
    const app = getApp<IAppOption>()
    if (app && app.globalData) {
      const darkMode = !!app.globalData.darkMode
      this.setData({
        darkMode,
        themeClass: darkMode ? '' : 'light-theme',
      })
    }
    try { wx.showLoading({ title: '加载中...', mask: true }) } catch { }
    this.loadLogs(true)
  },
  async loadLogs(reset = false) {
    if (this.data.loading) return
    this.setData({ loading: true })
    try {
      const cursor = reset ? null : this.data.nextCursor
      const limit = 200
      const response = await api.request<{
        items: (LogItem & { actor_nickname?: string; actor_open_id?: string })[]
        next: number | null
      }>(`/logs/my?limit=${limit}${cursor ? `&cursor=${cursor}` : ''}`)
      const mapped: UILogItem[] = (response.items || []).map((it) => {
        const t = formatTimeParts(it.created_at)
        return {
          ...it,
          dateStr: t.date,
          timeStr: t.time,
          actionLabel: formatAction(it.action),
          detailText: formatLogContent(it.action, it.detail),
          operatorName: it.actor_nickname || '我',
          operatorId: it.actor_open_id || '',
        }
      })
      const newLogs = reset ? mapped : [...this.data.logs, ...mapped]
      this.setData({
        logs: newLogs,
        hasMore: !!response.next,
        nextCursor: response.next,
      })
    } catch (error) {
      console.error('加载日志失败:', error)
      wx.showToast({ title: '加载日志失败', icon: 'none', duration: 2000 })
    } finally {
      this.setData({ loading: false })
      try { wx.hideLoading() } catch { }
    }
  },
  onScrollToLower() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadLogs(false)
    }
  },
})
