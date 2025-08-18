Component({
    properties: {
        label: { type: String, value: '' },  // 午餐/晚餐
        type: { type: String, value: '' },   // lunch/dinner for class hook
        view: { type: Object, value: {} },   // { bg, fg, l2, l3, status, my, left, meal_id }
        date: { type: String, value: '' },
        // Avoid using reserved attribute name 'slot' in WXML; use mealSlot instead
        mealSlot: { type: String, value: '' },   // 'lunch' | 'dinner'
    },
    methods: {
        onTap() {
            const v: any = this.data.view || {}
            this.triggerEvent('tapslot', {
                date: this.data.date,
                // expose as 'slot' in event payload for consumers
                slot: (this.data as any).mealSlot,
                mealId: v.meal_id || '',
                status: v.status || 'none',
                left: v.left || 0,
                my: !!v.my,
            })
        }
    }
})
