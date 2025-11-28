// 统一配置文件 - 管理所有IP和端口
const config = {
  // 服务器配置
  server: {
    host: '0.0.0.0',
    port: 3000
  },
  
  // API服务配置
  api: {
    host: 'localhost',
    port: '5000'
  },
  
  // WebSocket服务配置
  websocket: {
    host: 'localhost',
    port: '8765'
  }
}

export default config
