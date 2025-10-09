import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import config from './config.js'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: config.server.host,
    port: config.server.port,
    proxy: {
      '/api': {
        target: `http://${config.api.host}:${config.api.port}`,
        changeOrigin: true
      }
    }
  },
  define: {
    // 定义全局常量，在前端代码中可以直接使用
    __WEBSOCKET_HOST__: JSON.stringify(config.websocket.host),
    __WEBSOCKET_PORT__: JSON.stringify(config.websocket.port),
    __API_HOST__: JSON.stringify(config.api.host),
    __API_PORT__: JSON.stringify(config.api.port)
  },
  // 使用环境变量前缀 VITE_
  envPrefix: 'VITE_'
})
