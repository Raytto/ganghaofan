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
   * 获取指定月份的餐次日历
   */
  async getCalendar(month: string): Promise<MealCalendarResponse> {
    return httpClient.get<MealCalendarResponse>(
      `${API_ENDPOINTS.CALENDAR}?month=${month}`,
      { showLoading: true }
    )
  }

  /**
   * 批量获取多个月份的餐次日历
   */
  async getCalendarBatch(months: string[]): Promise<MealBatchCalendarResponse> {
    const monthsParam = encodeURIComponent(months.join(','))
    return httpClient.get<MealBatchCalendarResponse>(
      `${API_ENDPOINTS.CALENDAR_BATCH}?months=${monthsParam}`
    )
  }

  /**
   * 获取餐次详情
   */
  async getMealDetail(mealId: number): Promise<Meal> {
    return httpClient.get<Meal>(
      API_ENDPOINTS.MEAL_DETAIL(mealId),
      { showLoading: true }
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