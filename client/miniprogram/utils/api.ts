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

const BASE_URL = 'http://us.pangruitao.com:8000/api/v1';
const TOKEN_KEY = 'auth_token';
const DB_KEY_MAP_KEY = 'db_key_map'; // { [open_id]: key }
const DB_KEY_GLOBAL_KEY = 'db_key_global'; // 临时全局 Key（未拿到 open_id 之前使用）
const CURRENT_OPEN_ID_KEY = 'current_open_id';

// 调试信息
console.log('=== utils/api.ts 调试信息 ===')
console.log('BASE_URL:', BASE_URL)
console.log('时间戳:', new Date().toISOString())
console.log('=============================')

export function getToken(): string | null {
    try { return wx.getStorageSync(TOKEN_KEY) || null; } catch { return null; }
}

export function setToken(t: string) {
    try {
        wx.setStorageSync(TOKEN_KEY, t);
        // reset cached open_id on new token to ensure proper per-user scoping
        try { wx.removeStorageSync(CURRENT_OPEN_ID_KEY); } catch { }
    } catch { }
}

export function getCurrentOpenId(): string | null {
    try { return wx.getStorageSync(CURRENT_OPEN_ID_KEY) || null; } catch { return null; }
}

async function ensureCurrentOpenId(): Promise<string | null> {
    let oid = getCurrentOpenId();
    if (oid) return oid;
    try {
        const u: any = await request('/users/me', { method: 'GET' });
        oid = (u && u.open_id) ? String(u.open_id) : null;
        if (oid) {
            wx.setStorageSync(CURRENT_OPEN_ID_KEY, oid);
            // 如果存在临时全局 DB Key，则在拿到 open_id 后迁移到按用户作用域存储
            try {
                const gk = wx.getStorageSync(DB_KEY_GLOBAL_KEY) as string | undefined;
                if (gk && typeof gk === 'string' && gk.trim()) {
                    const map = (wx.getStorageSync(DB_KEY_MAP_KEY) || {}) as Record<string, string>;
                    map[oid] = gk;
                    wx.setStorageSync(DB_KEY_MAP_KEY, map);
                    try { wx.removeStorageSync(DB_KEY_GLOBAL_KEY); } catch { }
                }
            } catch { }
        }
        return oid;
    } catch {
        return null;
    }
}

export function getDbKey(): string | null {
    try {
        const map = (wx.getStorageSync(DB_KEY_MAP_KEY) || {}) as Record<string, string>;
        const oid = getCurrentOpenId();
        if (oid && map && typeof map === 'object' && map[oid]) return map[oid];
        // 若尚未拿到 open_id 或未设置用户作用域 key，则回退使用全局临时 Key
        const gk = wx.getStorageSync(DB_KEY_GLOBAL_KEY) as string | undefined;
        if (gk && typeof gk === 'string' && gk.trim()) return gk;
        // 默认使用development key用于开发环境
        return 'development';
    } catch { return 'development'; }
}

export function setDbKey(k: string | null) {
    try {
        const oid = getCurrentOpenId();
        if (oid) {
            const map = (wx.getStorageSync(DB_KEY_MAP_KEY) || {}) as Record<string, string>;
            if (k) {
                map[oid] = k;
            } else {
                if (oid in map) delete map[oid];
            }
            wx.setStorageSync(DB_KEY_MAP_KEY, map);
        } else {
            // 在 open_id 未知时，先保存到全局临时 Key，保证受保护接口（/users/me 等）可携带 X-DB-Key
            if (k && k.trim()) wx.setStorageSync(DB_KEY_GLOBAL_KEY, k);
            else try { wx.removeStorageSync(DB_KEY_GLOBAL_KEY) } catch { }
        }
    } catch { }
}

/**
 * 通用HTTP请求封装
 * 自动处理认证头、错误响应和401重试逻辑
 */
