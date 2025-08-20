/**
 * 业务逻辑相关类型定义
 */

import { Meal, MealOption } from './api'

// 日历相关
export interface CalendarCell {
  dateKey: string
  day: number
  isCurrentMonth: boolean
  isWeekend: boolean
  dow: string
  isToday: boolean
  lunch: SlotView
  dinner: SlotView
  dateLabel: string
}

export interface SlotView {
  status: 'none' | 'published' | 'locked' | 'completed' | 'canceled'
  text1: string  // 第一行：午餐/晚餐
  text2: string  // 第二行：状态描述
  text3: string  // 第三行：辅助信息
  bgColor: string
  textColor: string
  mealId?: number
  left?: number
  my?: boolean
}

// 发布弹窗相关
export interface PublishForm {
  date: string
  slot: 'lunch' | 'dinner'
  description: string
  basePrice: number  // 单位：元
  capacity: number
  options: PublishOption[]
}

export interface PublishOption {
  id: string
  name: string
  price: number  // 单位：元
}

export interface PublishDialogData {
  show: boolean
  mode: 'create' | 'edit'
  mealId?: number
  original?: Meal
  needsRepost: boolean
  readonly: boolean
  submitting: boolean
  form: PublishForm
}

// 订单弹窗相关
export interface OrderDialogData {
  show: boolean
  detail: OrderDetail
  selectedOptions: string[]
  action: 'create' | 'update' | 'readonly'
  readonlyMsg?: string
}

export interface OrderDetail {
  meal_id: number
  date: string
  slot: string
  description?: string
  capacity: number
  ordered_qty: number
  options: MealOption[]
  base_price_cents: number
  total_cents: number
  balance_cents?: number
  action: 'create' | 'update' | 'readonly'
  readonlyMsg?: string
}

// 主题相关
export interface ThemeConfig {
  isDark: boolean
  colors: {
    primary: string
    background: string
    surface: string
    text: string
    textSecondary: string
    border: string
    success: string
    warning: string
    error: string
  }
}

// 应用状态
export interface AppState {
  // 用户信息
  user?: {
    id: number
    openId: string
    nickname?: string
    isAdmin: boolean
    balance: number
  }
  
  // 认证状态
  auth: {
    token?: string
    isLoggedIn: boolean
  }
  
  // 主题状态
  theme: {
    mode: 'dark' | 'light'
    config: ThemeConfig
  }
  
  // 管理员状态
  admin: {
    canAdmin: boolean
    adminViewEnabled: boolean
  }
  
  // 全局UI状态
  ui: {
    loading: boolean
    toast?: {
      title: string
      icon?: 'success' | 'error' | 'loading' | 'none'
      duration?: number
    }
  }
}