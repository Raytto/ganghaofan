/**
 * 透支功能相关工具函数
 * 处理透支状态显示、警告提醒等UI逻辑
 */

/**
 * 格式化余额显示（支持负数透支）
 * @param balanceCents 余额（分）
 * @returns 格式化的余额字符串
 */
export function formatBalance(balanceCents: number): string {
  const yuan = balanceCents / 100
  if (balanceCents < 0) {
    return `-¥${Math.abs(yuan).toFixed(2)}`
  }
  return `¥${yuan.toFixed(2)}`
}

/**
 * 获取余额状态信息
 * @param balanceCents 余额（分）
 * @returns 余额状态对象
 */
export function getBalanceStatus(balanceCents: number) {
  const yuan = balanceCents / 100
  
  if (balanceCents >= 0) {
    return {
      status: 'normal',
      statusText: '正常',
      color: '#07c160',
      isOverdraft: false,
      overdraftAmount: 0
    }
  } else if (balanceCents >= -10000) { // -100元以内
    return {
      status: 'light_overdraft',
      statusText: '轻度透支',
      color: '#fa9550',
      isOverdraft: true,
      overdraftAmount: Math.abs(yuan)
    }
  } else if (balanceCents >= -30000) { // -300元以内
    return {
      status: 'moderate_overdraft',
      statusText: '中度透支',
      color: '#f76260',
      isOverdraft: true,
      overdraftAmount: Math.abs(yuan)
    }
  } else {
    return {
      status: 'heavy_overdraft',
      statusText: '重度透支',
      color: '#d32f2f',
      isOverdraft: true,
      overdraftAmount: Math.abs(yuan)
    }
  }
}

/**
 * 显示透支警告对话框
 * @param balanceCents 当前余额（分）
 * @param overdraftWarning 透支警告信息
 * @returns Promise<boolean> 用户是否确认继续
 */
export function showOverdraftWarning(
  balanceCents: number, 
  overdraftWarning?: string
): Promise<boolean> {
  return new Promise((resolve) => {
    const status = getBalanceStatus(balanceCents)
    
    if (!status.isOverdraft) {
      resolve(true)
      return
    }

    const content = `当前余额：${formatBalance(balanceCents)}\n透支金额：${formatBalance(Math.abs(balanceCents))}\n${overdraftWarning || '您已进入透支状态，可以继续使用'}`

    wx.showModal({
      title: '透支提醒',
      content,
      showCancel: true,
      cancelText: '知道了',
      confirmText: '继续使用',
      success: (res) => {
        resolve(res.confirm)
      },
      fail: () => {
        resolve(false)
      }
    })
  })
}

/**
 * 检查是否需要透支提醒
 * @param balanceCents 余额（分）
 * @returns 是否需要提醒
 */
export function shouldShowOverdraftReminder(balanceCents: number): boolean {
  // 透支超过30元时提醒
  return balanceCents < -3000
}

/**
 * 显示透支充值提醒
 * @param balanceCents 当前余额（分）
 * @returns Promise<boolean> 用户是否选择去充值
 */
export function showRechargeReminder(balanceCents: number): Promise<boolean> {
  return new Promise((resolve) => {
    const overdraftAmount = Math.abs(balanceCents) / 100

    wx.showModal({
      title: '充值提醒',
      content: `您当前透支${overdraftAmount}元，建议尽快充值恢复余额`,
      showCancel: true,
      cancelText: '稍后再说',
      confirmText: '去充值',
      success: (res) => {
        resolve(res.confirm)
      },
      fail: () => {
        resolve(false)
      }
    })
  })
}

/**
 * 计算建议充值金额
 * @param balanceCents 当前余额（分）
 * @returns 建议充值金额列表（分）
 */
export function getSuggestedRechargeAmounts(balanceCents: number): number[] {
  const baseAmounts = [1000, 2000, 5000, 10000, 20000] // 10, 20, 50, 100, 200元
  
  if (balanceCents >= 0) {
    return baseAmounts
  }

  // 透支状态下，建议充值金额包含覆盖透支的金额
  const overdraftAmount = Math.abs(balanceCents)
  const coverOverdraft = Math.ceil(overdraftAmount / 1000) * 1000 // 向上取整到10元
  
  const amounts = [coverOverdraft, ...baseAmounts.map(amount => amount + coverOverdraft)]
  
  // 去重并排序
  return [...new Set(amounts)].sort((a, b) => a - b)
}

/**
 * 格式化透支历史显示
 * @param transaction 交易记录
 * @returns 格式化的交易描述
 */
export function formatTransactionForOverdraft(transaction: {
  type: string
  amount_cents: number
  balance_after_cents: number
  remark: string
  created_at: string
}): {
  title: string
  description: string
  amount: string
  balanceAfter: string
  isOverdraft: boolean
} {
  const amount = formatBalance(transaction.amount_cents)
  const balanceAfter = formatBalance(transaction.balance_after_cents)
  const isOverdraft = transaction.balance_after_cents < 0

  let title = ''
  let description = transaction.remark

  switch (transaction.type) {
    case 'debit':
      title = '消费扣费'
      break
    case 'credit':
      title = '充值到账'
      break
    case 'adjustment':
      title = '余额调整'
      break
    case 'refund':
      title = '退款到账'
      break
    default:
      title = '余额变动'
  }

  return {
    title,
    description,
    amount,
    balanceAfter,
    isOverdraft
  }
}

/**
 * 透支功能可用性检查
 * @param balanceCents 当前余额（分）
 * @param orderAmountCents 订单金额（分）
 * @returns 检查结果
 */
export function checkOverdraftAvailability(
  balanceCents: number, 
  orderAmountCents: number
): {
  canOrder: boolean
  willOverdraft: boolean
  newBalance: number
  warning?: string
} {
  const newBalance = balanceCents - orderAmountCents
  const overdraftLimit = -50000 // -500元透支限制
  
  const willOverdraft = newBalance < 0
  const canOrder = newBalance >= overdraftLimit

  let warning: string | undefined

  if (willOverdraft && canOrder) {
    const overdraftAmount = Math.abs(newBalance) / 100
    warning = `此次下单将透支${overdraftAmount}元，您可以继续使用透支功能`
  } else if (!canOrder) {
    warning = `透支额度不足，请先充值后再下单`
  }

  return {
    canOrder,
    willOverdraft,
    newBalance,
    warning
  }
}