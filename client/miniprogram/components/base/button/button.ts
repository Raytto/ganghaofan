/**
 * 基础按钮组件
 * 
 * @description 标准化的按钮组件，支持多种样式和状态
 * @version 2.0.0
 */
Component({
  properties: {
    /** 按钮类型 */
    type: {
      type: String,
      value: 'primary' // primary, secondary, danger, ghost
    },
    /** 按钮大小 */
    size: {
      type: String,
      value: 'medium' // small, medium, large
    },
    /** 是否禁用 */
    disabled: {
      type: Boolean,
      value: false
    },
    /** 是否加载中 */
    loading: {
      type: Boolean,
      value: false
    },
    /** 按钮文本 */
    text: {
      type: String,
      value: ''
    },
    /** 是否为块级按钮 */
    block: {
      type: Boolean,
      value: false
    },
    /** 自定义样式类 */
    customClass: {
      type: String,
      value: ''
    }
  },

  data: {
    // 组件内部状态
  },

  methods: {
    onTap() {
      if (this.data.disabled || this.data.loading) {
        return;
      }
      this.triggerEvent('tap', {
        type: this.data.type
      });
    },

    onTouchStart() {
      if (this.data.disabled || this.data.loading) {
        return;
      }
      this.triggerEvent('touchstart');
    },

    onTouchEnd() {
      if (this.data.disabled || this.data.loading) {
        return;
      }
      this.triggerEvent('touchend');
    }
  }
});