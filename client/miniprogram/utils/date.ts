/**
 * 日期时间工具函数库
 * 为日历组件提供核心的日期计算和格式化功能
 * 
 * 主要功能：
 * - 日期格式化和解析（YYYY-MM-DD格式）
 * - 月份和周的边界计算
 * - 9周窗口的月份范围计算
 * - 工作日导向的日历逻辑支持
 * 
 * 设计原则：
 * - 以周一作为一周的开始（符合工作日历习惯）
 * - 支持跨月的周数据计算
 * - 为缓存和预加载提供月份范围工具
 */

/**
 * 格式化月份为 YYYY-MM 字符串
 */
export function formatMonth(d = new Date()): string {
    const y = d.getFullYear();
    const m = `${d.getMonth() + 1}`.padStart(2, '0');
    return `${y}-${m}`;
}

/**
 * 格式化日期为 YYYY-MM-DD 字符串
 */
export function formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = `${d.getMonth() + 1}`.padStart(2, '0');
    const day = `${d.getDate()}`.padStart(2, '0');
    return `${y}-${m}-${day}`;
}

/**
 * 解析 YYYY-MM-DD 字符串为Date对象
 */
export function parseDate(s: string): Date {
    const [y, m, d] = s.split('-').map(Number)
    return new Date(y, m - 1, d)
}

/**
 * 获取指定日期所在周的周一日期
 * 
 * @param d 任意日期
 * @returns 该周周一的Date对象
 * 
 * Note: 
 *   采用周一作为一周开始，符合工作日历的业务需求
 *   用于计算9周窗口的边界和数据分组
 */
export function getMondayStart(d: Date): Date {
    const copy = new Date(d)
    const dow = copy.getDay() // 0=周日, 1=周一, ..., 6=周六
    const delta = ((dow + 6) % 7) // 转换为周一开始：0=周一, 1=周二, ..., 6=周日
    copy.setDate(copy.getDate() - delta)
    return copy
}

// 月份操作工具函数，用于数据缓存和批量查询
export function monthKey(d: Date): string { return formatMonth(d) }
export function startOfMonth(d: Date): Date { return new Date(d.getFullYear(), d.getMonth(), 1) }
export function addMonths(d: Date, n: number): Date { return new Date(d.getFullYear(), d.getMonth() + n, 1) }

/**
 * 计算两个日期之间的所有月份列表
 * 
 * @param a 起始日期
 * @param b 结束日期
 * @returns 月份字符串数组，格式为 ['YYYY-MM', ...]
 */
export function monthsBetween(a: Date, b: Date): string[] {
    const start = startOfMonth(a)
    const end = startOfMonth(b)
    const keys: string[] = []
    let cur = new Date(start)
    while (cur <= end) { 
        keys.push(monthKey(cur)); 
        cur = addMonths(cur, 1) 
    }
    return keys
}

/**
 * 计算9周窗口涉及的月份范围
 * 用于首页日历的数据预加载，确保9周数据的完整性
 * 
 * @param centerMonday 中心周的周一日期
 * @returns 涉及的月份列表，通常为2-3个月
 * 
 * Note:
 *   9周 = 前4周 + 当前周 + 后4周
 *   跨月边界时自动包含相关月份
 */
export function windowMonthsForNineWeeks(centerMonday: Date): string[] {
    // 计算9周窗口的起始和结束日期
    const first = new Date(centerMonday); 
    first.setDate(centerMonday.getDate() - 4 * 7) // 前4周
    
    const last = new Date(centerMonday); 
    last.setDate(centerMonday.getDate() + 4 * 7 + 6) // 后4周+周末
    
    return monthsBetween(first, last)
}
