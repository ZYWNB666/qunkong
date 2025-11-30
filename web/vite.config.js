import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import config from './config.js'

export default defineConfig({
  plugins: [react()],
  server: {
    host: config.server.host,
    port: config.server.port,
    proxy: {
      '/api': {
        target: `http://${config.api.host}:${config.api.port}`,
        changeOrigin: true
      },
      '/ws': {
        target: `ws://${config.websocket.host}:${config.websocket.port}`,
        changeOrigin: true,
        ws: true
      }
    }
  },
  define: {
    // 定义全局常量，在前端代码中可以直接使用
    __WEBSOCKET_HOST__: JSON.stringify(config.websocket.host),
    __WEBSOCKET_PORT__: JSON.stringify(config.websocket.port),
    __API_HOST__: JSON.stringify(config.api.host),
    __API_PORT__: JSON.stringify(config.api.port),
    // Monaco Editor 本地配置
    MONACO_EDITOR_BASE_URL: JSON.stringify('/monaco-editor')
  },
  // 使用环境变量前缀 VITE_
  envPrefix: 'VITE_',
  // Monaco Editor 优化配置
  optimizeDeps: {
    include: ['monaco-editor', '@monaco-editor/react']
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ['monaco-editor'],
          antd: ['antd', '@ant-design/icons']
        }
      }
    }
  },
  // 静态资源处理
  assetsInclude: ['**/*.wasm']
})
