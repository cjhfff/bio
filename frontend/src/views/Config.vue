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
      </el-tabs>
      
      <div style="margin-top: 20px; text-align: right;">
        <el-button @click="loadConfig">重置</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const keywords = ref({
  nitrogen: ['nitrogen fixation', 'nitrogenase', 'rhizobia', 'nodulation'],
  signal: ['signal transduction', 'receptor kinase', 'ligand binding'],
  enzyme: ['enzyme structure', 'catalytic mechanism', 'active site', 'cryo-EM']
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

const loadConfig = async () => {
  try {
    const response = await api.getConfig()
    if (response.status === 'success') {
      // Update config from API
      ElMessage.success('配置加载成功')
    }
  } catch (error) {
    ElMessage.warning('配置API开发中，显示默认配置')
  }
}

const saveConfig = async () => {
  try {
    await api.updateConfig({
      keywords: keywords.value,
      scoring: scoring.value,
      dataSources: dataSources.value,
      push: push.value
    })
    ElMessage.success('配置保存成功')
  } catch (error) {
    ElMessage.error('配置保存失败: ' + error.message)
  }
}

const addKeyword = (category) => {
  ElMessage.info('添加关键词功能开发中...')
}

const testSource = async (source) => {
  try {
    await api.testSources()
    ElMessage.success(`${source.name} 测试完成，请查看日志`)
  } catch (error) {
    ElMessage.error(`${source.name} 测试失败: ` + error.message)
  }
}

const testPushPlus = () => {
  ElMessage.info('测试推送功能开发中...')
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
