import { resolvePassphrase, setDbKey } from './api'

export type PromptOptions = {
    title?: string
    placeholder?: string
    onSuccess?: (key: string) => void
    onError?: (err: any) => void
}

// 显示口令设置弹窗：成功后会持久化DB Key并弹出成功提示
export function promptPassphrase(opts?: PromptOptions): Promise<string | null> {
    const title = opts?.title || '对口令'
    const placeholderText = opts?.placeholder || '输入口令'
    return new Promise((resolve) => {
        wx.showModal({
            title,
            editable: true,
            placeholderText,
            showCancel: false,
            confirmText: '确定',
            success: async (res) => {
                if (!res.confirm) {
                    // 没有取消按钮，理论上不会触发；为稳妥起见重试
                    promptPassphrase(opts).then(resolve)
                    return
                }
                const val = (res.content || '').trim()
                if (!val) {
                    wx.showToast({ title: '请输入口令', icon: 'none' })
                    // 空输入时继续弹出
                    promptPassphrase(opts).then(resolve)
                    return
                }
                try {
                    const { key } = await resolvePassphrase(val)
                    setDbKey(key || null)
                    wx.showToast({ title: '已设置口令', icon: 'success' })
                    if (opts?.onSuccess) opts.onSuccess(key)
                    resolve(key)
                } catch (e: any) {
                    wx.showToast({ title: '口令没对上', icon: 'none' })
                    if (opts?.onError) opts.onError(e)
                    // 失败后立刻再次弹窗，直到用户取消或输入正确
                    promptPassphrase(opts).then(resolve)
                }
            }
        })
    })
}
