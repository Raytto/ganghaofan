/**
 * 前端API请求封装模块
 * 提供与后端服务的统一通信接口，包含认证、错误处理和自动重试机制
 * 
 * 主要功能：
 * - 微信小程序登录和token管理
 * - 统一的HTTP请求封装，自动处理认证头
 * - 401错误的自动登录重试机制
 * - 餐次日历数据的单月和批量查询
 * 
 * 使用说明：
 * - 所有API调用自动携带JWT token
 * - 网络错误和HTTP错误统一处理
 * - 支持微信小程序的request API
 */

const BASE_URL = 'http://127.0.0.1:8000/api/v1';
const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
    try { return wx.getStorageSync(TOKEN_KEY) || null; } catch { return null; }
}

export function setToken(t: string) {
    try { wx.setStorageSync(TOKEN_KEY, t); } catch { }
}

/**
 * 通用HTTP请求封装
 * 自动处理认证头、错误响应和401重试逻辑
 */
async function request<T = any>(
    path: string,
    options: Partial<WechatMiniprogram.RequestOption<any>> = {}
): Promise<T> {
    const doOnce = (): Promise<T> => {
        const url = path.startsWith('http') ? path : `${BASE_URL}${path}`;
        const headers: Record<string, string> = options.header ? { ...(options.header as any) } : {};
        const token = getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        
        return new Promise((resolve, reject) => {
            wx.request({
                ...options,
                url,
                header: headers,
                success: (res) => {
                    const sc = res.statusCode || 0
                    if (sc >= 200 && sc < 300) {
                        resolve(res.data as T)
                    } else {
                        const payload: any = res.data || {}
                        const err = { code: payload.code || sc, message: payload.message || 'HTTP Error', detail: payload }
                        reject(err)
                    }
                },
                fail: (e) => {
                    reject({ code: -1, message: 'Network Error', detail: e })
                },
            })
        })
    }
    
    try {
        return await doOnce()
    } catch (e: any) {
        // 401错误时自动尝试重新登录一次，避免用户手动处理认证失效
        if (e && (e.code === 401 || e.code === '401')) {
            try { await loginAndGetToken() } catch { /* ignore login failure */ }
            return await doOnce()
        }
        throw e
    }
}

/**
 * 微信登录并获取JWT token
 * 
 * Returns:
 *   Promise<string>: JWT token字符串
 *   
 * Note:
 *   调用微信wx.login获取code，然后与后端交换token
 *   token会自动保存到本地存储中
 */
export async function loginAndGetToken(): Promise<string> {
    const loginRes = await new Promise<WechatMiniprogram.LoginSuccessCallbackResult>((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
    });
    const data = await request<{ token: string }>(`/auth/login`, { method: 'POST', data: { code: loginRes.code } });
    setToken(data.token);
    return data.token;
}

/**
 * 餐次日历数据的类型定义
 */
export type MealCalendarItem = {
    meal_id: number;
    date: string; // YYYY-MM-DD
    slot: 'lunch' | 'dinner';
    title: string | null;
    base_price_cents: number;
    options: any;  // 配菜选项的动态结构
    capacity: number;
    per_user_limit: number;
    status: 'published' | 'locked' | 'completed' | 'canceled';
    ordered_qty: number;  // 当前已订数量
    my_ordered?: boolean;  // 当前用户是否已订
};

/**
 * 获取指定月份的餐次日历
 * 
 * Args:
 *   month: 月份字符串，格式为 YYYY-MM
 *   
 * Returns:
 *   Promise: 包含月份和餐次列表的对象
 */
export async function getCalendar(month: string): Promise<{ month: string; meals: MealCalendarItem[] }> {
    return request(`/calendar?month=${month}`, { method: 'GET' });
}

/**
 * 批量获取多个月份的餐次日历
 * 主要用于首页的9周窗口数据预加载
 * 
 * Args:
 *   months: 月份数组，如 ['2024-08', '2024-09']
 *   
 * Returns:
 *   Promise: 包含各月餐次数据的对象
 */
export async function getCalendarBatch(months: string[]): Promise<{ months: Record<string, MealCalendarItem[]> }> {
    const q = encodeURIComponent(months.join(','));
    return request(`/calendar/batch?months=${q}`, { method: 'GET' });
}

// 导出API对象供其他模块使用
export const api = { request, loginAndGetToken, getCalendar, getCalendarBatch };
