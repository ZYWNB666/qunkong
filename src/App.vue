<template>
  <div id="app">
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-left">
          <div class="logo-container">
            <img src="/logo.svg" alt="Qunkong" class="logo" />
            <span class="title">Qunkong</span>
          </div>
        </div>
        <div class="header-center">
          <el-input
            v-model="searchKeyword"
            placeholder="AIGC"
            class="search-input"
            size="small"
          >
            <template #suffix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <div class="header-right">
          <el-dropdown>
            <span class="user-info">
              <el-icon><User /></el-icon>
              admin@example.com
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人设置</el-dropdown-item>
                <el-dropdown-item>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container>
        <!-- 侧边栏 -->
        <el-aside width="240px" class="sidebar">
          <el-menu
            :default-active="$route.path"
            class="sidebar-menu"
            router
            background-color="#001529"
            text-color="rgba(255, 255, 255, 0.85)"
            active-text-color="#1890ff"
          >
            <!-- 业务概览 -->
            <el-sub-menu index="overview">
              <template #title>
                <el-icon><DataBoard /></el-icon>
                <span>业务概览</span>
              </template>
            </el-sub-menu>

            <!-- 快速执行 -->
            <el-sub-menu index="quick">
              <template #title>
                <span class="menu-group-title">快速执行</span>
              </template>
              <el-menu-item index="/script-execution">
                <el-icon><Document /></el-icon>
                <span>脚本执行</span>
              </el-menu-item>
              <el-menu-item index="/file-distribution">
                <el-icon><FolderOpened /></el-icon>
                <span>文件分发</span>
              </el-menu-item>
            </el-sub-menu>

            <!-- 任务编排 -->
            <el-sub-menu index="task">
              <template #title>
                <span class="menu-group-title">任务编排</span>
              </template>
              <el-menu-item index="/jobs">
                <el-icon><Operation /></el-icon>
                <span>作业</span>
              </el-menu-item>
              <el-menu-item index="/schedule">
                <el-icon><Timer /></el-icon>
                <span>定时</span>
              </el-menu-item>
              <el-menu-item index="/execution-history">
                <el-icon><Clock /></el-icon>
                <span>执行历史</span>
              </el-menu-item>
            </el-sub-menu>

            <!-- 节点管理 -->
            <el-sub-menu index="node">
              <template #title>
                <span class="menu-group-title">节点管理</span>
              </template>
              <el-menu-item index="/agent-management">
                <el-icon><Monitor /></el-icon>
                <span>Agent</span>
              </el-menu-item>
              <el-menu-item index="/cloud-region">
                <el-icon><CloudDownload /></el-icon>
                <span>云区域</span>
              </el-menu-item>
            </el-sub-menu>

            <!-- 资源 -->
            <el-sub-menu index="resource">
              <template #title>
                <span class="menu-group-title">资源</span>
              </template>
              <el-menu-item index="/scripts">
                <el-icon><Document /></el-icon>
                <span>脚本</span>
              </el-menu-item>
              <el-menu-item index="/notification">
                <el-icon><Bell /></el-icon>
                <span>通知群组</span>
              </el-menu-item>
            </el-sub-menu>
          </el-menu>
        </el-aside>

        <!-- 主内容区 -->
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'App',
  setup() {
    const searchKeyword = ref('')
    
    return {
      searchKeyword
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
}

.logo {
  height: 32px;
  margin-right: 12px;
}

.title {
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  max-width: 400px;
  margin: 0 40px;
}

.search-input {
  width: 200px;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
  color: #666;
  font-size: 14px;
}

.user-info:hover {
  background-color: #f5f5f5;
}

.user-info .el-icon {
  margin: 0 4px;
}

.sidebar {
  background: #001529;
  height: calc(100vh - 64px);
  overflow-y: auto;
}

.sidebar-menu {
  border: none;
  height: 100%;
}

.sidebar-menu .el-sub-menu__title {
  height: 48px;
  line-height: 48px;
  padding-left: 20px !important;
}

.sidebar-menu .el-menu-item {
  height: 40px;
  line-height: 40px;
  padding-left: 48px !important;
  margin: 0;
  border-radius: 0;
}

.sidebar-menu .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.08) !important;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #1890ff !important;
  color: #fff !important;
}

.menu-group-title {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
}

.main-content {
  background: #f0f2f5;
  padding: 0;
  height: calc(100vh - 64px);
  overflow-y: auto;
}

/* Element Plus 样式覆盖 */
.el-sub-menu .el-sub-menu__title:hover {
  background-color: rgba(255, 255, 255, 0.08) !important;
}

.el-sub-menu.is-active > .el-sub-menu__title {
  color: #1890ff !important;
}

.el-menu--collapse .el-sub-menu__title span {
  display: none;
}
</style>