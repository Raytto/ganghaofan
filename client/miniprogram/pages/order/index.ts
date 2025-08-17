import { api } from '../../utils/api'

Page({
    data: {
        mealId: 0,
        meal: null as any,
        loading: false,
        tip: '',
    },
    onLoad(query: Record<string, string>) {
        const id = Number(query.id || 0)
        this.setData({ mealId: id })
        this.load()
    },
    async load() {
        if (!this.data.mealId) return
        this.setData({ loading: true, tip: '' })
        try {
            const res = await api.request(`/meals/${this.data.mealId}`, { method: 'GET' })
            this.setData({ meal: res })
        } catch (e: any) {
            const msg = (e && (e as any).message) || '加载失败'
            this.setData({ tip: msg })
        } finally {
            this.setData({ loading: false })
        }
    },
    async onCreateOrder() {
        if (!this.data.mealId) return
        try {
            await api.request('/orders', { method: 'POST', data: { meal_id: this.data.mealId, qty: 1, options: [] } })
            wx.showToast({ title: '下单成功', icon: 'success' })
        } catch (e: any) {
            const msg = (e && (e as any).message) || '下单失败'
            wx.showToast({ title: msg, icon: 'none' })
        }
    }
})
