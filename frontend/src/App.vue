<template>
  <el-config-provider :locale="zhCn">
    <div id="app">
      <el-container>
        <el-aside width="200px" class="sidebar">
          <div class="logo">
            <h2>📚 Bio System</h2>
          </div>
          <el-menu
            :default-active="activeMenu"
            router
            background-color="#001529"
            text-color="#fff"
            active-text-color="#1890ff"
          >
            <el-menu-item index="/">
              <el-icon><DataLine /></el-icon>
              <span>仪表盘</span>
            </el-menu-item>
            <el-menu-item index="/papers">
              <el-icon><Document /></el-icon>
              <span>论文管理</span>
            </el-menu-item>
            <el-menu-item index="/config">
              <el-icon><Setting /></el-icon>
              <span>配置中心</span>
            </el-menu-item>
            <el-menu-item index="/logs">
              <el-icon><List /></el-icon>
              <span>日志查看</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        
        <el-container>
          <el-header class="header">
            <h1>智能论文推送系统</h1>
          </el-header>
          
          <el-main class="main-content">
            <router-view />
          </el-main>
        </el-container>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  height: 100vh;
}

.el-container {
  height: 100vh;
}

.sidebar {
  background-color: #001529;
  overflow: auto;
}

.logo {
  padding: 20px;
  text-align: center;
  color: #fff;
}

.logo h2 {
  font-size: 18px;
  margin: 0;
}

.header {
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.header h1 {
  font-size: 20px;
  margin: 0;
}

.main-content {
  background-color: #f0f2f5;
  padding: 24px;
  overflow: auto;
}
</style>
