/**
 * 常量模块统一导出
 */

export * from './api'
export * from './ui'

// 通用常量
export const APP_CONFIG = {
  NAME: '罡好饭',
  VERSION: '2.0.0',
  DESCRIPTION: '和罡子哥一起健康每一天！'
} as const

export const VALIDATION = {
  MAX_NICKNAME_LENGTH: 100,
  MAX_DESCRIPTION_LENGTH: 1000,
  MIN_PRICE: 0,
  MAX_PRICE: 10000, // 单位：元
  MIN_CAPACITY: 1,
  MAX_CAPACITY: 1000,
  MAX_ORDER_QTY: 10
} as const