/**
 * 首页日历组件 - 核心页面逻辑
 * 
 * 功能概述：
 * - 展示工作日（周一至周五）的9周窗口日历视图
 * - 支持平滑的滑动翻页和吸附定位
 * - 管理员/用户模式切换，支持餐次发布和订单管理
 * - 数据缓存和预加载机制，减少网络请求
 * 
 * 核心特性：
 * - 9周窗口：预加载前3周+当前3周+后3周的数据
 * - 吸附滚动：每次滑动跨越3周，自动居中定位
 * - 双模式：用户模式查看和下单，管理员模式发布和管理
 * - 弹窗组件：集成发布弹窗和订单弹窗
 */

// index.ts
import { api, getCalendarBatch } from '../../utils/api'
import { loginAndGetToken } from '../../utils/api'
import { getDbKey } from '../../utils/api'
import { promptPassphrase } from '../../utils/passphrase'
import { formatMonth, formatDate, parseDate, getMondayStart, startOfMonth, addMonths, monthsBetween, windowMonthsForNineWeeks } from '../../utils/date'
import { toSlotView } from '../../utils/slotView'

Component({
  data: {
    // 时间和标签相关
    month: formatMonth(),
    anchorDate: formatDate(new Date()),
    monthLabel: '',
    yearLabel: '',
    monthOnlyLabel: '',
    fullLabel: '',
    todayCnLabel: '',

    // 餐次数据
    meals: [] as any[],
    week: [] as any[],
    prevWeek: [] as any[],
    nextWeek: [] as any[],
    weeks9: [] as any[], // 9周窗口数据：[3 prev, 3 current, 3 next]

    // UI状态
    loading: false,
    tip: '',

    // 触摸和滚动控制
    _touchY: 0,
    _touchX: 0,
    _touchTime: 0,
    blockH: 0, // 视口高度，用于计算滚动距离
    trackY: 0, // 当前滚动位移
    trackAnimate: false, // 是否启用滚动动画
    _pageOffset: 0, // 页面偏移量：-1, 0, +1
    trackBase: 0, // 基础偏移量，用于保持当前3周居中
    trackHeight: 0, // 3页高度（1页=blockH）

    // 模式和权限
    adminView: false, // 是否为管理员视图
    canAdmin: false, // 是否具有管理员权限

    // 发布弹窗相关
    showPublish: false,
    publishMode: 'create' as 'create' | 'edit',
    publishMealId: null as number | null,
    publishOriginal: null as any,
    publishNeedsRepost: false, // 是否需要危险重发
    publishReadonly: false,
    submittingPublish: false,

    // 订单弹窗相关  
    showOrder: false,
    orderDetail: {} as any,

    // 最近一次点击的日期和餐次（用于发布时自动填充）
    lastPublishDate: '' as string,
    lastPublishSlot: '' as any as 'lunch' | 'dinner' | '',

    // 发布表单数据
    publishForm: {
      date: '',
      slot: 'lunch',
      description: '',
      basePrice: 20, // 单位：元
      capacity: 50,
      options: [] as { id: string; name: string; price: number }[],
    },

    // 主题相关
    themeClass: '',
    darkMode: true,
  },

  lifetimes: {
    attached() {
      const m = this.data.month

      // 初始化主题
      const app = getApp<IAppOption>()
      const darkMode = app?.globalData?.darkMode !== false

      this.setData({
        monthLabel: m.replace('-', '年') + '月',
        yearLabel: m.split('-')[0] + '年',
        monthOnlyLabel: m.split('-')[1].replace(/^0/, '') + '月',
        fullLabel: m.replace('-', '年') + '月',
        todayCnLabel: this.formatCnDate(new Date()),
        themeClass: darkMode ? '' : 'light-theme',
        darkMode: darkMode
      })
        // init caches
        ; (this as any)._byKey = new Map<string, any>()
        ; (this as any)._loadedMonths = new Set<string>()
        ; (this as any)._dbKeyPrev = getDbKey() || ''
      // set adminView and slogan based on app global toggle & permission
      this.refreshAdminBindings()
        ; (this as any)._lastRefreshTs = 0
        ; (this as any)._refreshingSwipe = false
      // 如果未设置口令，优先弹窗并跳过首次数据加载，待设置后再刷新
      const dbKey = getDbKey()
      if (!dbKey) {
        wx.nextTick(() => this.measureViewportAndCenter())
        setTimeout(() => this.promptPassphraseOnCalendar(), 50)
        return
      }
      // 已有口令则正常加载
      this.loadWeek(this.data.anchorDate, { preload3Months: true })
      // After first render, measure viewport and center the track
      wx.nextTick(() => this.measureViewportAndCenter())
    }
  },
  methods: {
    // 口令相关：弹窗并在设置后刷新当前日历
    async promptPassphraseOnCalendar() {
      const key = await promptPassphrase()
      if (key) this.onDbKeyChanged(key || '')
    },
    onDbKeyChanged(newKey: string) {
      ; (this as any)._dbKeyPrev = newKey || ''
      // 清理旧缓存与视图测量值，避免沿用错误的高度与基线
      this.resetCalendarCache()
      this.setData({ blockH: 0, trackBase: 0, trackY: 0, trackAnimate: false, _pageOffset: 0, trackHeight: 0 })
      // 基于新数据库强制刷新当前锚点的三月预载窗口
      this.loadWeek(this.data.anchorDate, { preload3Months: true, force: true })
      // 确保在新数据渲染后重新测量并居中到中页
      wx.nextTick(() => this.measureViewportAndCenter())
    },
    resetCalendarCache() {
      ; (this as any)._byKey = new Map<string, any>()
        ; (this as any)._loadedMonths = new Set<string>()
        ; (this as any)._lastRefreshTs = 0
    },
    formatCnDate(d: Date) {
      const y = d.getFullYear()
      const m = `${d.getMonth() + 1}`.padStart(2, '0')
      const day = `${d.getDate()}`.padStart(2, '0')
      return `${y}年${m}月${day}日`
    },
    refreshAdminBindings() {
      const app = getApp<IAppOption>()
      const canAdmin = !!(app.globalData && (app.globalData.debugMode || app.globalData.isAdmin))
      const adminView = !!(app.globalData && app.globalData.adminViewEnabled && canAdmin)
      this.setData({ adminView, canAdmin })
    },
    onToggleAdminView() {
      const app = getApp<IAppOption>()
      const canAdmin = !!(app.globalData && (app.globalData.debugMode || app.globalData.isAdmin))
      if (!canAdmin) return
      const next = !this.data.adminView
      if (app.globalData) {
        app.globalData.adminViewEnabled = next
      }
      wx.setStorageSync('admin_view_enabled', next)
      this.setData({ adminView: next })
      // 如需立即切换视图数据，可解开下一行
      // this.loadWeek(this.data.anchorDate, { silent: true })
    },
    // ---------- Admin Publish Dialog ----------
    openPublishDialog(dateStr: string, slot: 'lunch' | 'dinner') {
      // initialize form defaults
      this.setData({
        showPublish: true,
        publishMode: 'create',
        publishMealId: null,
        publishOriginal: null,
        publishNeedsRepost: false,
        publishReadonly: false,
        publishForm: {
          date: dateStr,
          slot,
          description: '',
          basePrice: 20,
          capacity: 50,
          options: [],
        },
        lastPublishDate: dateStr,
        lastPublishSlot: slot,
      })
    },
    async openEditPublishDialog(mealId: number) {
      try {
        await this.ensureLogin()
        const d: any = await api.request(`/meals/${mealId}`, { method: 'GET' })
        const form = {
          date: d.date,
          slot: d.slot,
          description: d.description || '',
          basePrice: Math.round((d.base_price_cents || 0) / 100),
          capacity: Number(d.capacity || 0),
          options: (d.options || []).map((o: any) => ({ id: String(o.id || ''), name: o.name || '', price: Math.round((o.price_cents || 0) / 100) })),
        }
        this.setData({
          showPublish: true,
          publishMode: 'edit',
          publishMealId: mealId,
          publishOriginal: { ...d },
          publishReadonly: d.status !== 'published',
          publishForm: form,
        })
        this.computePublishNeedsRepost()
      } catch (e: any) {
        wx.showToast({ title: e?.message || '加载失败', icon: 'none' })
      }
    },
    computePublishNeedsRepost() {
      const orig: any = (this.data as any).publishOriginal
      const form: any = (this.data as any).publishForm
      if (!orig || !form) { this.setData({ publishNeedsRepost: false }); return }
      // dangerous changes: price changed; capacity decreased below ordered; options deleted
      const priceChanged = Math.round((orig.base_price_cents || 0) / 100) !== Math.round((form.basePrice || 0))
      const ordered = Number(orig.ordered_qty || 0)
      const capacityDropBelowOrdered = Number(form.capacity || 0) < ordered
      const origIds = new Set((orig.options || []).map((o: any) => String(o.id || '')))
      const newIds = new Set((form.options || []).map((o: any) => String(o.id || '')))
      let deleted = false
      origIds.forEach(id => { if (id && !newIds.has(id)) deleted = true })
      const needs = !!(priceChanged || capacityDropBelowOrdered || deleted)
      this.setData({ publishNeedsRepost: needs })
    },
    closePublishDialog() {
      this.setData({ showPublish: false })
    },
    onPublishInput(e: WechatMiniprogram.CustomEvent) {
      const field = (e.detail as any)?.field as string
      const v = (e.detail as any)?.value as string
      if (!field) return
      const key = `publishForm.${field}`
      this.setData({ [key]: v })
      if (this.data.publishMode === 'edit') this.computePublishNeedsRepost()
    },
    onPublishNumberInput(e: WechatMiniprogram.CustomEvent) {
      const field = (e.detail as any)?.field as string
      if (!field) return
      let v = parseInt(((e.detail as any)?.value as string) || '0', 10)
      if (!Number.isFinite(v)) v = 0
      const key = `publishForm.${field}`
      this.setData({ [key]: v })
      if (this.data.publishMode === 'edit') this.computePublishNeedsRepost()
    },
    onAdjustNumber(e: WechatMiniprogram.CustomEvent) {
      const field = (e.detail as any)?.field as string
      const step = Number((e.detail as any)?.step || 1)
      if (!field || !Number.isFinite(step)) return
      const cur = (this.data as any).publishForm?.[field] || 0
      let v = cur + step
      if (field === 'basePrice') v = Math.max(0, v)
      if (field === 'capacity') v = Math.max(1, v)
      const key = `publishForm.${field}`
      this.setData({ [key]: v })
      if (this.data.publishMode === 'edit') this.computePublishNeedsRepost()
    },
    onAddOption() {
      const opts = (this.data as any).publishForm.options || []
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
      opts.push({ id, name: '', price: 0 })
      this.setData({ 'publishForm.options': opts })
    },
    onRemoveOption(e: WechatMiniprogram.CustomEvent) {
      const idx = Number((e.detail as any)?.idx)
      const opts = ((this.data as any).publishForm.options || []).slice()
      if (idx >= 0 && idx < opts.length) {
        opts.splice(idx, 1)
        this.setData({ 'publishForm.options': opts })
      }
    },
    onOptionInput(e: WechatMiniprogram.CustomEvent) {
      const idx = Number((e.detail as any)?.idx)
      const field = (e.detail as any)?.field as 'name' | 'price'
      const val = (e.detail as any)?.value as string
      const opts = ((this.data as any).publishForm.options || []).slice()
      if (!(idx >= 0 && idx < opts.length)) return
      if (field === 'name') {
        opts[idx].name = val
      } else if (field === 'price') {
        let p = parseInt(val || '0', 10)
        if (!Number.isFinite(p)) p = 0
        opts[idx].price = p
      }
      this.setData({ 'publishForm.options': opts })
      // recompute warning on edit mode
      if (this.data.publishMode === 'edit') this.computePublishNeedsRepost()
    },
    onAdjustOptionPrice(e: WechatMiniprogram.CustomEvent) {
      const idx = Number((e.detail as any)?.idx)
      const step = Number((e.detail as any)?.step || 1)
      const opts = ((this.data as any).publishForm.options || []).slice()
      if (!(idx >= 0 && idx < opts.length)) return
      let p = (opts[idx].price || 0) + step
      // option price allows negative
      opts[idx].price = p
      this.setData({ 'publishForm.options': opts })
      if (this.data.publishMode === 'edit') this.computePublishNeedsRepost()
    },
    async onPublishSubmit() {
      if (this.data.submittingPublish) { return }
      this.setData({ submittingPublish: true })
      const form = (this.data as any).publishForm
      try { wx.showLoading({ title: '提交中...', mask: true }) } catch { }
      if (!this.data.adminView) {
        wx.showToast({ title: '无权限', icon: 'none' })
        try { wx.hideLoading() } catch { }
        ; (this as any)._publishTmr && clearTimeout((this as any)._publishTmr)
        this.setData({ submittingPublish: false })
        return
      }
      // 自动填充缺失的日期和餐次
      let dateToUse = form && form.date
      let slotToUse = form && form.slot
      if (!dateToUse) dateToUse = (this.data as any).lastPublishDate || ''
      if (!slotToUse) slotToUse = (this.data as any).lastPublishSlot || ''
      if (!form) {
        this.setData({ publishForm: { date: dateToUse || '', slot: (slotToUse as any) || 'lunch', description: '', basePrice: 20, capacity: 50, options: [] } })
      } else {
        if (!form.date && dateToUse) this.setData({ 'publishForm.date': dateToUse })
        if (!form.slot && slotToUse) this.setData({ 'publishForm.slot': slotToUse })
      }
      if (!dateToUse || !slotToUse) {
        try { wx.hideLoading() } catch { }
        wx.showToast({ title: '请选择日期和餐次', icon: 'none' })
          ; (this as any)._publishTmr && clearTimeout((this as any)._publishTmr)
        this.setData({ submittingPublish: false })
        return
      }
      // safety timeout to avoid infinite spinner on network hang (start after validations)
      ; (this as any)._publishTmr && clearTimeout((this as any)._publishTmr)
        ; (this as any)._publishTmr = setTimeout(() => {
          try { wx.hideLoading() } catch { }
          this.setData({ submittingPublish: false })
          wx.showToast({ title: '网络超时，请稍后重试', icon: 'none' })
        }, 15000)
      const body: any = {
        date: dateToUse,
        slot: slotToUse,
        title: null,
        description: form.description || '',
        base_price_cents: Math.round((form.basePrice || 0) * 100),
        options: (form.options || []).map((o: any) => ({ id: String(o.id || ''), name: o.name || '', price_cents: Math.round((o.price || 0) * 100) })),
        capacity: Math.max(1, Number(form.capacity || 0)),
      }
      // per_user_limit 固定由后端默认为 1，不再通过前端设置
      try {
        await this.ensureLogin()
        let meal_id: number
        let usedRepost = false
        if (this.data.publishMode === 'edit' && this.data.publishMealId) {
          if (this.data.publishNeedsRepost) {
            await api.request(`/meals/${this.data.publishMealId}/repost`, { method: 'POST', data: body })
            meal_id = this.data.publishMealId as number
            usedRepost = true
          } else {
            await api.request(`/meals/${this.data.publishMealId}`, { method: 'PUT', data: body })
            meal_id = this.data.publishMealId as number
          }
        } else {
          const res = await api.request<{ meal_id: number }>(`/meals`, { method: 'POST', data: body })
          meal_id = (res as any).meal_id
        }
        // update local cache
        const byKey: Map<string, any> = (this as any)._byKey || new Map<string, any>()
        const ordered_qty = usedRepost ? 0 : ((this.data.publishMode === 'edit' && (this.data as any).publishOriginal) ? Number((this.data as any).publishOriginal.ordered_qty || 0) : 0)
        byKey.set(`${dateToUse}_${slotToUse}`, {
          meal_id,
          date: dateToUse,
          slot: slotToUse,
          title: null,
          base_price_cents: body.base_price_cents,
          options: body.options,
          capacity: body.capacity,
          per_user_limit: 1,
          status: 'published',
          ordered_qty,
        })
          ; (this as any)._byKey = byKey
        // rebuild current view
        const anchor = parseDate(this.data.anchorDate)
        const curStart = getMondayStart(anchor)
        this.rebuildWeeks(curStart)
        this.setData({ showPublish: false })
        wx.showToast({ title: this.data.publishMode === 'edit' ? '已修改' : '已发布', icon: 'success' })
      } catch (e: any) {
        const msg = (e && (e as any).message) || '发布失败'
        wx.showToast({ title: msg, icon: 'none' })
      } finally {
        try { wx.hideLoading() } catch { }
        ; (this as any)._publishTmr && clearTimeout((this as any)._publishTmr)
        this.setData({ submittingPublish: false })
      }
    },
    onPublishFieldChange() {
      if (this.data.publishMode === 'edit') this.computePublishNeedsRepost()
    },
    async onMealLock() {
      if (this.data.submittingPublish) return
      const id = this.data.publishMealId
      if (!id) return
      this.setData({ submittingPublish: true })
      try {
        try { wx.showLoading({ title: '处理中...', mask: true }) } catch { }
        await this.ensureLogin()
        await api.request(`/meals/${id}/lock`, { method: 'POST' })
        wx.showToast({ title: '已锁定', icon: 'success' })
        this.setData({ showPublish: false })
        // refresh cache for current window
        const anchor = parseDate(this.data.anchorDate)
        const curStart = getMondayStart(anchor)
        const months = windowMonthsForNineWeeks(curStart)
        await this.ensureCacheMonths(months, true, true)
        this.rebuildWeeks(curStart)
      } catch (e: any) {
        wx.showToast({ title: e?.message || '操作失败', icon: 'none' })
      } finally {
        try { wx.hideLoading() } catch { }
        this.setData({ submittingPublish: false })
      }
    },
    async onMealCancel() {
      if (this.data.submittingPublish) return
      const id = this.data.publishMealId
      if (!id) return
      this.setData({ submittingPublish: true })
      try {
        try { wx.showLoading({ title: '处理中...', mask: true }) } catch { }
        await this.ensureLogin()
        await api.request(`/meals/${id}/cancel`, { method: 'POST' })
        wx.showToast({ title: '已撤单', icon: 'success' })
        this.setData({ showPublish: false })
        const anchor = parseDate(this.data.anchorDate)
        const curStart = getMondayStart(anchor)
        const months = windowMonthsForNineWeeks(curStart)
        await this.ensureCacheMonths(months, true, true)
        this.rebuildWeeks(curStart)
      } catch (e: any) {
        wx.showToast({ title: e?.message || '操作失败', icon: 'none' })
      } finally {
        try { wx.hideLoading() } catch { }
        this.setData({ submittingPublish: false })
      }
    },
    async onMealUnlock() {
      if (this.data.submittingPublish) return
      const id = this.data.publishMealId
      if (!id) return
      this.setData({ submittingPublish: true })
      try {
        try { wx.showLoading({ title: '处理中...', mask: true }) } catch { }
        await this.ensureLogin()
        await api.request(`/meals/${id}/unlock`, { method: 'POST' })
        wx.showToast({ title: '已取消锁定', icon: 'success' })
        this.setData({ showPublish: false })
        // refresh cache for current window
        const anchor = parseDate(this.data.anchorDate)
        const curStart = getMondayStart(anchor)
        const months = windowMonthsForNineWeeks(curStart)
        await this.ensureCacheMonths(months, true, true)
        this.rebuildWeeks(curStart)
      } catch (e: any) {
        wx.showToast({ title: e?.message || '操作失败', icon: 'none' })
      } finally {
        try { wx.hideLoading() } catch { }
        this.setData({ submittingPublish: false })
      }
    },
    async ensureCacheMonths(months: string[], silent = false, force = false) {
      const loaded: Set<string> = (this as any)._loadedMonths || new Set<string>()
      const missing = force ? months : months.filter(m => !loaded.has(m))
      if (missing.length === 0) return { fetched: false }
      if (!silent) this.setData({ loading: true })
      try {
        await this.ensureLogin()
        const batch = await getCalendarBatch(missing)
        const monthsMap = batch.months || {}
        const byKey: Map<string, any> = (this as any)._byKey || new Map<string, any>()
        for (const mKey of Object.keys(monthsMap)) {
          const arr = monthsMap[mKey] || []
          for (const it of arr) {
            byKey.set(`${it.date}_${it.slot}`, it)
          }
          loaded.add(mKey)
        }
        ; (this as any)._byKey = byKey
          ; (this as any)._loadedMonths = loaded
          ; (this as any)._lastRefreshTs = Date.now()
        return { fetched: true }
      } finally {
        if (!silent) this.setData({ loading: false })
      }
    },
    async refreshIfStale() {
      const now = Date.now()
      const last = (this as any)._lastRefreshTs || 0
      if (now - last < 10000) return
      if ((this as any)._refreshingSwipe) return
        ; (this as any)._refreshingSwipe = true
      try {
        const anchor = parseDate(this.data.anchorDate)
        const curStart = getMondayStart(anchor)
        const months = windowMonthsForNineWeeks(curStart)
        // Update cache in background to avoid UI flashing, do not rebuild immediately
        await this.ensureCacheMonths(months, true, true)
      } catch (e) {
        // silent fail
      } finally {
        ; (this as any)._refreshingSwipe = false
      }
    },
    rebuildWeeks(curStart: Date) {
      const byKey: Map<string, any> = (this as any)._byKey || new Map<string, any>()
      const anchor = this.data.anchorDate ? parseDate(this.data.anchorDate) : new Date()
      // compute week starts symmetrical -4..+4
      const weekStarts: Date[] = []
      for (let i = -4; i <= 4; i++) {
        const d = new Date(curStart)
        d.setDate(curStart.getDate() + i * 7)
        weekStarts.push(d)
      }
      const weeks9 = weekStarts.map(ws => this.buildWeek(ws, byKey, anchor))
      const prevWeek = this.buildWeek(new Date(curStart.getTime() - 7 * 86400000), byKey, anchor)
      const week = this.buildWeek(curStart, byKey, anchor)
      const nextWeek = this.buildWeek(new Date(curStart.getTime() + 7 * 86400000), byKey, anchor)
      this.setData({ weeks9, prevWeek, week, nextWeek })
    },
    computeWeeks(curStart: Date) {
      const byKey: Map<string, any> = (this as any)._byKey || new Map<string, any>()
      const anchor = this.data.anchorDate ? parseDate(this.data.anchorDate) : new Date()
      const weekStarts: Date[] = []
      for (let i = -4; i <= 4; i++) {
        const d = new Date(curStart)
        d.setDate(curStart.getDate() + i * 7)
        weekStarts.push(d)
      }
      const weeks9 = weekStarts.map(ws => this.buildWeek(ws, byKey, anchor))
      const prevWeek = this.buildWeek(new Date(curStart.getTime() - 7 * 86400000), byKey, anchor)
      const week = this.buildWeek(curStart, byKey, anchor)
      const nextWeek = this.buildWeek(new Date(curStart.getTime() + 7 * 86400000), byKey, anchor)
      return { weeks9, prevWeek, week, nextWeek }
    },
    measureViewportAndCenter() {
      const q = wx.createSelectorQuery().in(this as any)
      q.select('.cal-viewport').boundingClientRect()
      q.select('.scrollarea').boundingClientRect()
      q.exec((res: any[]) => {
        let h = 0
        const v1 = res && res[0]
        const v2 = res && res[1]
        if (v1 && v1.height) h = Math.floor(v1.height)
        else if (v2 && v2.height) h = Math.floor(v2.height)
        if (!h || h <= 0) {
          try {
            const sys = wx.getSystemInfoSync()
            if (sys && sys.windowHeight) h = Math.floor(sys.windowHeight * 0.66) // fallback: use 2/3 of window
          } catch { }
        }
        if (!h || h <= 0) return
        // center current three-week page in middle of 3 pages => base = -h
        this.setData({ blockH: h, trackBase: -h, trackY: 0, trackHeight: h * 3 })
      })
    },
    buildWeek(start: Date, byKey: Map<string, any>, anchor: Date) {
      const todayStr = formatDate(new Date())
      const cells: any[] = []
      // Layout order: Sun(prev) | Mon Tue Wed Thu Fri | Sat(this)
      // Indices relative to Monday-start: -1, 0, 1, 2, 3, 4, 5
      for (let rel = -1; rel <= 5; rel++) {
        const d = new Date(start)
        d.setDate(start.getDate() + rel)
        const dM = `${d.getMonth() + 1}`.padStart(2, '0')
        const dD = d.getDate()
        const dateStr = `${d.getFullYear()}-${dM}-${`${dD}`.padStart(2, '0')}`
        const dow = (d.getDay() + 6) % 7 // 0-6 => Mon..Sun
        const dowStr = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][dow]
        const isWeekend = dow >= 5 || d.getDay() === 0
        const isCurrentMonth = (d.getFullYear() === anchor.getFullYear() && d.getMonth() === anchor.getMonth())
        const now = new Date()
        const isThisMonthNow = (d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth())
        const isThisYearNow = (d.getFullYear() === now.getFullYear())
        const lunch = byKey.get(`${dateStr}_lunch`)
        const dinner = byKey.get(`${dateStr}_dinner`)
        const toCell = (it: any) => toSlotView(it)
        const DD = `${dD}`.padStart(2, '0')
        const MM = dM
        const YY = `${d.getFullYear()}`.slice(2)
        let dateLabel: string
        if (isWeekend || isThisMonthNow) {
          dateLabel = DD
        } else if (!isThisYearNow) {
          dateLabel = `${YY}/${MM}/${DD}`
        } else {
          dateLabel = `${MM}/${DD}`
        }
        cells.push({
          dateKey: dateStr,
          day: dD,
          isCurrentMonth,
          isWeekend,
          dow: dowStr,
          isToday: dateStr === todayStr,
          lunch: toCell(lunch),
          dinner: toCell(dinner),
          dateLabel,
        })
      }
      return cells
    },
    async fetchMealDetail(mealId: number) {
      await this.ensureLogin()
      const detail: any = await api.request(`/meals/${mealId}`, { method: 'GET' })
      // options are ensured as arrays by server
      detail.options = Array.isArray(detail.options) ? detail.options : []
      return detail
    },
    async openOrderDialogBySlot(mealId: number, _status: string, _left: number, my: boolean) {
      // pre-open refresh latest window
      const anchor = parseDate(this.data.anchorDate)
      const curStart = getMondayStart(anchor)
      const months = windowMonthsForNineWeeks(curStart)
      await this.ensureCacheMonths(months, true, true)
      // fetch meal detail
      const d = await this.fetchMealDetail(mealId)
      const cap = Number(d.capacity || 0)
      const ordered = Number(d.ordered_qty || 0)
      const leftNow = Math.max(0, cap - ordered)
      
      // Fetch user's current order for this meal if they have one
      let userOrder = null
      if (my) {
        try {
          userOrder = await api.request(`/orders?meal_id=${mealId}`, { method: 'GET' })
        } catch (e) {
          console.log('No existing order found for user')
        }
      }
      
      // decide action/read-only
      let action: 'create' | 'update' | 'readonly' = 'readonly'
      let readonlyMsg = ''
      if (d.status === 'published') {
        if (leftNow > 0) action = my ? 'update' : 'create'
        else action = my ? 'update' : 'readonly', readonlyMsg = '哦豁，被订完了，下次加油'
      } else if (d.status === 'locked') {
        action = 'readonly'; readonlyMsg = my ? '已锁定' : '哦豁，已锁定，你错过了，下次加油'
      } else if (d.status === 'completed') {
        action = 'readonly'; readonlyMsg = my ? '本餐已完成' : '本餐已结束'
      } else {
        wx.showToast({ title: '尚未发布', icon: 'none' }); return
      }
      // compute totals (no selected options yet; only base price)
      const base = Number(d.base_price_cents || 0)
      const total = base
      // try get user balance for reminder
      let balance_cents: number | undefined = undefined
      try {
        const bal: any = await api.request('/users/me/balance', { method: 'GET' })
        balance_cents = Number(bal && bal.balance_cents || 0)
      } catch { }
      this.setData({
        showOrder: true,
        orderDetail: {
          meal_id: d.meal_id,
          date: d.date,
          slot: d.slot,
          description: d.description,
          capacity: cap,
          ordered_qty: ordered,
          options: d.options,
          base_price_cents: base,
          total_cents: total,
          balance_cents,
          action,
          readonlyMsg
        }
      })
      
      // Set selected options in the dialog component after it's shown
      setTimeout(() => {
        const orderDialog = this.selectComponent('#order-dialog')
        if (orderDialog && userOrder && userOrder.options) {
          orderDialog.setData({ 
            selectedOptions: userOrder.options || [] 
          })
        }
      }, 100)
    },
    closeOrderDialog() {
      this.setData({ showOrder: false })
      // pre-close refresh latest window
      const anchor = parseDate(this.data.anchorDate)
      const curStart = getMondayStart(anchor)
      const months = windowMonthsForNineWeeks(curStart)
      this.ensureCacheMonths(months, true, true).then(() => this.rebuildWeeks(curStart))
    },
    async onOrderCreate() {
      try {
        const d = this.data.orderDetail || {}
        await this.ensureLogin()
        // Get selected options from the order dialog component
        const orderDialog = this.selectComponent('#order-dialog')
        const selectedOptions = orderDialog ? orderDialog.data.selectedOptions || [] : []
        const payload = { meal_id: d.meal_id, qty: 1, options: selectedOptions }
        await api.request('/orders', { method: 'POST', data: payload })
        wx.showToast({ title: '下单成功', icon: 'success' })
        this.closeOrderDialog()
      } catch (e: any) {
        wx.showToast({ title: e?.message || '下单失败', icon: 'none' })
      }
    },
    async onOrderUpdate() {
      try {
        const d = this.data.orderDetail || {}
        await this.ensureLogin()
        // Get selected options from the order dialog component
        const orderDialog = this.selectComponent('#order-dialog')
        const selectedOptions = orderDialog ? orderDialog.data.selectedOptions || [] : []
        // backend enforces single order per meal; reuse POST to replace
        const payload = { meal_id: d.meal_id, qty: 1, options: selectedOptions }
        await api.request('/orders', { method: 'POST', data: payload })
        wx.showToast({ title: '已更新', icon: 'success' })
        this.closeOrderDialog()
      } catch (e: any) {
        wx.showToast({ title: e?.message || '更新失败', icon: 'none' })
      }
    },
    async onOrderCancel() {
      try {
        const d = this.data.orderDetail || {}
        await this.ensureLogin()
        // Assume backend supports DELETE /orders?meal_id=xx to cancel current user's order
        await api.request(`/orders?meal_id=${d.meal_id}`, { method: 'DELETE' })
        wx.showToast({ title: '已取消', icon: 'success' })
        this.closeOrderDialog()
      } catch (e: any) {
        wx.showToast({ title: e?.message || '取消失败', icon: 'none' })
      }
    },
    async ensureLogin() {
      if (!api) return
      // 简单校验本地是否已有 token，没有则触发登录
      const token = wx.getStorageSync('auth_token')
      if (!token) {
        try { await loginAndGetToken() } catch (e) { console.error(e) }
      }
    },
    async loadWeek(anchorDateStr: string, opts?: { silent?: boolean, preload3Months?: boolean, force?: boolean }) {
      const silent = !!(opts && opts.silent)
      const preload3Months = !!(opts && opts.preload3Months)
      const force = !!(opts && (opts as any).force)
      if (!silent) this.setData({ loading: true, tip: '' })
      try {
        const anchor = parseDate(anchorDateStr)
        const curStart = getMondayStart(anchor)
        // Determine which months to ensure in cache
        let monthsToEnsure: string[]
        if (preload3Months) {
          const centerMonth = startOfMonth(curStart)
          monthsToEnsure = monthsBetween(addMonths(centerMonth, -1), addMonths(centerMonth, 1))
        } else {
          monthsToEnsure = windowMonthsForNineWeeks(curStart)
        }
        await this.ensureCacheMonths(monthsToEnsure, silent, force)
        // Build weeks and labels, then batch in a single setData to avoid flash
        const w = this.computeWeeks(curStart)
        this.setData({
          ...w,
          meals: [],
          anchorDate: anchorDateStr,
          month: formatMonth(anchor),
          monthLabel: formatMonth(anchor).replace('-', '年') + '月',
          yearLabel: `${anchor.getFullYear()}年`,
          monthOnlyLabel: `${anchor.getMonth() + 1}月`,
          fullLabel: formatMonth(anchor).replace('-', '年') + '月',
        })
        // ensure viewport measured and track is centered on middle page
        if (!this.data.blockH || this.data.blockH <= 0) {
          // 确保日历已渲染（关闭 loading）再测量，否则会得到 0 高度
          if (!silent) this.setData({ loading: false })
          wx.nextTick(() => this.measureViewportAndCenter())
        } else {
          // if already measured, just set base to -H and update total track height
          const H = this.data.blockH
          this.setData({ trackBase: -H, trackY: 0, trackHeight: H * 3 })
        }
      } catch (e: any) {
        const msg = (e && (e as any).message) || '加载失败'
        this.setData({ tip: msg })
      } finally {
        if (!silent) this.setData({ loading: false })
      }
    },
    onToday() {
      const today = formatDate(new Date())
      this.setData({ todayCnLabel: this.formatCnDate(new Date()) })
      this.loadWeek(today)
    },
    onPrevMonth() {
      const a = parseDate(this.data.anchorDate)
      a.setDate(a.getDate() - 21)
      this.loadWeek(formatDate(a), { silent: true, force: true })
    },
    onNextMonth() {
      const a = parseDate(this.data.anchorDate)
      a.setDate(a.getDate() + 21)
      this.loadWeek(formatDate(a), { silent: true, force: true })
    },
    onCalTouchStart(e: WechatMiniprogram.TouchEvent) {
      const t = e.touches && e.touches[0]
      if (t) {
        this.setData({ _touchY: t.clientY, _touchX: t.clientX, _touchTime: Date.now(), trackAnimate: false })
      }
      // If data is stale (>10s), trigger a silent refresh of current 9-week window at swipe start
      this.refreshIfStale()
    },
    onCalTouchMove(e: WechatMiniprogram.TouchEvent) {
      // Provide visual drag feedback by translating the track while dragging vertically
      const t = e.touches && e.touches[0]
      if (!t) return
      const dx = t.clientX - (this.data._touchX || 0)
      const dy = t.clientY - (this.data._touchY || 0)
      const H = this.data.blockH > 0 ? this.data.blockH : 468
      if (Math.abs(dy) > Math.abs(dx)) {
        // clamp drag distance to avoid excessive blank space reveal
        const maxDrag = Math.min(H, Math.floor(H * 0.9))
        const y = Math.max(-maxDrag, Math.min(maxDrag, dy))
        this.setData({ trackY: y })
      }
    },
    onCalTouchEnd(e: WechatMiniprogram.TouchEvent) {
      const changed = e.changedTouches && e.changedTouches[0]
      if (!changed) return
      const dy = changed.clientY - (this.data._touchY || 0)
      const dx = changed.clientX - (this.data._touchX || 0)
      const H = this.data.blockH > 0 ? this.data.blockH : 468
      // detect vertical swipe; ignore if horizontal dominates
      if (Math.abs(dy) <= Math.abs(dx)) return
      // thresholds at +/- 18% of viewport (one page = viewport height), min 72px, max 220px
      const threshold = Math.max(72, Math.min(220, Math.floor(H * 0.18)))
      if (dy <= -threshold) {
        // swipe up: animate one page (3 weeks) up, then load next set of 3 weeks centered
        this.setData({ trackAnimate: true, trackY: -H, _pageOffset: 1 })
        setTimeout(() => {
          this.onNextMonth()
          this.setData({ trackAnimate: false, trackY: 0, _pageOffset: 0 })
        }, 180)
      } else if (dy >= threshold) {
        // swipe down: animate one page (3 weeks) down, then load prev set
        this.setData({ trackAnimate: true, trackY: H, _pageOffset: -1 })
        setTimeout(() => {
          this.onPrevMonth()
          this.setData({ trackAnimate: false, trackY: 0, _pageOffset: 0 })
        }, 180)
      } else {
        // not enough to switch: snap back to rest position
        this.setData({ trackAnimate: true, trackY: 0 })
        setTimeout(() => this.setData({ trackAnimate: false }), 180)
      }
    },
    onTapSlot(e: WechatMiniprogram.TouchEvent | WechatMiniprogram.CustomEvent) {
      const ds: any = (e as any).detail && Object.keys((e as any).detail).length
        ? (e as any).detail
        : (e.currentTarget && (e.currentTarget as any).dataset) || {}
      const { mealId, status, date, slot, left, my } = ds
      // 记录最近一次点击的日期和餐次，用于发布时自动填充
      if (date && slot) {
        this.setData({ lastPublishDate: String(date), lastPublishSlot: String(slot) as any })
      }
      if (status === 'none') {
        if (this.data.adminView) {
          // open publish dialog for this date+slot (weekday only; weekend slots not rendered)
          this.openPublishDialog(date, slot)
        } else {
          wx.showToast({ title: '未发布', icon: 'none' })
        }
        return
      }
      if (!mealId) {
        wx.showToast({ title: '无效餐次', icon: 'none' })
        return
      }
      if (this.data.adminView) {
        // 管理模式：根据状态打开编辑或创建
        if (status === 'published' || status === 'locked') {
          this.openEditPublishDialog(Number(mealId))
        } else if (status === 'completed') {
          // 只读，暂时打开编辑框但不允许提交
          this.openEditPublishDialog(Number(mealId))
        } else {
          this.openPublishDialog(date, slot)
        }
        return
      }
      // 用户模式：打开点餐弹窗（不同状态下不同操作能力）
      this.openOrderDialogBySlot(Number(mealId), String(status), Number(left || 0), Boolean(my))
    },
  },
  pageLifetimes: {
    show() {
      // Refresh admin-related UI (slogan/adminView) when page becomes visible
      this.refreshAdminBindings()
      const tab = (this as any).getTabBar && (this as any).getTabBar()
      if (tab && typeof tab.updateSelected === 'function') {
        tab.updateSelected()
      }
      // 若DB Key发生变更（例如在“我的”页设置/修改），则清缓存并强制刷新日历
      const curKey = getDbKey() || ''
      const prevKey = (this as any)._dbKeyPrev || ''
      if (curKey !== prevKey) {
        this.onDbKeyChanged(curKey)
      }
      // 如仍未设置口令，则提示设置
      if (!curKey) {
        setTimeout(() => this.promptPassphraseOnCalendar(), 50)
      }
      // 若尚未完成测量，补一次测量与居中
      if (!this.data.blockH || this.data.blockH <= 0) {
        wx.nextTick(() => this.measureViewportAndCenter())
      }
    }
  }
})
