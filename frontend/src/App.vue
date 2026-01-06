<template>
  <el-config-provider :locale="zhCn">
    <div id="app">
      <!-- 登录页不显示侧边栏和顶栏 -->
      <template v-if="isLoginPage">
        <router-view />
      </template>
      
      <!-- 其他页面显示完整布局 -->
      <el-container v-else>
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
            <el-menu-item v-if="currentUser && currentUser.role === 'admin'" index="/admin">
              <el-icon><UserFilled /></el-icon>
              <span>管理员后台</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        
        <el-container>
          <el-header class="header">
            <h1>智能论文推送系统</h1>
            <div style="flex: 1"></div>
            <div class="user-info" v-if="currentUser">
              <el-icon style="margin-right: 5px; color: #1890ff"><User /></el-icon>
              <span class="username">{{ currentUser.username }}</span>
              <el-tag v-if="currentUser.role === 'admin'" type="danger" size="small" style="margin-left: 8px">
                管理员
              </el-tag>
            </div>
            <el-button v-if="isLoggedIn" type="danger" link @click="handleLogout" style="margin-left: 16px">
              <el-icon style="margin-right: 5px"><SwitchButton /></el-icon>
              退出登录
            </el-button>
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
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import api from './api'
import { SwitchButton, User, UserFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const activeMenu = computed(() => route.path)
const isLoginPage = computed(() => route.path === '/login')

const isLoggedIn = ref(false)
const currentUser = ref(null)

const checkLoginStatus = () => {
  isLoggedIn.value = !!localStorage.getItem('token')
  // 从localStorage读取用户信息
  const userStr = localStorage.getItem('user')
  if (userStr) {
    try {
      currentUser.value = JSON.parse(userStr)
    } catch (e) {
      console.error('解析用户信息失败:', e)
      currentUser.value = null
    }
  } else {
    currentUser.value = null
  }
}

// 获取当前用户信息
const fetchCurrentUser = async () => {
  if (!isLoggedIn.value) return
  
  try {
    const response = await api.getCurrentUser()
    if (response.status === 'success' && response.user) {
      currentUser.value = response.user
      localStorage.setItem('user', JSON.stringify(response.user))
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
    // 如果token失效，清除登录状态
    if (error.response?.status === 401) {
      api.logout()
      isLoggedIn.value = false
      currentUser.value = null
    }
  }
}

// 监听路由变化来更新登录状态
watch(() => route.path, () => {
  checkLoginStatus()
  if (isLoggedIn.value && !isLoginPage.value) {
    fetchCurrentUser()
  }
})

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要退出登录吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    api.logout()
    isLoggedIn.value = false
    currentUser.value = null
    router.push('/login')
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  checkLoginStatus()
  if (isLoggedIn.value && !isLoginPage.value) {
    fetchCurrentUser()
  }
})
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

.user-info {
  display: flex;
  align-items: center;
  margin-right: 16px;
}

.username {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.main-content {
  background-color: #f0f2f5;
  padding: 24px;
  overflow: auto;
}
</style>
