/**
 * API相关类型定义
 */

// 基础响应类型
export interface BaseResponse<T = any> {
  success: boolean
  data?: T
  message: string
  error_code?: string
  details?: Record<string, any>
}

// 分页参数
export interface PaginationParams {
  page: number
  size: number
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

// 认证相关
export interface LoginRequest {
  code: string
}

export interface LoginResponse {
  token: string
  user_id: number
  is_admin: boolean
}

export interface PassphraseRequest {
  passphrase: string
}

export interface PassphraseResponse {
  key: string
}

// 用户相关
export interface UserProfile {
  user_id: number
  open_id: string
  nickname?: string
  is_admin: boolean
  balance_cents: number
}

export interface UserBalance {
  user_id: number
  balance_cents: number
}

export interface RechargeRequest {
  amount_cents: number
  remark?: string
}

// 餐次相关
export interface MealOption {
  id: string
  name: string
  price_cents: number
}

export interface MealBase {
  date: string
  slot: 'lunch' | 'dinner'
  title?: string
  description?: string
  base_price_cents: number
  capacity: number
  per_user_limit: number
  options: MealOption[]
}

export interface Meal extends MealBase {
  meal_id: number
  status: 'published' | 'locked' | 'completed' | 'canceled'
  ordered_qty: number
  my_ordered: boolean
  created_by?: number
  created_at?: string
  updated_at?: string
}

export interface MealCalendarResponse {
  month: string
  meals: Meal[]
}

export interface MealBatchCalendarResponse {
  months: Record<string, Meal[]>
}

// 订单相关
export interface OrderBase {
  qty: number
  options: string[]
}

export interface OrderCreateRequest extends OrderBase {
  meal_id: number
}

export interface OrderUpdateRequest extends OrderBase {}

export interface OrderResponse {
  order_id: number
  amount_cents: number
  balance_cents: number
}

export interface OrderDetail {
  order_id: number
  meal_id: number
  meal_date: string
  meal_slot: string
  meal_title?: string
  qty: number
  options: string[]
  amount_cents: number
  status: 'active' | 'canceled'
  created_at: string
}

// 日志相关
export interface LogEntry {
  log_id: number
  user_id: number
  actor_id?: number
  action: string
  detail_json: any
  created_at: string
}