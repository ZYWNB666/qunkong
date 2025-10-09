import * as monaco from 'monaco-editor'

// 配置Monaco Editor使用本地资源
self.MonacoEnvironment = {
  getWorkerUrl: function (moduleId, label) {
    // Monaco Editor 0.44.0使用统一的workerMain.js
    // 所有语言支持都整合在这个worker中
    return '/monaco-editor/vs/base/worker/workerMain.js'
  }
}

export { monaco }
