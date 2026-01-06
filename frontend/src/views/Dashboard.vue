<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- Statistics Cards -->
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #1890ff">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.todayPapers }}</div>
              <div class="stat-label">今日推送</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #52c41a">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalPapers }}</div>
              <div class="stat-label">总论文数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #faad14">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.successRate }}%</div>
              <div class="stat-label">成功率</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #722ed1">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.apiCalls }}</div>
              <div class="stat-label">API调用</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Section -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>📈 7天推送趋势</span>
          </template>
          <div id="trend-chart" style="height: 300px;"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>📊 数据源占比</span>
          </template>
          <div id="source-chart" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent Runs -->
    <el-row style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>🕐 最近运行记录</span>
              <el-button 
                type="primary" 
                size="small" 
                @click="triggerRun"
                :loading="running"
                :disabled="running"
              >
                <el-icon v-if="!running"><VideoPlay /></el-icon>
                {{ running ? '任务运行中...' : '立即执行' }}
              </el-button>
            </div>
          </template>
          
          <el-table :data="recentRuns" v-loading="loading">
            <el-table-column prop="run_id" label="运行ID" width="180" />
            <el-table-column prop="start_time" label="开始时间" width="180">
              <template #default="{ row }">
                {{ row.start_time ? new Date(row.start_time).toLocaleString('zh-CN') : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_papers" label="论文数" width="100" />
            <el-table-column prop="window_days" label="窗口(天)" width="100" />
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewDetails(row.run_id)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import api from '../api'

const stats = ref({
  todayPapers: 0,
  totalPapers: 0,
  successRate: 0,
  apiCalls: 0
})

const recentRuns = ref([])
const running = ref(false)  // 任务是否正在运行
const loading = ref(false)

let trendChart = null
let sourceChart = null

const loadDashboardData = async () => {
  loading.value = true
  try {
    // Load recent runs
    const response = await api.getRuns(30) // 获取更多数据用于图表
    if (response.status === 'success' && response.data) {
      recentRuns.value = response.data.slice(0, 10) // 表格只显示最近10条
      
      // Calculate stats from runs
      if (response.data.length > 0) {
        const today = new Date().toISOString().split('T')[0]
        const todayRuns = response.data.filter(r => 
          r.start_time && r.start_time.startsWith(today)
        )
        
        stats.value.todayPapers = todayRuns.reduce((sum, r) => sum + (r.total_papers || 0), 0)
        stats.value.totalPapers = response.data.reduce((sum, r) => sum + (r.total_papers || 0), 0)
        
        const completedRuns = response.data.filter(r => r.status === 'completed')
        stats.value.successRate = response.data.length > 0 
          ? Math.round(completedRuns.length / response.data.length * 100) 
          : 0
        
        stats.value.apiCalls = response.data.length
        
        // 更新图表
        await nextTick()
        updateCharts(response.data)
      }
    }
  } catch (error) {
    ElMessage.error('加载数据失败: ' + (error.message || '未知错误'))
    console.error('Dashboard加载错误:', error)
  } finally {
    loading.value = false
  }
}

const updateCharts = (runs) => {
  // 7天趋势图
  const last7Days = []
  const papersCount = []
  for (let i = 6; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    const dateStr = date.toISOString().split('T')[0]
    last7Days.push(dateStr.slice(5)) // MM-DD格式
    
    const dayRuns = runs.filter(r => r.start_time && r.start_time.startsWith(dateStr))
    papersCount.push(dayRuns.reduce((sum, r) => sum + (r.total_papers || 0), 0))
  }
  
  if (!trendChart) {
    trendChart = echarts.init(document.getElementById('trend-chart'))
  }
  trendChart.setOption({
    title: { text: '7天推送趋势', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: last7Days },
    yAxis: { type: 'value', name: '论文数' },
    series: [{
      data: papersCount,
      type: 'line',
      smooth: true,
      areaStyle: {}
    }]
  })
  
  // 数据源占比图
  const sourceCount = {}
  runs.forEach(r => {
    // 从运行历史中无法直接获取数据源分布，使用示例数据
  })
  
  // 使用示例数据源分布（实际应该从数据库统计）
  const sourceData = [
    { value: 35, name: 'bioRxiv' },
    { value: 25, name: 'PubMed' },
    { value: 20, name: 'Europe PMC' },
    { value: 15, name: 'RSS' },
    { value: 5, name: 'GitHub' }
  ]
  
  if (!sourceChart) {
    sourceChart = echarts.init(document.getElementById('source-chart'))
  }
  sourceChart.setOption({
    title: { text: '数据源占比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: '60%',
      data: sourceData,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  })
}

// 检查任务运行状态
const checkRunStatus = async () => {
  try {
    const response = await api.getRunStatus()
    if (response.status === 'success') {
      running.value = response.running || false
      return response.running
    }
    return false
  } catch (error) {
    return false
  }
}

const triggerRun = async () => {
  // 先检查是否有任务正在运行
  const isRunning = await checkRunStatus()
  if (isRunning) {
    ElMessage.warning('已有任务正在运行中，请等待当前任务完成后再试')
    running.value = true
    return
  }
  
  // 防止重复点击
  if (running.value) {
    ElMessage.warning('任务正在运行中，请勿重复点击')
    return
  }
  
  try {
    running.value = true
    loading.value = true
    const response = await api.triggerRun()
    
    // 检查返回结果
    if (response.status === 'error' && response.running) {
      ElMessage.warning(response.message || '已有任务正在运行中')
      running.value = true
      loading.value = false
      return
    }
    
    ElMessage.success(response.message || '任务已启动，正在后台执行')
    
    // 定期检查任务状态，直到任务完成
    const checkInterval = setInterval(async () => {
      try {
        const isStillRunning = await checkRunStatus()
        if (!isStillRunning) {
          clearInterval(checkInterval)
          running.value = false
          loading.value = false
          await loadDashboardData()  // 刷新数据
          ElMessage.success('任务执行完成')
        }
      } catch (error) {
        // 检查失败不影响主流程
      }
    }, 5000) // 每5秒检查一次
    
    // 设置最大等待时间（30分钟）
    setTimeout(() => {
      clearInterval(checkInterval)
      if (running.value) {
        running.value = false
        loading.value = false
        ElMessage.warning('任务执行时间较长，请稍后手动刷新查看结果')
      }
    }, 30 * 60 * 1000)
    
  } catch (error) {
    ElMessage.error('启动任务失败: ' + (error.message || '未知错误'))
    running.value = false
    loading.value = false
  }
}

const viewDetails = async (runId) => {
  try {
    loading.value = true
    const scoresResponse = await api.getRunScores(runId)
    if (scoresResponse.status === 'success') {
      const scores = scoresResponse.data || []
      const scoresText = scores.map((s, idx) => 
        `${idx + 1}. ${s.title} (${s.source}) - 评分: ${s.score}`
      ).join('\n')
      
      ElMessageBox.alert(
        `<div style="text-align: left; max-height: 400px; overflow-y: auto;">
          <p><strong>运行ID:</strong> ${runId}</p>
          <p><strong>论文数量:</strong> ${scores.length}</p>
          <hr style="margin: 10px 0;">
          <pre style="white-space: pre-wrap; font-size: 12px;">${scoresText || '暂无评分数据'}</pre>
        </div>`,
        '运行详情',
        {
          dangerouslyUseHTMLString: true,
          confirmButtonText: '关闭'
        }
      )
    }
  } catch (error) {
    ElMessage.error('加载详情失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const getStatusType = (status) => {
  const typeMap = {
    'completed': 'success',
    'running': 'warning',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'completed': '完成',
    'running': '运行中',
    'failed': '失败'
  }
  return textMap[status] || status
}

onMounted(async () => {
  // 先检查任务状态
  await checkRunStatus()
  // 然后加载数据
  loadDashboardData()
  
  // 如果任务正在运行，定期检查状态
  if (running.value) {
    const checkInterval = setInterval(async () => {
      const isStillRunning = await checkRunStatus()
      if (!isStillRunning) {
        clearInterval(checkInterval)
        await loadDashboardData()  // 任务完成，刷新数据
        ElMessage.success('任务执行完成')
      }
    }, 5000) // 每5秒检查一次
    
    // 30分钟后停止检查
    setTimeout(() => {
      clearInterval(checkInterval)
    }, 30 * 60 * 1000)
  }
  
  // 窗口大小改变时重新调整图表
  window.addEventListener('resize', () => {
    if (trendChart) trendChart.resize()
    if (sourceChart) sourceChart.resize()
  })
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
  margin-right: 16px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #999;
}
</style>