async function request<T = any>(
    path: string,
    options: Partial<WechatMiniprogram.RequestOption<any>> = {}
): Promise<T> {
    // 直接调用的口令解析（避免在403处理时通过request造成递归）
    const resolvePassphraseRaw = (passphrase: string): Promise<{ key: string }> => {
        const url = `${BASE_URL}/env/resolve`;
        const headers: Record<string, string> = {};
        const token = getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        return new Promise((resolve, reject) => {
            wx.request({
                method: 'POST',
                url,
                data: { passphrase },
                header: headers,
                success: (res) => {
                    const sc = res.statusCode || 0;
                    if (sc >= 200 && sc < 300) resolve(res.data as any);
                    else reject(res.data || { code: sc, message: 'HTTP Error' });
                },
                fail: (e) => reject(e),
            });
        });
    };

    const promptPassphraseInline = (): Promise<string | null> => {
        return new Promise((resolve) => {
            wx.showModal({
                title: '对口令',
                editable: true,
                placeholderText: '输入口令',
                showCancel: false,
                confirmText: '确定',
                success: async (res) => {
                    if (!res.confirm) { resolve(null); return; }
                    const val = (res.content || '').trim();
                    if (!val) { wx.showToast({ title: '请输入口令', icon: 'none' }); promptPassphraseInline().then(resolve); return; }
                    try {
                        const { key } = await resolvePassphraseRaw(val);
                        setDbKey(key || null);
                        wx.showToast({ title: '已设置口令', icon: 'success' });
                        resolve(key || null);
                    } catch {
                        wx.showToast({ title: '口令没对上', icon: 'none' });
                        promptPassphraseInline().then(resolve);
                    }
                },
            });
        });
    };

    const doOnce = (): Promise<T> => {
        let url = path.startsWith('http') ? path : `${BASE_URL}${path}`;
        
        // 强制替换任何127.0.0.1地址，确保使用公网地址
        if (url.includes('127.0.0.1:8000')) {
            url = url.replace('127.0.0.1:8000', 'us.pangruitao.com:8000');
            console.log('强制替换URL:', url);
        }
        
        const headers: Record<string, string> = options.header ? { ...(options.header as any) } : {};
        const token = getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const dbKey = getDbKey();
        if (dbKey) headers['X-DB-Key'] = dbKey;

        return new Promise((resolve, reject) => {
            console.log(`Making request to: ${url}`);
            wx.request({
                ...options,
                url,
                header: headers,
                timeout: 10000, // 10秒超时
                success: (res) => {
                    const sc = res.statusCode || 0
                    if (sc >= 200 && sc < 300) {
                        console.log(`Request success: ${url} - ${sc}`);
                        resolve(res.data as T)
                    } else {
                        console.log(`Request error: ${url} - ${sc}`);
                        const payload: any = res.data || {}
                        const err = { code: payload.code || sc, message: payload.message || 'HTTP Error', detail: payload }
                        reject(err)
                    }
                },
                fail: (e) => {
                    console.log(`Request failed: ${url}`, e);
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
        // 403错误时提示输入口令并重试一次（跳过对/env/resolve本身的处理以防递归）
        if (e && (e.code === 403 || e.code === '403')) {
            const p = (path || '').toLowerCase();
            if (!p.includes('/env/resolve')) {
                const key = await promptPassphraseInline();
                if (key) return await doOnce();
            }
        }
        // 网络错误时等待片刻后重试一次
        if (e && e.code === -1 && e.message === 'Network Error') {
            console.log('Network error detected, retrying after 500ms...');
            await new Promise(resolve => setTimeout(resolve, 500));
            try {
                const result = await doOnce()
                console.log('Retry successful!');
                return result;
            } catch (retryError) {
                console.log('Retry failed, throwing original error');
                // 重试失败，抛出原错误
            }
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
    // store current open_id for per-user DB key scoping
    try { await ensureCurrentOpenId(); } catch { }
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
    // 避免对逗号进行URL编码，直接传递给后端
    const q = months.join(',');
    return request(`/calendar/batch?months=${q}`, { method: 'GET' });
}

export async function resolvePassphrase(passphrase: string): Promise<{ key: string }> {
    return request('/env/resolve', { method: 'POST', data: { passphrase } });
}

// 导出API对象供其他模块使用
export const api = { request, loginAndGetToken, getCalendar, getCalendarBatch, resolvePassphrase };
