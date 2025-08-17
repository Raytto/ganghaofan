Component({
    properties: {
        show: { type: Boolean, value: false },
        detail: { type: Object, value: {} },
    },
    methods: {
        onCloseMask() { this.triggerEvent('close'); },
        onClose() { this.triggerEvent('close'); },
        onCreate() { this.triggerEvent('create'); },
        onUpdate() { this.triggerEvent('update'); },
        onCancelOrder() { this.triggerEvent('cancelorder'); },
    }
})
