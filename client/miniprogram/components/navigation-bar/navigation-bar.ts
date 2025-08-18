/**
 * 自定义导航栏组件
 * 
 * 功能：
 * - 替代小程序默认导航栏，提供更灵活的样式定制
 * - 自动适配iOS/Android的安全区域和胶囊按钮位置
 * - 支持多插槽内容定制（左侧、中间、右侧）
 * - 内置返回按钮和加载状态显示
 * 
 * 设计考虑：
 * - 深色主题适配，默认背景色为#1B1B1B
 * - 胶囊按钮区域自动避让，确保内容不被遮挡
 * - 支持显示/隐藏动画效果
 * - 跨平台兼容性处理
 */

Component({
  options: {
    multipleSlots: true // 启用多slot支持，允许左中右三个插槽
  },
  /**
   * 组件对外属性配置
   */
  properties: {
    extClass: {
      type: String,
      value: ''
    },
    title: {
      type: String,
      value: ''
    },
    background: {
      type: String,
      value: '#1B1B1B'
    },
    color: {
      type: String,
      value: '#C9D1D9'
    },
    back: {
      type: Boolean,
      value: true
    },
    loading: {
      type: Boolean,
      value: false
    },
    homeButton: {
      type: Boolean,
      value: false,
    },
    animated: {
      // 显示隐藏的时候opacity动画效果
      type: Boolean,
      value: true
    },
    show: {
      // 显示隐藏导航，隐藏的时候navigation-bar的高度占位还在
      type: Boolean,
      value: true,
      observer: '_showChange'
    },
    // back为true的时候，返回的页面深度
    delta: {
      type: Number,
      value: 1
    },
  },
  /**
   * 组件的初始数据
   */
  data: {
    displayStyle: ''
  },
  lifetimes: {
    attached() {
      const rect = wx.getMenuButtonBoundingClientRect()
      wx.getSystemInfo({
        success: (res) => {
          const isAndroid = res.platform === 'android'
          const isDevtools = res.platform === 'devtools'
          this.setData({
            ios: !isAndroid,
            innerPaddingRight: `padding-right: ${res.windowWidth - rect.left}px`,
            leftWidth: `width: ${res.windowWidth - rect.left}px`,
            safeAreaTop: isDevtools || isAndroid ? `height: calc(var(--height) + ${res.safeArea.top}px); padding-top: ${res.safeArea.top}px` : ``
          })
        }
      })
    },
  },
  /**
   * 组件的方法列表
   */
  methods: {
    _showChange(show: boolean) {
      const animated = this.data.animated
      let displayStyle = ''
      if (animated) {
        displayStyle = `opacity: ${show ? '1' : '0'
          };transition:opacity 0.5s;`
      } else {
        displayStyle = `display: ${show ? '' : 'none'}`
      }
      this.setData({
        displayStyle
      })
    },
    back() {
      const data = this.data
      if (data.delta) {
        wx.navigateBack({
          delta: data.delta
        })
      }
      this.triggerEvent('back', { delta: data.delta }, {})
    }
  },
})
