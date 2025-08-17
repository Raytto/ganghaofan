// date.ts - shared date utilities for calendar calculations

export function formatMonth(d = new Date()): string {
    const y = d.getFullYear();
    const m = `${d.getMonth() + 1}`.padStart(2, '0');
    return `${y}-${m}`;
}

export function formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = `${d.getMonth() + 1}`.padStart(2, '0');
    const day = `${d.getDate()}`.padStart(2, '0');
    return `${y}-${m}-${day}`;
}

export function parseDate(s: string): Date {
    const [y, m, d] = s.split('-').map(Number)
    return new Date(y, m - 1, d)
}

export function getMondayStart(d: Date): Date {
    const copy = new Date(d)
    const dow = copy.getDay() // 0 Sun .. 6 Sat
    const delta = ((dow + 6) % 7) // 0 Mon .. 6 Sun
    copy.setDate(copy.getDate() - delta)
    return copy
}

// month helpers for caching
export function monthKey(d: Date): string { return formatMonth(d) }
export function startOfMonth(d: Date): Date { return new Date(d.getFullYear(), d.getMonth(), 1) }
export function addMonths(d: Date, n: number): Date { return new Date(d.getFullYear(), d.getMonth() + n, 1) }
export function monthsBetween(a: Date, b: Date): string[] {
    const start = startOfMonth(a)
    const end = startOfMonth(b)
    const keys: string[] = []
    let cur = new Date(start)
    while (cur <= end) { keys.push(monthKey(cur)); cur = addMonths(cur, 1) }
    return keys
}

export function windowMonthsForNineWeeks(centerMonday: Date): string[] {
    const first = new Date(centerMonday); first.setDate(centerMonday.getDate() - 4 * 7)
    const last = new Date(centerMonday); last.setDate(centerMonday.getDate() + 4 * 7 + 6)
    return monthsBetween(first, last)
}
