Component({
    properties: {
        show: { type: Boolean, value: false },
        detail: { type: Object, value: {} },
    },
    data: {
        selectedOptions: [] as string[], // Track selected option IDs
        calculatedTotal: 0, // Calculated total price in cents
    },
    observers: {
        'detail, selectedOptions': function(detail: any, selectedOptions: string[]) {
            this.calculateTotal(detail, selectedOptions);
        }
    },
    methods: {
        onCloseMask() { this.triggerEvent('close'); },
        onClose() { this.triggerEvent('close'); },
        onCreate() { 
            this.triggerEvent('create', { selectedOptions: this.data.selectedOptions }); 
        },
        onUpdate() { 
            this.triggerEvent('update', { selectedOptions: this.data.selectedOptions }); 
        },
        onCancelOrder() { this.triggerEvent('cancelorder'); },
        
        // Toggle option selection
        onToggleOption(e: any) {
            const optionId = e.currentTarget.dataset.optionId;
            const selectedOptions = [...this.data.selectedOptions];
            const index = selectedOptions.indexOf(optionId);
            
            if (index > -1) {
                selectedOptions.splice(index, 1); // Remove if selected
            } else {
                selectedOptions.push(optionId); // Add if not selected
            }
            
            this.setData({ selectedOptions });
        },
        
        // Calculate total price based on selected options
        calculateTotal(detail: any, selectedOptions: string[]) {
            if (!detail || !detail.options) {
                this.setData({ calculatedTotal: detail?.base_price_cents || 0 });
                return;
            }
            
            let total = detail.base_price_cents || 0;
            const options = detail.options || [];
            
            selectedOptions.forEach(optionId => {
                const option = options.find((op: any) => op.id === optionId || op.id === String(optionId));
                if (option) {
                    total += option.price_cents || 0;
                }
            });
            
            this.setData({ calculatedTotal: total });
        }
    }
})
