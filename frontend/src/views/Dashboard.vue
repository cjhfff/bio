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
          <div id="trend-chart" style="height: 300px; display: flex; align-items: center; justify-content: center; color: #999;">
            图表功能需要安装 ECharts
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>📊 数据源占比</span>
          </template>
          <div id="source-chart" style="height: 300px; display: flex; align-items: center; justify-content: center; color: #999;">
            图表功能需要安装 ECharts
          </div>
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
              <el-button type="primary" size="small" @click="triggerRun">
                <el-icon><VideoPlay /></el-icon>
                立即执行
              </el-button>
            </div>
          </template>
          
          <el-table :data="recentRuns" v-loading="loading">
            <el-table-column prop="run_id" label="运行ID" width="180" />
            <el-table-column prop="created_at" label="时间" width="180" />
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const stats = ref({
  todayPapers: 0,
  totalPapers: 0,
  successRate: 0,
  apiCalls: 0
})

const recentRuns = ref([])
const loading = ref(false)

const loadDashboardData = async () => {
  loading.value = true
  try {
    // Load recent runs
    const response = await api.getRuns(10)
    if (response.status === 'success') {
      recentRuns.value = response.data
      
      // Calculate stats from runs
      if (recentRuns.value.length > 0) {
        const today = new Date().toISOString().split('T')[0]
        const todayRuns = recentRuns.value.filter(r => 
          r.created_at && r.created_at.startsWith(today)
        )
        
        stats.value.todayPapers = todayRuns.reduce((sum, r) => sum + (r.total_papers || 0), 0)
        stats.value.totalPapers = recentRuns.value.reduce((sum, r) => sum + (r.total_papers || 0), 0)
        
        const completedRuns = recentRuns.value.filter(r => r.status === 'completed')
        stats.value.successRate = recentRuns.value.length > 0 
          ? Math.round(completedRuns.length / recentRuns.value.length * 100) 
          : 0
        
        stats.value.apiCalls = recentRuns.value.length
      }
    }
  } catch (error) {
    ElMessage.error('加载数据失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const triggerRun = async () => {
  try {
    loading.value = true
    await api.triggerRun()
    ElMessage.success('任务已启动，请稍后查看结果')
    setTimeout(loadDashboardData, 2000)
  } catch (error) {
    ElMessage.error('启动任务失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const viewDetails = (runId) => {
  // TODO: Implement details view
  ElMessage.info('详情功能开发中...')
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

onMounted(() => {
  loadDashboardData()
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
