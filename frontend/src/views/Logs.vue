<template>
  <div class="logs">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>📜 日志查看器</span>
          <el-space>
            <el-select v-model="logLevel" placeholder="日志级别" style="width: 120px;">
              <el-option label="全部" value="" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="ERROR" value="ERROR" />
            </el-select>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索关键词"
              style="width: 200px"
              clearable
            />
            <el-button type="primary" @click="loadLogs">刷新</el-button>
            <el-button @click="clearLogs">清空</el-button>
          </el-space>
        </div>
      </template>
      
      <div class="log-container" v-loading="loading">
        <div
          v-for="(log, index) in filteredLogs"
          :key="index"
          :class="['log-entry', `log-${log.level.toLowerCase()}`]"
        >
          <span class="log-time">{{ log.time }}</span>
          <span class="log-level">{{ log.level }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        
        <div v-if="filteredLogs.length === 0" class="empty-logs">
          暂无日志数据
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const logs = ref([])
const loading = ref(false)
const logLevel = ref('')
const searchKeyword = ref('')

const filteredLogs = computed(() => {
  let result = logs.value
  
  if (logLevel.value) {
    result = result.filter(log => log.level === logLevel.value)
  }
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(log => 
      log.message.toLowerCase().includes(keyword)
    )
  }
  
  return result
})

const loadLogs = async () => {
  loading.value = true
  try {
    const response = await api.getLogs({
      level: logLevel.value,
      search: searchKeyword.value
    })
    
    if (response.status === 'success') {
      logs.value = response.data
    }
  } catch (error) {
    // Generate sample logs
    ElMessage.warning('日志API开发中，显示示例日志')
    logs.value = generateSampleLogs()
  } finally {
    loading.value = false
  }
}

const clearLogs = () => {
  logs.value = []
  ElMessage.success('日志已清空')
}

const generateSampleLogs = () => {
  const now = new Date()
  return [
    {
      time: now.toISOString().slice(0, 19).replace('T', ' '),
      level: 'INFO',
      message: '开始执行生物化学研究资讯抓取与推送'
    },
    {
      time: now.toISOString().slice(0, 19).replace('T', ' '),
      level: 'INFO',
      message: 'bioRxiv: 获取到 15 条结果'
    },
    {
      time: now.toISOString().slice(0, 19).replace('T', ' '),
      level: 'WARNING',
      message: 'Semantic Scholar 测试失败: API限流严重'
    },
    {
      time: now.toISOString().slice(0, 19).replace('T', ' '),
      level: 'INFO',
      message: '对当天所有论文进行评分（共25篇）...'
    },
    {
      time: now.toISOString().slice(0, 19).replace('T', ' '),
      level: 'ERROR',
      message: '论文处理失败: Connection timeout'
    }
  ]
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.logs {
  width: 100%;
}

.log-container {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  max-height: 600px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-entry {
  margin-bottom: 4px;
}

.log-time {
  color: #858585;
  margin-right: 12px;
}

.log-level {
  display: inline-block;
  width: 70px;
  font-weight: bold;
  margin-right: 12px;
}

.log-info .log-level {
  color: #4ec9b0;
}

.log-warning .log-level {
  color: #dcdcaa;
}

.log-error .log-level {
  color: #f48771;
}

.log-message {
  color: #d4d4d4;
}

.empty-logs {
  text-align: center;
  color: #858585;
  padding: 40px;
}
</style>
