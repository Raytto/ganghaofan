Component({
    properties: {
        label: { type: String, value: '' },  // 午餐/晚餐
        type: { type: String, value: '' },   // lunch/dinner for class hook
        view: { type: Object, value: {} },   // { bg, fg, l2, l3, status, my, left, meal_id }
        date: { type: String, value: '' },
        slot: { type: String, value: '' },   // 'lunch' | 'dinner'
    },
    methods: {
        onTap() {
            const v: any = this.data.view || {}
            this.triggerEvent('tapslot', {
                date: this.data.date,
                slot: this.data.slot,
                mealId: v.meal_id || '',
                status: v.status || 'none',
                left: v.left || 0,
                my: !!v.my,
            })
        }
    }
})
