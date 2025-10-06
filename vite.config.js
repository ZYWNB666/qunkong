import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: `http://${process.env.VITE_API_HOST || 'localhost'}:${process.env.VITE_API_PORT || '5000'}`,
        changeOrigin: true
      }
    }
  },
  define: {
    // 定义全局常量，在前端代码中可以直接使用
    __WEBSOCKET_HOST__: JSON.stringify(process.env.VITE_WEBSOCKET_HOST || 'localhost'),
    __WEBSOCKET_PORT__: JSON.stringify(process.env.VITE_WEBSOCKET_PORT || '8765'),
    __API_HOST__: JSON.stringify(process.env.VITE_API_HOST || 'localhost'),
    __API_PORT__: JSON.stringify(process.env.VITE_API_PORT || '5000')
  },
  // 使用环境变量前缀 VITE_
  envPrefix: 'VITE_'
})
