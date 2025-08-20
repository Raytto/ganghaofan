/**
 * 基础输入框组件
 * 
 * @description 标准化的输入框组件，支持多种类型和验证
 * @version 2.0.0
 */
Component({
  properties: {
    /** 输入框类型 */
    type: {
      type: String,
      value: 'text' // text, number, password, textarea
    },
    /** 输入框值 */
    value: {
      type: String,
      value: ''
    },
    /** 占位符 */
    placeholder: {
      type: String,
      value: ''
    },
    /** 是否禁用 */
    disabled: {
      type: Boolean,
      value: false
    },
    /** 是否只读 */
    readonly: {
      type: Boolean,
      value: false
    },
    /** 最大长度 */
    maxlength: {
      type: Number,
      value: -1
    },
    /** 是否显示字符计数 */
    showCount: {
      type: Boolean,
      value: false
    },
    /** 标签文本 */
    label: {
      type: String,
      value: ''
    },
    /** 是否必填 */
    required: {
      type: Boolean,
      value: false
    },
    /** 错误信息 */
    error: {
      type: String,
      value: ''
    },
    /** 帮助文本 */
    helper: {
      type: String,
      value: ''
    },
    /** 自定义样式类 */
    customClass: {
      type: String,
      value: ''
    }
  },

  data: {
    focused: false,
    currentLength: 0
  },

  observers: {
    'value': function(newValue) {
      this.setData({
        currentLength: newValue ? newValue.length : 0
      });
    }
  },

  methods: {
    onInput(e: any) {
      const value = e.detail.value;
      this.setData({
        currentLength: value.length
      });
      this.triggerEvent('input', {
        value: value
      });
    },

    onFocus(e: any) {
      this.setData({
        focused: true
      });
      this.triggerEvent('focus', e.detail);
    },

    onBlur(e: any) {
      this.setData({
        focused: false
      });
      this.triggerEvent('blur', e.detail);
    },

    onConfirm(e: any) {
      this.triggerEvent('confirm', e.detail);
    },

    onKeyboardHeightChange(e: any) {
      this.triggerEvent('keyboardheightchange', e.detail);
    },

    // 清除输入内容
    onClear() {
      this.setData({
        currentLength: 0
      });
      this.triggerEvent('input', {
        value: ''
      });
      this.triggerEvent('clear');
    }
  }
});