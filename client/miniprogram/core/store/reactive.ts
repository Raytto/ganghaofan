/**
 * 响应式状态工具
 * 为微信小程序页面和组件提供响应式状态绑定
 */

import { stateManager, StateListener } from './index'

/**
 * 页面响应式 Mixin
 * 为页面添加状态绑定能力
 */
export function createPageReactive() {
  return {
    /**
     * 绑定状态到页面数据
     */
    bindState(bindings: Record<string, string>) {
      const unsubscribers: (() => void)[] = []

      Object.entries(bindings).forEach(([dataKey, statePath]) => {
        // 初始化数据
        const initialValue = stateManager.getState(statePath)
        this.setData({ [dataKey]: initialValue })

        // 订阅状态变化
        const unsubscribe = stateManager.subscribe(statePath, (newValue) => {
          this.setData({ [dataKey]: newValue })
        })

        unsubscribers.push(unsubscribe)
      })

      // 保存取消订阅函数
      this._stateUnsubscribers = unsubscribers
    },

    /**
     * 页面卸载时清理订阅
     */
    onUnload() {
      if (this._stateUnsubscribers) {
        this._stateUnsubscribers.forEach(unsubscribe => unsubscribe())
        this._stateUnsubscribers = null
      }
    }
  }
}

/**
 * 组件响应式 Mixin
 * 为组件添加状态绑定能力
 */
export function createComponentReactive() {
  return {
    /**
     * 绑定状态到组件数据
     */
    bindState(bindings: Record<string, string>) {
      const unsubscribers: (() => void)[] = []

      Object.entries(bindings).forEach(([dataKey, statePath]) => {
        // 初始化数据
        const initialValue = stateManager.getState(statePath)
        this.setData({ [dataKey]: initialValue })

        // 订阅状态变化
        const unsubscribe = stateManager.subscribe(statePath, (newValue) => {
          this.setData({ [dataKey]: newValue })
        })

        unsubscribers.push(unsubscribe)
      })

      // 保存取消订阅函数
      this._stateUnsubscribers = unsubscribers
    },

    /**
     * 组件销毁时清理订阅
     */
    detached() {
      if (this._stateUnsubscribers) {
        this._stateUnsubscribers.forEach(unsubscribe => unsubscribe())
        this._stateUnsubscribers = null
      }
    }
  }
}

/**
 * 自动状态绑定装饰器
 * 为页面/组件方法提供简化的状态绑定
 */
export function withState(stateBindings: Record<string, string>) {
  return function(target: any) {
    const originalOnLoad = target.onLoad
    const originalOnReady = target.onReady
    const originalOnUnload = target.onUnload
    const originalDetached = target.detached

    // 页面生命周期
    if (typeof originalOnLoad === 'function' || !target.onReady) {
      target.onLoad = function(options: any) {
        bindStateToInstance(this, stateBindings)
        if (originalOnLoad) {
          originalOnLoad.call(this, options)
        }
      }
    }

    // 组件生命周期
    if (typeof originalOnReady === 'function' || target.behaviors) {
      target.onReady = function() {
        bindStateToInstance(this, stateBindings)
        if (originalOnReady) {
          originalOnReady.call(this)
        }
      }
    }

    // 清理函数
    target.onUnload = function() {
      cleanupStateBinding(this)
      if (originalOnUnload) {
        originalOnUnload.call(this)
      }
    }

    target.detached = function() {
      cleanupStateBinding(this)
      if (originalDetached) {
        originalDetached.call(this)
      }
    }

    return target
  }
}

/**
 * 绑定状态到实例
 */
function bindStateToInstance(instance: any, bindings: Record<string, string>) {
  const unsubscribers: (() => void)[] = []

  Object.entries(bindings).forEach(([dataKey, statePath]) => {
    // 初始化数据
    const initialValue = stateManager.getState(statePath)
    instance.setData({ [dataKey]: initialValue })

    // 订阅状态变化
    const unsubscribe = stateManager.subscribe(statePath, (newValue) => {
      instance.setData({ [dataKey]: newValue })
    })

    unsubscribers.push(unsubscribe)
  })

  instance._stateUnsubscribers = unsubscribers
}

