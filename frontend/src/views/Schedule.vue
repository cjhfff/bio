<template>
  <div class="schedule">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>⏰ 定时任务管理</span>
          <el-button type="primary" @click="saveSchedule" :loading="saving">保存配置</el-button>
        </div>
      </template>

      <el-alert
        title="定时任务说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <p>配置后需要在操作系统层面设置实际的定时触发器（如 Linux crontab 或 Windows 任务计划程序）</p>
        <p>详细设置方法请参考下方的"系统集成指南"</p>
      </el-alert>

      <el-form :model="schedule" label-width="150px">
        <el-form-item label="启用定时任务">
          <el-switch v-model="schedule.enabled" />
        </el-form-item>

        <el-form-item label="执行时间 (Cron)">
          <el-select v-model="schedule.cron" placeholder="选择或输入 Cron 表达式" filterable allow-create style="width: 300px;">
            <el-option
              v-for="example in cronExamples"
              :key="example.expression"
              :label="`${example.expression} - ${example.description}`"
              :value="example.expression"
            />
          </el-select>
          <el-button link type="primary" @click="showCronHelp">查看示例</el-button>
        </el-form-item>

        <el-form-item label="抓取窗口（天）">
          <el-input-number v-model="schedule.window_days" :min="1" :max="30" />
          <span style="margin-left: 10px; color: #909399;">抓取最近几天的论文</span>
        </el-form-item>

        <el-form-item label="推送Top K">
          <el-input-number v-model="schedule.top_k" :min="1" :max="100" />
          <span style="margin-left: 10px; color: #909399;">推送评分最高的前K篇论文</span>
        </el-form-item>

        <el-form-item label="任务描述">
          <el-input v-model="schedule.description" placeholder="例如：每天上午9点推送" style="width: 400px;" />
        </el-form-item>
      </el-form>

      <el-divider />

      <h3>🔧 系统集成指南</h3>
      
      <el-tabs v-model="activeTab" style="margin-top: 20px;">
        <el-tab-pane label="Linux / Mac" name="linux">
          <div class="integration-guide">
            <h4>使用 Crontab 设置定时任务</h4>
            <el-steps direction="vertical" :active="3">
              <el-step title="编辑 crontab" description="在终端执行: crontab -e" />
              <el-step title="添加定时任务" description="复制下方命令到 crontab 文件" />
              <el-step title="保存并退出" description="任务将自动生效" />
            </el-steps>
            
            <div class="code-block" style="margin-top: 20px;">
              <div class="code-header">
                <span>Crontab 命令</span>
                <el-button size="small" @click="copyToClipboard(cronHints.linux)">复制</el-button>
              </div>
              <pre><code>{{ cronHints.linux || '保存配置后生成命令' }}</code></pre>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="Windows" name="windows">
          <div class="integration-guide">
            <h4>使用任务计划程序设置定时任务</h4>
            <el-steps direction="vertical" :active="5">
              <el-step title="打开任务计划程序" description="Win + R, 输入 taskschd.msc" />
              <el-step title="创建基本任务" description="右侧面板选择"创建基本任务"" />
              <el-step title="设置触发器" description="根据 Cron 表达式设置执行时间" />
              <el-step title="设置操作" description="选择"启动程序", 复制下方 PowerShell 命令" />
              <el-step title="完成" description="确认并保存任务" />
            </el-steps>
            
            <div class="code-block" style="margin-top: 20px;">
              <div class="code-header">
                <span>PowerShell 脚本</span>
                <el-button size="small" @click="copyToClipboard(cronHints.windows)">复制</el-button>
              </div>
              <pre><code>{{ cronHints.windows || '保存配置后生成命令' }}</code></pre>
            </div>

            <el-alert
              title="任务计划程序设置"
              type="warning"
              :closable="false"
              style="margin-top: 15px;"
            >
              程序/脚本: powershell.exe<br>
              添加参数: -Command "复制上方PowerShell命令"
            </el-alert>
          </div>
        </el-tab-pane>

        <el-tab-pane label="Docker" name="docker">
          <div class="integration-guide">
            <h4>Docker 环境定时任务设置</h4>
            <p>在宿主机上设置 crontab，通过 docker exec 或 API 调用触发任务</p>
            
            <div class="code-block" style="margin-top: 20px;">
              <div class="code-header">
                <span>宿主机 Crontab 命令</span>
                <el-button size="small" @click="copyToClipboard(cronHints.docker)">复制</el-button>
              </div>
              <pre><code>{{ cronHints.docker || '保存配置后生成命令' }}</code></pre>
            </div>

            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-top: 15px;"
            >
              确保容器名称正确（默认为 bio-backend），可通过 docker ps 查看
            </el-alert>
          </div>
        </el-tab-pane>
      </el-tabs>

      <el-divider />

      <div class="quick-test">
        <h3>⚡ 快速测试</h3>
        <p style="color: #909399; margin: 10px 0;">测试推送功能是否正常工作</p>
        <el-button type="success" @click="testRun" :loading="testing">
          <el-icon><VideoPlay /></el-icon>
          立即执行一次推送任务
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const schedule = ref({
  enabled: false,
  cron: '0 9 * * *',
  window_days: 1,
  top_k: 12,
  description: '每天上午9点推送'
})

