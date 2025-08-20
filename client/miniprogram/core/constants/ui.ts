/**
 * UI相关常量定义
 */

export const MEAL_SLOTS = {
  LUNCH: 'lunch',
  DINNER: 'dinner'
} as const

export const MEAL_STATUS = {
  PUBLISHED: 'published',
  LOCKED: 'locked',
  COMPLETED: 'completed',
  CANCELED: 'canceled'
} as const

export const ORDER_STATUS = {
  ACTIVE: 'active',
  CANCELED: 'canceled'
} as const

export const THEME_MODES = {
  DARK: 'dark',
  LIGHT: 'light'
} as const

export const PAGE_ROUTES = {
  INDEX: '/pages/index/index',
  ORDER: '/pages/order/index',
  ADMIN: '/pages/admin/index',
  PROFILE: '/pages/profile/index',
  LOGS: '/pages/logs/logs'
} as const

export const DIALOG_TYPES = {
  PUBLISH: 'publish',
  ORDER: 'order',
  CONFIRM: 'confirm'
} as const

export const TOAST_DURATION = {
  SHORT: 1500,
  LONG: 3000
} as const

export const LOADING_MESSAGES = {
  LOGIN: '登录中...',
  LOADING: '加载中...',
  SUBMITTING: '提交中...',
  PROCESSING: '处理中...'
} as const