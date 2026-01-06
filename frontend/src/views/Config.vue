<template>
  <div class="config">
    <el-card>
      <template #header>
        <span>⚙️ 配置中心</span>
      </template>
      
      <el-tabs>
        <el-tab-pane label="关键词管理">
          <el-alert
            title="关键词配置"
            type="info"
            description="配置研究方向相关的关键词，用于论文筛选和评分"
            :closable="false"
            style="margin-bottom: 20px;"
          />
          
          <el-form label-width="120px">
            <el-form-item label="生物固氮">
              <el-tag
                v-for="tag in keywords.nitrogen"
                :key="tag"
                closable
                style="margin-right: 10px; margin-bottom: 10px;"
                @close="removeKeyword('nitrogen', tag)"
              >
                {{ tag }}
              </el-tag>
              <el-button size="small" @click="addKeyword('nitrogen')">+ 添加</el-button>
            </el-form-item>
            
            <el-form-item label="信号转导">
              <el-tag
                v-for="tag in keywords.signal"
                :key="tag"
                closable
                style="margin-right: 10px; margin-bottom: 10px;"
                @close="removeKeyword('signal', tag)"
              >
                {{ tag }}
              </el-tag>
              <el-button size="small" @click="addKeyword('signal')">+ 添加</el-button>
            </el-form-item>
            
            <el-form-item label="酶结构机制">
              <el-tag
                v-for="tag in keywords.enzyme"
                :key="tag"
                closable
                style="margin-right: 10px; margin-bottom: 10px;"
                @close="removeKeyword('enzyme', tag)"
              >
                {{ tag }}
              </el-tag>
              <el-button size="small" @click="addKeyword('enzyme')">+ 添加</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="评分规则">
          <el-form label-width="150px">
            <el-form-item label="关键词匹配权重">
              <el-slider v-model="scoring.keywordWeight" :max="100" />
              <span style="margin-left: 10px;">{{ scoring.keywordWeight }}%</span>
            </el-form-item>
            
            <el-form-item label="顶刊加分">
              <el-slider v-model="scoring.journalBonus" :max="100" />
              <span style="margin-left: 10px;">{{ scoring.journalBonus }}%</span>
            </el-form-item>
            
            <el-form-item label="引用数权重">
              <el-slider v-model="scoring.citationWeight" :max="100" />
              <span style="margin-left: 10px;">{{ scoring.citationWeight }}%</span>
            </el-form-item>
            
            <el-form-item label="新鲜度权重">
              <el-slider v-model="scoring.freshnessWeight" :max="100" />
              <span style="margin-left: 10px;">{{ scoring.freshnessWeight }}%</span>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="数据源配置">
          <el-table :data="dataSources">
            <el-table-column prop="name" label="数据源" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" />
              </template>
            </el-table-column>
            <el-table-column prop="windowDays" label="时间窗口(天)" width="150">
              <template #default="{ row }">
                <el-input-number v-model="row.windowDays" :min="1" :max="30" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="testSource(row)">
                  测试
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="推送配置">
          <el-form label-width="120px">
            <el-form-item label="PushPlus Token">
              <el-input v-model="push.pushplusToken" type="password" show-password />
              <el-button style="margin-top: 10px;" @click="testPushPlus">测试推送</el-button>
            </el-form-item>
            
            <el-form-item label="邮箱配置">
              <el-input v-model="push.email" placeholder="接收邮箱" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="定时任务">
          <el-alert
            title="定时任务配置"
            type="info"
            description="配置系统自动执行推送任务的时间。启用后，系统将在指定时间自动运行推送任务。"
            :closable="false"
            style="margin-bottom: 20px;"
          />
          
          <el-form label-width="150px">
            <el-form-item label="启用定时任务">
              <el-switch v-model="schedule.enabled" />
              <span style="margin-left: 10px; color: #909399;">
                {{ schedule.enabled ? '已启用' : '已禁用' }}
              </span>
            </el-form-item>
            
            <el-form-item label="执行时间" v-if="schedule.enabled">
              <el-time-picker
                v-model="scheduleTime"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 200px;"
              />
              <div style="margin-top: 10px; color: #909399; font-size: 12px;">
                <div v-if="schedule.nextRun">
                  下次执行时间: {{ formatNextRun(schedule.nextRun) }}
                </div>
                <div v-else>
                  定时任务将在每天指定时间自动执行
                </div>
              </div>
            </el-form-item>
            
            <el-form-item label="任务状态" v-if="schedule.enabled">
              <el-tag :type="schedule.status === 'running' ? 'success' : 'info'">
                {{ schedule.status === 'running' ? '运行中' : '已停止' }}
              </el-tag>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      
      <div style="margin-top: 20px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <el-popconfirm title="确定要清空所有数据库记录吗？此操作不可恢复！" @confirm="handleClearDatabase">
            <template #reference>
              <el-button type="danger" plain :loading="clearingDatabase">🗑️ 清空数据库</el-button>
            </template>
          </el-popconfirm>
        </div>
        <div>
          <el-button @click="loadConfig" :loading="configLoading">重新加载</el-button>
          <el-button type="warning" @click="reloadConfig" :loading="reloading">
            🔄 热重载配置
          </el-button>
          <el-button type="primary" @click="saveConfig" :loading="loading">保存配置</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const keywords = ref({
  nitrogen: [],
  signal: [],
  enzyme: []
})

const scoring = ref({
  keywordWeight: 80,
  journalBonus: 60,
  citationWeight: 70,
  freshnessWeight: 50
})

const dataSources = ref([
  { name: 'bioRxiv', enabled: true, windowDays: 7 },
  { name: 'PubMed', enabled: true, windowDays: 7 },
  { name: 'Europe PMC', enabled: true, windowDays: 1 },
  { name: 'GitHub', enabled: true, windowDays: 7 },
  { name: 'Semantic Scholar', enabled: false, windowDays: 7 }
])

