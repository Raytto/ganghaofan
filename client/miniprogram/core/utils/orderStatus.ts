/**
 * 订单状态工具类
 * 处理订单状态相关的业务逻辑
 */

export enum OrderStatus {
  ACTIVE = 'active',       // 活跃订单（可修改/取消）
  LOCKED = 'locked',       // 锁定订单（不可修改，但有效）
  COMPLETED = 'completed', // 已完成
  CANCELED = 'canceled',   // 已取消（用户操作）
  REFUNDED = 'refunded'    // 已退款（系统/管理员操作）
}

export enum MealStatus {
  DRAFT = 'draft',         // 草稿
  PUBLISHED = 'published', // 已发布
  LOCKED = 'locked',       // 已锁定
  COMPLETED = 'completed', // 已完成
  CANCELED = 'canceled'    // 已取消
}

/**
 * 状态流转关系
 */
export const STATUS_TRANSITIONS = {
  [OrderStatus.ACTIVE]: [OrderStatus.LOCKED, OrderStatus.CANCELED, OrderStatus.REFUNDED],
  [OrderStatus.LOCKED]: [OrderStatus.ACTIVE, OrderStatus.COMPLETED, OrderStatus.REFUNDED],
  [OrderStatus.COMPLETED]: [], // 终态
  [OrderStatus.CANCELED]: [],  // 终态
  [OrderStatus.REFUNDED]: []   // 终态
}

/**
 * 订单状态工具类
 */
export class OrderStatusHelper {
  /**
   * 检查状态是否可以流转
   */
  static canTransition(from: OrderStatus, to: OrderStatus): boolean {
    const allowedTransitions = STATUS_TRANSITIONS[from] || []
    return allowedTransitions.includes(to)
  }

  /**
   * 获取订单状态显示文本
   */
  static getOrderStatusText(status: OrderStatus, quantity: number = 1): string {
    switch (status) {
      case OrderStatus.ACTIVE:
        return `已订餐 (${quantity}份)`
      case OrderStatus.LOCKED:
        return `已锁定 (${quantity}份)`
      case OrderStatus.COMPLETED:
        return `已完成 (${quantity}份)`
      case OrderStatus.CANCELED:
        return '已取消'
      case OrderStatus.REFUNDED:
        return '已退款'
      default:
        return '未知状态'
    }
  }

  /**
   * 获取餐次状态显示文本
   */
  static getMealStatusText(status: MealStatus): string {
    switch (status) {
      case MealStatus.DRAFT:
        return '未发布'
      case MealStatus.PUBLISHED:
        return '可订餐'
      case MealStatus.LOCKED:
        return '已锁定'
      case MealStatus.COMPLETED:
        return '已完成'
      case MealStatus.CANCELED:
        return '已取消'
      default:
        return '未知状态'
    }
  }

  /**
   * 获取状态颜色类型
   */
  static getStatusColor(orderStatus: OrderStatus | null, mealStatus: MealStatus): string {
    // 如果有订单状态，优先根据订单状态确定颜色
    if (orderStatus) {
      switch (orderStatus) {
        case OrderStatus.ACTIVE:
          return 'success'
        case OrderStatus.LOCKED:
          return 'warning'
        case OrderStatus.COMPLETED:
          return 'info'
        case OrderStatus.CANCELED:
          return 'error'
        case OrderStatus.REFUNDED:
          return 'error'
        default:
          return 'default'
      }
    }

    // 根据餐次状态确定颜色
    switch (mealStatus) {
      case MealStatus.PUBLISHED:
        return 'primary'
      case MealStatus.LOCKED:
        return 'warning'
      case MealStatus.COMPLETED:
        return 'info'
      case MealStatus.CANCELED:
        return 'error'
      default:
        return 'default'
    }
  }

  /**
   * 判断订单是否可修改
   */
  static isOrderModifiable(orderStatus: OrderStatus | null, mealStatus: MealStatus): boolean {
    // 只有活跃状态的订单且餐次是已发布状态才可修改
    return orderStatus === OrderStatus.ACTIVE && mealStatus === MealStatus.PUBLISHED
  }

  /**
   * 判断是否可以下单
   */
  static canCreateOrder(mealStatus: MealStatus, hasExistingOrder: boolean): boolean {
    // 餐次已发布且用户没有现有订单时可以下单
    return mealStatus === MealStatus.PUBLISHED && !hasExistingOrder
  }

  /**
   * 判断订单是否为终态
   */
  static isOrderFinal(status: OrderStatus): boolean {
    return [OrderStatus.COMPLETED, OrderStatus.CANCELED, OrderStatus.REFUNDED].includes(status)
  }

  /**
   * 获取可用的管理员操作
   */
  static getAdminActions(mealStatus: MealStatus, orderCount: number): Array<{
    action: string
    text: string
    color: string
    disabled: boolean
  }> {
    const actions = []

    switch (mealStatus) {
      case MealStatus.PUBLISHED:
        actions.push(
          { action: 'lock', text: '锁定订单', color: 'warning', disabled: orderCount === 0 },
          { action: 'complete', text: '完成餐次', color: 'success', disabled: orderCount === 0 },
          { action: 'cancel', text: '取消餐次', color: 'error', disabled: false }
        )
        break
        
      case MealStatus.LOCKED:
        actions.push(
          { action: 'unlock', text: '解锁订单', color: 'primary', disabled: false },
          { action: 'complete', text: '完成餐次', color: 'success', disabled: orderCount === 0 },
          { action: 'cancel', text: '取消餐次', color: 'error', disabled: false }
        )
        break
        
      case MealStatus.COMPLETED:
        // 已完成的餐次没有可用操作
        break
        
      case MealStatus.CANCELED:
        // 已取消的餐次没有可用操作
        break
    }

    return actions
  }

  /**
   * 获取状态变更提示文本
   */
  static getStatusChangeText(action: string): string {
    const textMap = {
      'lock': '确定要锁定此餐次的所有订单吗？锁定后用户无法修改订单。',
      'unlock': '确定要解锁此餐次的所有订单吗？解锁后用户可以重新修改订单。',
      'complete': '确定要完成此餐次吗？完成后所有订单将标记为已完成。',
      'cancel': '确定要取消此餐次吗？取消后将为所有订单退款。',
      'refund': '确定要为此餐次的所有订单退款吗？此操作不可撤销。'
    }
    
    return textMap[action] || '确定要执行此操作吗？'
  }
}

export default OrderStatusHelper