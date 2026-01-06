import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/papers',
    name: 'Papers',
    component: () => import('../views/Papers.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/config',
    name: 'Config',
    component: () => import('../views/Config.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/logs',
    name: 'Logs',
    component: () => import('../views/Logs.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/Admin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const requiresAuth = to.meta.requiresAuth !== false // 默认需要认证
  const requiresAdmin = to.meta.requiresAdmin === true // 需要管理员权限
  
  if (requiresAuth && !token) {
    // 需要认证但未登录，跳转到登录页
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.path === '/login' && token) {
    // 已登录但访问登录页，跳转到首页
    next('/')
  } else if (requiresAdmin && token) {
    // 需要管理员权限，检查用户角色
    try {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        const user = JSON.parse(userStr)
        if (user.role === 'admin') {
          next()
        } else {
          // 非管理员，跳转到首页并提示
          next({ path: '/', query: { error: 'no_permission' } })
        }
      } else {
        // 尝试从 API 获取用户信息
        // 这里简化处理，直接跳转
        next({ path: '/', query: { error: 'no_permission' } })
      }
    } catch (error) {
      next({ path: '/', query: { error: 'no_permission' } })
    }
  } else {
    next()
  }
})

export default router