/**
 * 清理状态绑定
 */
function cleanupStateBinding(instance: any) {
  if (instance._stateUnsubscribers) {
    instance._stateUnsubscribers.forEach((unsubscribe: () => void) => unsubscribe())
    instance._stateUnsubscribers = null
  }
}

/**
 * 计算属性
 * 基于状态创建衍生值
 */
export class ComputedProperty<T> {
  private _value: T
  private _compute: () => T
  private _dependencies: string[]
  private _unsubscribers: (() => void)[] = []
  private _listeners: Set<(value: T) => void> = new Set()

  constructor(compute: () => T, dependencies: string[]) {
    this._compute = compute
    this._dependencies = dependencies
    this._value = compute()

    // 订阅依赖变化
    dependencies.forEach(dep => {
      const unsubscribe = stateManager.subscribe(dep, () => {
        const newValue = this._compute()
        if (newValue !== this._value) {
          const oldValue = this._value
          this._value = newValue
          this._listeners.forEach(listener => {
            try {
              listener(newValue)
            } catch (error) {
              console.error('Computed property listener error:', error)
            }
          })
        }
      })
      this._unsubscribers.push(unsubscribe)
    })
  }

  get value(): T {
    return this._value
  }

  /**
   * 订阅计算属性变化
   */
  subscribe(listener: (value: T) => void): () => void {
    this._listeners.add(listener)
    return () => this._listeners.delete(listener)
  }

  /**
   * 销毁计算属性
   */
  destroy() {
    this._unsubscribers.forEach(unsubscribe => unsubscribe())
    this._unsubscribers = []
    this._listeners.clear()
  }
}

/**
 * 创建计算属性
 */
export function computed<T>(compute: () => T, dependencies: string[]): ComputedProperty<T> {
  return new ComputedProperty(compute, dependencies)
}

/**
 * 状态操作助手
 */
export const stateActions = {
  /**
   * 切换布尔值状态
   */
  toggle(path: string) {
    const currentValue = stateManager.getState<boolean>(path)
    stateManager.setState(path, !currentValue)
  },

  /**
   * 增加数值状态
   */
  increment(path: string, delta = 1) {
    const currentValue = stateManager.getState<number>(path) || 0
    stateManager.setState(path, currentValue + delta)
  },

  /**
   * 减少数值状态
   */
  decrement(path: string, delta = 1) {
    const currentValue = stateManager.getState<number>(path) || 0
    stateManager.setState(path, currentValue - delta)
  },

  /**
   * 添加到数组
   */
  push(path: string, item: any) {
    const currentArray = stateManager.getState<any[]>(path) || []
    stateManager.setState(path, [...currentArray, item])
  },

  /**
   * 从数组移除
   */
  remove(path: string, predicate: (item: any, index: number) => boolean) {
    const currentArray = stateManager.getState<any[]>(path) || []
    const newArray = currentArray.filter((item, index) => !predicate(item, index))
    stateManager.setState(path, newArray)
  },

  /**
   * 更新数组中的项
   */
  updateInArray(path: string, predicate: (item: any, index: number) => boolean, updater: (item: any) => any) {
    const currentArray = stateManager.getState<any[]>(path) || []
    const newArray = currentArray.map((item, index) => {
      return predicate(item, index) ? updater(item) : item
    })
    stateManager.setState(path, newArray)
  },

  /**
   * 合并对象状态
   */
  merge(path: string, updates: Record<string, any>) {
    const currentValue = stateManager.getState<Record<string, any>>(path) || {}
    stateManager.setState(path, { ...currentValue, ...updates })
  }
}