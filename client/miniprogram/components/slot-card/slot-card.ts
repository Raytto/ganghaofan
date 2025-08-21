/**
 * 时间段卡片组件 - 重构版
 * 
 * @description 显示餐次信息和订餐状态的卡片组件
 * @version 2.0.0
 */
import { createComponentReactive, stateManager } from '../../core/store/index'

Component({
    properties: {
        /** 餐次标签 */
        label: { 
            type: String, 
            value: '' 
        },
        /** 餐次类型 */
        type: { 
            type: String, 
            value: '' 
        },
        /** 餐次视图数据 */
        view: { 
            type: Object, 
            value: {} 
        },
        /** 餐次日期 */
        date: { 
            type: String, 
            value: '' 
        },
        /** 餐次时段 */
        mealSlot: { 
            type: String, 
            value: '' 
        },
        /** 是否显示管理员操作 */
        showAdminActions: {
            type: Boolean,
            value: false
        },
        /** 当前用户的订单 */
        userOrder: {
            type: Object,
            value: null
        }
    },

    data: {
        statusText: '',
        statusColor: '',
        canOrder: false,
        canModify: false,
        darkMode: false,
        isAdmin: false
    },

    // 混入响应式功能
    ...createComponentReactive(),

    ready() {
        // 绑定状态
        this.bindState({
            darkMode: 'app.darkMode',
            isAdmin: 'user.isAdmin'
        })
    },

    observers: {
        'view, userOrder': function(view: any, userOrder: any) {
            if (view) {
                this.updateStatus(view, userOrder);
            }
        }
    },

    methods: {
        updateStatus(view: any, userOrder: any) {
            const mealStatus = view.status || 'none';
            const orderStatus = userOrder?.status || null;
            let statusText = '';
            let statusColor = '';
            let canOrder = false;
            let canModify = false;

            // 根据餐次状态和订单状态确定显示
            if (mealStatus === 'published') {
                if (userOrder && view.my) {
                    // 用户已下单，根据订单状态显示
                    switch (orderStatus) {
                        case 'active':
                            statusText = `已订餐 (${userOrder.quantity || 1}份)`;
                            statusColor = 'success';
                            canModify = true;
                            break;
                        case 'locked':
                            statusText = `已锁定 (${userOrder.quantity || 1}份)`;
                            statusColor = 'warning';
                            canModify = false;
                            break;
                        case 'completed':
                            statusText = `已完成 (${userOrder.quantity || 1}份)`;
                            statusColor = 'info';
                            canModify = false;
                            break;
                        case 'canceled':
                            statusText = '已取消';
                            statusColor = 'error';
                            canModify = false;
                            break;
                        case 'refunded':
                            statusText = '已退款';
                            statusColor = 'error';
                            canModify = false;
                            break;
                        default:
                            statusText = `已订餐 (${userOrder.quantity || 1}份)`;
                            statusColor = 'success';
                            canModify = true;
                    }
                } else {
                    statusText = '可订餐';
                    statusColor = 'primary';
                    canOrder = true;
                }
            } else if (mealStatus === 'locked') {
                statusText = '已锁定';
                statusColor = 'warning';
                canOrder = false;
                canModify = false;
            } else if (mealStatus === 'completed') {
                statusText = '已完成';
                statusColor = 'info';
                canOrder = false;
                canModify = false;
            } else if (mealStatus === 'canceled') {
                statusText = '已取消';
                statusColor = 'error';
                canOrder = false;
                canModify = false;
            } else {
                statusText = '未发布';
                statusColor = 'default';
                canOrder = false;
                canModify = false;
            }

            this.setData({
                statusText,
                statusColor,
                canOrder,
                canModify
            });
        },

        onTap() {
            const v: any = this.data.view || {};
            
            if (this.data.canOrder) {
                this.triggerEvent('order', { 
                    date: this.data.date,
                    slot: this.data.mealSlot,
                    mealId: v.meal_id || '',
                    meal: v
                });
            } else if (this.data.canModify) {
                this.triggerEvent('modify', { 
                    date: this.data.date,
                    slot: this.data.mealSlot,
                    mealId: v.meal_id || '',
                    meal: v,
                    order: this.data.userOrder
                });
            }
            
            // 保持向后兼容
            this.triggerEvent('tapslot', {
                date: this.data.date,
                slot: this.data.mealSlot,
                mealId: v.meal_id || '',
                status: v.status || 'none',
                left: v.left || 0,
                my: !!v.my,
            });
        },

        onAdminAction(e: any) {
            const action = e.currentTarget.dataset.action;
            const v: any = this.data.view || {};
            
            this.triggerEvent('adminAction', {
                action,
                date: this.data.date,
                slot: this.data.mealSlot,
                mealId: v.meal_id || '',
                meal: v
            });
        }
    }
})