const push = ref({
  pushplusToken: '',
  email: ''
})

const schedule = ref({
  enabled: false,
  time: '08:30',
  status: 'stopped',
  nextRun: null
})

const scheduleTime = ref('08:30')

const loading = ref(false)
const configLoading = ref(false)
const reloading = ref(false)
const clearingDatabase = ref(false)

const handleClearDatabase = async () => {
  clearingDatabase.value = true
  try {
    await api.clearDatabase()
    ElMessage.success('数据库已清空')
  } catch (error) {
    ElMessage.error('清空失败: ' + error.message)
  } finally {
    clearingDatabase.value = false
  }
}

const loadConfig = async () => {
  configLoading.value = true
  try {
    const response = await api.getConfig()
    if (response.status === 'success' && response.data) {
      const data = response.data
      
      // 更新关键词
      if (data.keywords) {
        keywords.value = {
          nitrogen: data.keywords.nitrogen || [],
          signal: data.keywords.signal || [],
          enzyme: data.keywords.enzyme || []
        }
      }
      
      // 更新评分规则
      if (data.scoring) {
        scoring.value = {
          keywordWeight: data.scoring.keywordWeight || 80,
          journalBonus: data.scoring.journalBonus || 60,
          citationWeight: data.scoring.citationWeight || 70,
          freshnessWeight: data.scoring.freshnessWeight || 50
        }
      }
      
      // 更新数据源
      if (data.dataSources) {
        dataSources.value = data.dataSources
      }
      
      // 更新推送配置
      if (data.push) {
        push.value = {
          pushplusToken: Array.isArray(data.push.pushplusTokens) 
            ? data.push.pushplusTokens.join(',') 
            : (data.push.pushplusTokens || ''),
          email: data.push.email || ''
        }
      }
      
      // 更新通用配置
      if (data.general) {
        // 可以在这里更新通用配置
      }
      
      // 更新定时任务配置
      if (data.schedule) {
        schedule.value = {
          enabled: data.schedule.enabled || false,
          time: data.schedule.time || '08:30',
          status: data.schedule.status || 'stopped',
          nextRun: data.schedule.nextRun || null
        }
        scheduleTime.value = schedule.value.time
      }
      
      ElMessage.success('配置加载成功')
    }
  } catch (error) {
    ElMessage.warning('配置加载失败: ' + (error.message || '未知错误'))
  } finally {
    configLoading.value = false
  }
}

const saveConfig = async () => {
  try {
    loading.value = true
    
    // 处理推送配置：如果只有一个 token，转换为数组格式
    const pushConfig = {
      pushplusTokens: push.value.pushplusToken 
        ? (push.value.pushplusToken.includes(',') 
          ? push.value.pushplusToken.split(',').map(t => t.trim())
          : [push.value.pushplusToken])
        : [],
      email: push.value.email
    }
    
    // 处理定时任务配置
    const scheduleConfig = {
      enabled: schedule.value.enabled,
      time: scheduleTime.value || schedule.value.time
    }
    
    const response = await api.updateConfig({
      keywords: keywords.value,
      scoring: scoring.value,
      dataSources: dataSources.value,
      push: pushConfig,
      schedule: scheduleConfig
    })
    
    if (response.status === 'success') {
      ElMessage.success(response.message || '配置保存成功')
      // 重新加载配置以确保同步
      await loadConfig()
    }
  } catch (error) {
    ElMessage.error('配置保存失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const reloadConfig = async () => {
  try {
    reloading.value = true
    const response = await api.reloadConfig()
    if (response.status === 'success') {
      ElMessage.success(response.message || '配置已重新加载')
    }
  } catch (error) {
    ElMessage.error('重新加载失败: ' + (error.message || '未知错误'))
  } finally {
    reloading.value = false
  }
}

const addKeyword = async (category) => {
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入关键词',
      `添加${category === 'nitrogen' ? '生物固氮' : category === 'signal' ? '信号转导' : '酶结构机制'}关键词`,
      {
        confirmButtonText: '添加',
        cancelButtonText: '取消',
        inputPattern: /.+/,
        inputErrorMessage: '关键词不能为空'
      }
    )
    
    if (value && value.trim()) {
      const keyword = value.trim()
      if (!keywords.value[category].includes(keyword)) {
        keywords.value[category].push(keyword)
        ElMessage.success('关键词已添加（需要保存配置）')
      } else {
        ElMessage.warning('关键词已存在')
      }
    }
  } catch (error) {
    // 用户取消
  }
}

const formatNextRun = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 监听定时任务时间变化
watch(scheduleTime, (newTime) => {
  if (newTime && schedule.value.enabled) {
    schedule.value.time = newTime
  }
})

const removeKeyword = (category, keyword) => {
  const index = keywords.value[category].indexOf(keyword)
  if (index > -1) {
    keywords.value[category].splice(index, 1)
    ElMessage.success('关键词已移除（需要保存配置）')
  }
}

const testSource = async (source) => {
  try {
    await api.testSources()
    ElMessage.success(`${source.name} 测试完成，请查看日志`)
  } catch (error) {
    ElMessage.error(`${source.name} 测试失败: ` + error.message)
  }
}

const testPushPlus = async () => {
  try {
    if (!push.value.pushplusToken) {
      ElMessage.warning('请先输入 PushPlus Token')
      return
    }
    
    await api.testPushPlus(push.value.pushplusToken)
    ElMessage.success('测试推送已发送，请检查是否收到')
  } catch (error) {
    ElMessage.error('测试推送失败: ' + error.message)
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.config {
  width: 100%;
}
</style>
