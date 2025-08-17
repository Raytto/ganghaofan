Component({
    properties: {
        show: { type: Boolean, value: false },
        mode: { type: String, value: 'create' }, // 'create' | 'edit'
        form: { type: Object, value: {} },
        original: { type: Object, value: {} },
        readonly: { type: Boolean, value: false },
        needsRepost: { type: Boolean, value: false },
    },
    methods: {
        onCloseMask() { this.triggerEvent('close'); },
        onClose() { this.triggerEvent('close'); },
        onInput(e: WechatMiniprogram.Input) {
            const field = (e.currentTarget.dataset as any)?.field;
            const value = (e.detail as any)?.value;
            this.triggerEvent('input', { field, value });
        },
        onNumber(e: WechatMiniprogram.Input) {
            const field = (e.currentTarget.dataset as any)?.field;
            const value = (e.detail as any)?.value;
            this.triggerEvent('number', { field, value });
        },
        onAdjust(e: WechatMiniprogram.TouchEvent) {
            const ds = e.currentTarget.dataset as any;
            this.triggerEvent('adjust', { field: ds?.field, step: Number(ds?.step || 0) });
        },
        onAddOption() { this.triggerEvent('addoption'); },
        onRemoveOption(e: WechatMiniprogram.TouchEvent) {
            const idx = Number((e.currentTarget.dataset as any)?.idx);
            this.triggerEvent('removeoption', { idx });
        },
        onOptionInput(e: WechatMiniprogram.Input) {
            const ds = e.currentTarget.dataset as any;
            const field = ds?.field;
            const idx = Number(ds?.idx);
            const value = (e.detail as any)?.value;
            this.triggerEvent('optioninput', { idx, field, value });
        },
        onAdjustOption(e: WechatMiniprogram.TouchEvent) {
            const ds = e.currentTarget.dataset as any;
            this.triggerEvent('adjustoption', { idx: Number(ds?.idx), step: Number(ds?.step || 0) });
        },
        onSubmit() { this.triggerEvent('submit'); },
        onCancelMeal() { this.triggerEvent('cancelmeal'); },
        onLockMeal() { this.triggerEvent('lockmeal'); },
    }
})