const cronExamples = ref([])
const cronHints = ref({
  linux: '',
  windows: '',
  docker: ''
})

const activeTab = ref('linux')
const saving = ref(false)
const testing = ref(false)

onMounted(async () => {
  await loadSchedule()
  await loadCronExamples()
})

const loadSchedule = async () => {
  try {
    const response = await api.getSchedule()
    if (response.status === 'success') {
      schedule.value = response.data
    }
  } catch (error) {
    console.error('Failed to load schedule:', error)
    ElMessage.error('加载定时任务配置失败')
  }
}

const loadCronExamples = async () => {
  try {
    const response = await api.getCronExamples()
    if (response.status === 'success') {
      cronExamples.value = response.data
    }
  } catch (error) {
    console.error('Failed to load cron examples:', error)
  }
}

const saveSchedule = async () => {
  saving.value = true
  try {
    const response = await api.updateSchedule(schedule.value)
    if (response.status === 'success') {
      ElMessage.success('配置保存成功！')
      
      // Update cron hints
      if (response.cron_hint) {
        cronHints.value = response.cron_hint
      }
      
      // Show next steps
      if (schedule.value.enabled) {
        ElMessageBox.alert(
          '定时任务配置已保存。请按照下方"系统集成指南"设置实际的定时触发器。',
          '下一步操作',
          {
            confirmButtonText: '我知道了',
            type: 'success'
          }
        )
      }
    }
  } catch (error) {
    console.error('Failed to save schedule:', error)
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

const testRun = async () => {
  testing.value = true
  try {
    await api.triggerRun(schedule.value.window_days, schedule.value.top_k)
    ElMessage.success('任务已启动，请查看仪表盘了解执行情况')
  } catch (error) {
    console.error('Failed to trigger run:', error)
    ElMessage.error('启动任务失败')
  } finally {
    testing.value = false
  }
}

const showCronHelp = () => {
  ElMessageBox.alert(
    `Cron 表达式格式: 分 时 日 月 周
    
常用示例：
• 0 9 * * *      每天上午9点
• 0 */6 * * *    每6小时
• 0 9,18 * * *   每天上午9点和下午6点
• 0 9 * * 1      每周一上午9点
• 0 9 1 * *      每月1日上午9点
• */30 * * * *   每30分钟`,
    'Cron 表达式说明',
    {
      confirmButtonText: '知道了'
    }
  )
}

const copyToClipboard = (text) => {
  if (!text) {
    ElMessage.warning('请先保存配置以生成命令')
    return
  }
  
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动复制')
  })
}
</script>

<style scoped>
.schedule {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.integration-guide {
  padding: 20px;
}

.integration-guide h4 {
  margin-bottom: 15px;
  color: #303133;
}

.code-block {
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #e4e7ed;
  border-bottom: 1px solid #dcdfe6;
}

.code-block pre {
  margin: 0;
  padding: 15px;
  overflow-x: auto;
}

.code-block code {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
}

.quick-test {
  margin-top: 20px;
}

.quick-test h3 {
  margin-bottom: 10px;
}
</style>
