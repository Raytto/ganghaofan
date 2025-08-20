/**
 * UI组件相关类型定义
 */

// 通用组件Props
export interface BaseComponentProps {
  className?: string
  style?: string
}

// 按钮组件
export interface ButtonProps extends BaseComponentProps {
  type?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  loading?: boolean
  openType?: string
}

// 输入框组件
export interface InputProps extends BaseComponentProps {
  value: string
  placeholder?: string
  maxlength?: number
  disabled?: boolean
  readonly?: boolean
  type?: 'text' | 'number' | 'password'
}

// 对话框组件
export interface DialogProps extends BaseComponentProps {
  show: boolean
  title?: string
  showClose?: boolean
  maskClosable?: boolean
  width?: string
  maxHeight?: string
}

// 导航栏组件
export interface NavigationBarProps extends BaseComponentProps {
  title: string
  background?: string
  color?: string
  back?: boolean
  delta?: number
  loading?: boolean
}

// 日历组件
export interface CalendarProps extends BaseComponentProps {
  month: string
  weeks: any[]
  adminView: boolean
  onSlotTap?: (event: any) => void
  onTouchStart?: (event: any) => void
  onTouchMove?: (event: any) => void
  onTouchEnd?: (event: any) => void
}

// 卡片组件
export interface SlotCardProps extends BaseComponentProps {
  slot: any
  adminView: boolean
  onTap?: (event: any) => void
}

// Toast配置
export interface ToastConfig {
  title: string
  icon?: 'success' | 'error' | 'loading' | 'none'
  duration?: number
  mask?: boolean
}

// Modal配置
export interface ModalConfig {
  title: string
  content?: string
  showCancel?: boolean
  cancelText?: string
  confirmText?: string
  editable?: boolean
  placeholderText?: string
}

// 事件处理器类型
export interface EventHandler<T = any> {
  (event: T): void
}

export interface CustomEventHandler<T = any> {
  (event: WechatMiniprogram.CustomEvent<T>): void
}

export interface TouchEventHandler {
  (event: WechatMiniprogram.TouchEvent): void
}