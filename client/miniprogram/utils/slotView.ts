// slotView.ts - compute three-line texts and colors from meal data

export type SlotView = {
    meal_id?: number
    status: string
    left: number
    title?: string | null
    my: boolean
    bg: string
    fg: string
    l2: string
    l3: string
}

export type MealLite = {
    meal_id: number
    status: string
    capacity: number
    ordered_qty: number
    title?: string | null
    my_ordered?: boolean
}

export function toSlotView(it?: MealLite | null): SlotView {
    if (!it) return { status: 'none', left: 0, my: false, bg: '#616161', fg: '#C4C7C5', l2: '未发布', l3: '未订' }
    const left = Math.max(0, (it.capacity || 0) - (it.ordered_qty || 0))
    const status = it.status as string
    const my = !!(it.my_ordered)
    // line2/line3
    let l2 = '未发布'
    if (status === 'published') {
        if (left > 0) {
            l2 = '抢餐中'
        } else {
            l2 = '已订完'
        }
    } else if (status === 'locked') {
        l2 = '已锁定'
    } else if (status === 'completed') {
        l2 = '已结束'
    } else if (status === 'canceled') {
        l2 = '未发布'
    }
    // line3: for published with stock left, show remaining; otherwise show my status
    const l3 = (status === 'published' && left > 0) ? `剩${left}` : (my ? '已订' : '未订')
    // color rules
    let bg = '#616161', fg = '#C4C7C5'
    if (status === 'published') {
        if (left > 0) {
            bg = my ? '#F4511E' : '#F6BF26'
            fg = '#131314'
        } else {
            bg = my ? '#F4511E' : '#616161'
            fg = my ? '#131314' : '#C4C7C5'
        }
    } else if (status === 'locked') {
        bg = my ? '#8E24AA' : '#616161'
        fg = my ? '#131314' : '#C4C7C5'
    } else if (status === 'completed') {
        bg = my ? '#039BE5' : '#616161'
        fg = my ? '#131314' : '#C4C7C5'
    } else {
        // includes 'none' and 'canceled'
        bg = '#616161'; fg = '#C4C7C5'
    }
    return { meal_id: it.meal_id, status, left, title: it.title, my, bg, fg, l2, l3 }
}
