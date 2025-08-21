/**
 * 餐次相关API封装
 */

import { httpClient } from './base'
import { API_ENDPOINTS } from '../constants'
import type { 
  Meal,
  MealBase,
  MealCalendarResponse,
  MealBatchCalendarResponse
} from '../../types'

export class MealAPI {
  /**
   * 获取餐次列表（支持筛选）
   */
  async getMealsList(params?: {
    status?: string
    date_from?: string
    date_to?: string
    limit?: number
    offset?: number
  }): Promise<any> {
    const queryParams = new URLSearchParams()
    
    if (params?.status) queryParams.append('status', params.status)
    if (params?.date_from) queryParams.append('date_from', params.date_from)
    if (params?.date_to) queryParams.append('date_to', params.date_to)
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.offset) queryParams.append('offset', params.offset.toString())

    const url = `${API_ENDPOINTS.MEAL_LIST}?${queryParams.toString()}`

    return httpClient.get(url, {
      showLoading: params?.offset === 0,
      cacheDuration: 2 * 60 * 1000, // 2分钟缓存
      retryConfig: {
        maxAttempts: 2,
        baseDelay: 500,
        maxDelay: 2000,
        backoffFactor: 2,
        retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
      }
    })
  }

  /**
   * 获取指定月份的餐次日历
   */
  async getCalendar(month: string): Promise<MealCalendarResponse> {
    return httpClient.get<MealCalendarResponse>(
      `${API_ENDPOINTS.CALENDAR}?month=${month}`,
      { 
        showLoading: true,
        cacheDuration: 2 * 60 * 1000, // 2分钟缓存
        retryConfig: {
          maxAttempts: 2,
          baseDelay: 500,
          maxDelay: 2000,
          backoffFactor: 2,
          retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
        }
      }
    )
  }

  /**
   * 批量获取多个月份的餐次日历
   */
  async getCalendarBatch(months: string[]): Promise<MealBatchCalendarResponse> {
    const monthsParam = encodeURIComponent(months.join(','))
    return httpClient.get<MealBatchCalendarResponse>(
      `${API_ENDPOINTS.CALENDAR_BATCH}?months=${monthsParam}`,
      {
        cacheDuration: 5 * 60 * 1000, // 5分钟缓存
        retryConfig: {
          maxAttempts: 3,
          baseDelay: 1000,
          maxDelay: 5000,
          backoffFactor: 2,
          retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
        }
      }
    )
  }

  /**
   * 获取餐次详情
   */
  async getMealDetail(mealId: number): Promise<Meal> {
    return httpClient.get<Meal>(
      API_ENDPOINTS.MEAL_DETAIL(mealId),
      { 
        showLoading: true,
        cacheDuration: 10 * 60 * 1000, // 10分钟缓存，餐次详情相对稳定
        retryConfig: {
          maxAttempts: 2,
          baseDelay: 500,
          maxDelay: 2000,
          backoffFactor: 2,
          retryableErrors: ['timeout', 'fail', 'NETWORK_ERROR']
        }
      }
    )
  }

  /**
   * 创建餐次（管理员功能）
   */
  async createMeal(mealData: MealBase): Promise<{ meal_id: number }> {
    return httpClient.post<{ meal_id: number }>(
      API_ENDPOINTS.MEAL_CREATE,
      mealData,
      { showLoading: true }
    )
  }

  /**
   * 更新餐次（管理员功能）
   */
  async updateMeal(mealId: number, mealData: Partial<MealBase>): Promise<{ meal_id: number }> {
    return httpClient.put<{ meal_id: number }>(
      API_ENDPOINTS.MEAL_UPDATE(mealId),
      mealData,
      { showLoading: true }
    )
  }

  /**
   * 危险重发餐次（管理员功能）
   */
  async repostMeal(mealId: number, mealData: MealBase): Promise<{ meal_id: number }> {
    return httpClient.post<{ meal_id: number }>(
      API_ENDPOINTS.MEAL_REPOST(mealId),
      mealData,
      { showLoading: true }
    )
  }

  /**
   * 锁定餐次（管理员功能）
   */
  async lockMeal(mealId: number): Promise<{ meal_id: number; status: string }> {
    return httpClient.post<{ meal_id: number; status: string }>(
      API_ENDPOINTS.MEAL_LOCK(mealId),
      {},
      { showLoading: true }
    )
  }

  /**
   * 取消锁定餐次（管理员功能）
   */
  async unlockMeal(mealId: number): Promise<{ meal_id: number; status: string }> {
    return httpClient.post<{ meal_id: number; status: string }>(
      API_ENDPOINTS.MEAL_UNLOCK(mealId),
      {},
      { showLoading: true }
    )
  }

  /**
   * 标记餐次完成（管理员功能）
   */
  async completeMeal(mealId: number): Promise<{ meal_id: number; status: string }> {
    return httpClient.post<{ meal_id: number; status: string }>(
      API_ENDPOINTS.MEAL_COMPLETE(mealId),
      {},
      { showLoading: true }
    )
  }

  /**
   * 取消餐次（管理员功能）
   */
  async cancelMeal(mealId: number): Promise<{ meal_id: number; status: string }> {
    return httpClient.post<{ meal_id: number; status: string }>(
      API_ENDPOINTS.MEAL_CANCEL(mealId),
      {},
      { showLoading: true }
    )
  }
}

// 导出默认实例
export const mealAPI = new MealAPI()