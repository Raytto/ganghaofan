const BASE_URL = 'http://127.0.0.1:8000/api/v1';
const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
    try { return wx.getStorageSync(TOKEN_KEY) || null; } catch { return null; }
}

export function setToken(t: string) {
    try { wx.setStorageSync(TOKEN_KEY, t); } catch { }
}

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
        // auto login on 401 once
        if (e && (e.code === 401 || e.code === '401')) {
            try { await loginAndGetToken() } catch { /* ignore */ }
            return await doOnce()
        }
        throw e
    }
}

export async function loginAndGetToken(): Promise<string> {
    const loginRes = await new Promise<WechatMiniprogram.LoginSuccessCallbackResult>((resolve, reject) => {
        wx.login({ success: resolve, fail: reject });
    });
    const data = await request<{ token: string }>(`/auth/login`, { method: 'POST', data: { code: loginRes.code } });
    setToken(data.token);
    return data.token;
}

export type MealCalendarItem = {
    meal_id: number;
    date: string; // YYYY-MM-DD
    slot: 'lunch' | 'dinner';
    title: string | null;
    base_price_cents: number;
    options: any;
    capacity: number;
    per_user_limit: number;
    status: 'published' | 'locked' | 'completed' | 'canceled';
    ordered_qty: number;
    my_ordered?: boolean;
};

export async function getCalendar(month: string): Promise<{ month: string; meals: MealCalendarItem[] }> {
    return request(`/calendar?month=${month}`, { method: 'GET' });
}

export async function getCalendarBatch(months: string[]): Promise<{ months: Record<string, MealCalendarItem[]> }> {
    const q = encodeURIComponent(months.join(','));
    return request(`/calendar/batch?months=${q}`, { method: 'GET' });
}

export const api = { request, loginAndGetToken, getCalendar, getCalendarBatch };
