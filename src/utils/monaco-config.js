import * as monaco from 'monaco-editor'

// 配置Monaco Editor使用本地资源
self.MonacoEnvironment = {
  getWorkerUrl: function (moduleId, label) {
    // Monaco Editor 0.44.0使用统一的workerMain.js
    // 所有语言支持都整合在这个worker中
    return '/monaco-editor/vs/base/worker/workerMain.js'
  },
  // 配置本地化资源路径
  globalAPI: true,
  // 设置基础路径以解决语言文件加载问题
  baseUrl: '/monaco-editor/vs'
}

// 设置Monaco Editor的基础路径
if (typeof window !== 'undefined') {
  window.MonacoEnvironment = self.MonacoEnvironment
  // 设置require.js的配置路径（如果需要）
  if (typeof window.require !== 'undefined' && window.require.config) {
    window.require.config({ 
      paths: { 
        'vs': '/monaco-editor/vs' 
      } 
    })
  }
}

export { monaco }
