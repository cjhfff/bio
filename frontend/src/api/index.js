import axios from 'axios'

const instance = axios.create({
  baseURL: '/api',
  timeout: 300000 // 增加超时时间到 5 分钟 (300秒)
})

// Request interceptor
instance.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
instance.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response && error.response.status === 401) {
        // Redirect to login if not already there
        // Assuming hash router is used, otherwise use window.location.pathname
        if (!window.location.hash.includes('login') && !window.location.pathname.includes('login')) {
             // Let the router handle this via interceptors or simple redirect
             // For now, we'll just clear token
             localStorage.removeItem('token')
        }
    }
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default {
    login(username, password) {
        // 使用 URLSearchParams 确保正确的 Content-Type
        const params = new URLSearchParams()
        params.append('username', username)
        params.append('password', password)
        return instance.post('/auth/login', params, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        })
            .then(data => {
                localStorage.setItem('token', data.access_token)
                if (data.user) {
                    localStorage.setItem('user', JSON.stringify(data.user))
                }
                return data
            })
    },

    logout() {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
    },

    register(username, password, email) {
        return instance.post('/auth/register', {
            username,
            password,
            email: email || null
        })
    },

    getCurrentUser() {
        return instance.get('/auth/me')
    },

  // Run management
  getRuns(limit = 10) {
    return instance.get('/runs', { params: { limit } })
  },
  
  getRunScores(runId) {
    return instance.get(`/runs/${runId}/scores`)
  },
  
  triggerRun(windowDays = null, topK = null) {
    return instance.post('/run', null, { 
      params: { window_days: windowDays, top_k: topK } 
    })
  },
  
  getRunStatus() {
    return instance.get('/run/status')
  },

  clearDatabase() {
    return instance.post('/config/clear-database')
  },
  
  testSources() {
    return instance.post('/test-sources')
  },
  
  // Papers management
  getPapers(params) {
    return instance.get('/papers', { params })
  },
  
  getPaper(id) {
    return instance.get(`/papers/${id}`)
  },
  
  deletePaper(id) {
    return instance.delete(`/papers/${id}`)
  },
  
  // Config management (to be implemented)
  getConfig() {
    return instance.get('/config')
  },
  
  updateConfig(config) {
    return instance.put('/config', config)
  },
  
  // Logs
  getLogs(params) {
    return instance.get('/logs', { params })
  },
  
  // Test push
  testPushPlus(token) {
    return instance.post('/config/test-push', { token })
  },
  
  // Reload config
  reloadConfig() {
    return instance.post('/config/reload')
  },
  
  // Admin user management
  adminListUsers() {
    return instance.get('/admin/users')
  },
  
  adminCreateUser(userData) {
    return instance.post('/admin/users', userData)
  },
  
  adminUpdateUser(userId, userData) {
    return instance.put(`/admin/users/${userId}`, userData)
  },
  
  adminResetPassword(userId, newPassword) {
    return instance.post(`/admin/users/${userId}/reset-password`, {
      new_password: newPassword
    })
  }
}
