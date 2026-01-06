import axios from 'axios'

const instance = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Request interceptor
instance.interceptors.request.use(
  config => {
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
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default {
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
  
  testSources() {
    return instance.post('/test-sources')
  },
  
  // Papers management (to be implemented)
  getPapers(params) {
    return instance.get('/papers', { params })
  },
  
  getPaper(id) {
    return instance.get(`/papers/${id}`)
  },
  
  // Config management (to be implemented)
  getConfig() {
    return instance.get('/config')
  },
  
  updateConfig(config) {
    return instance.put('/config', config)
  },
  
  // Logs (to be implemented)
  getLogs(params) {
    return instance.get('/logs', { params })
  }
}
