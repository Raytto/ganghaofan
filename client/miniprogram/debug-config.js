// 调试配置文件 - 临时验证BASE_URL配置
const API_CONFIG = {
  BASE_URL: 'http://us.pangruitao.com:8000/api/v1',
  TIMEOUT: 10000,
  MAX_RETRIES: 3
}

console.log('=== 调试信息 ===')
console.log('当前API配置:', API_CONFIG)
console.log('BASE_URL:', API_CONFIG.BASE_URL)
console.log('=============')

// 导出给调试使用
module.exports = API_CONFIG