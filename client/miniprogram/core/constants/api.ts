/**
 * API相关常量定义
 */

export const API_CONFIG = {
  BASE_URL: 'http://127.0.0.1:8000/api/v1',
  TIMEOUT: 10000,
  MAX_RETRIES: 3
} as const

export const API_ENDPOINTS = {
  // 认证相关
  LOGIN: '/auth/login',
  RESOLVE_PASSPHRASE: '/env/resolve',
  MOCK_CONFIG: '/env/mock',
  
  // 用户相关
  USER_PROFILE: '/users/me',
  USER_BALANCE: '/users/me/balance',
  USER_RECHARGE: (userId: number) => `/users/${userId}/recharge`,
  
  // Phase 2 新增用户API
  USER_PROFILE_SUMMARY: '/users/profile',
  USER_ORDER_HISTORY: '/users/orders/history',
  USER_BALANCE_HISTORY: '/users/balance/history',
  USER_BALANCE_RECHARGE: '/users/balance/recharge',
  
  // 餐次相关
  CALENDAR: '/calendar',
  CALENDAR_BATCH: '/calendar/batch',
  MEAL_DETAIL: (mealId: number) => `/meals/${mealId}`,
  MEAL_CREATE: '/meals',
  MEAL_UPDATE: (mealId: number) => `/meals/${mealId}`,
  MEAL_LOCK: (mealId: number) => `/meals/${mealId}/lock`,
  MEAL_UNLOCK: (mealId: number) => `/meals/${mealId}/unlock`,
  MEAL_COMPLETE: (mealId: number) => `/meals/${mealId}/complete`,
  MEAL_CANCEL: (mealId: number) => `/meals/${mealId}/cancel`,
  MEAL_REPOST: (mealId: number) => `/meals/${mealId}/repost`,
  
  // 订单相关
  ORDER_CREATE: '/orders',
  ORDER_UPDATE: (orderId: number) => `/orders/${orderId}`,
  ORDER_CANCEL: (orderId: number) => `/orders/${orderId}`,
  
  // 日志相关
  LOGS_MY: '/logs/my',
  LOGS_ALL: '/logs/all',
  
  // 健康检查
  HEALTH: '/health'
} as const

export const STORAGE_KEYS = {
  TOKEN: 'auth_token',
  DB_KEY_MAP: 'db_key_map',
  DB_KEY_GLOBAL: 'db_key_global',
  CURRENT_OPEN_ID: 'current_open_id',
  ADMIN_VIEW_ENABLED: 'admin_view_enabled',
  THEME_MODE: 'theme_mode'
} as const

export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  INTERNAL_SERVER_ERROR: 500
} as const