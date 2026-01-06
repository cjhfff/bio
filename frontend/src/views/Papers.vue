<template>
  <div class="papers">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>📄 论文管理</span>
          <el-space>
            <el-input
              v-model="searchQuery"
              placeholder="搜索论文标题或关键词"
              style="width: 300px"
              clearable
              @clear="loadPapers"
            >
              <template #append>
                <el-button @click="loadPapers" :icon="Search" />
              </template>
            </el-input>
          </el-space>
        </div>
      </template>
      
      <el-table :data="papers" v-loading="loading" style="width: 100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding: 20px;">
              <p><strong>摘要:</strong></p>
              <p>{{ row.abstract || '无摘要' }}</p>
              <p style="margin-top: 10px;"><strong>来源:</strong> {{ row.source }}</p>
              <p><strong>日期:</strong> {{ row.date }}</p>
              <p v-if="row.link"><strong>链接:</strong> <a :href="row.link" target="_blank">{{ row.link }}</a></p>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="300" />
        <el-table-column prop="score" label="评分" width="100" sortable />
        <el-table-column prop="source" label="来源" width="120" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row)">详情</el-button>
            <el-button v-if="isAdmin" type="danger" link @click="deletePaper(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadPapers"
        @current-change="loadPapers"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const papers = ref([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 获取当前用户信息
const currentUser = ref(null)
const isAdmin = computed(() => currentUser.value?.role === 'admin')

// 加载用户信息
const loadCurrentUser = async () => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      currentUser.value = JSON.parse(userStr)
    } else {
      // 尝试从 API 获取
      const response = await api.getCurrentUser()
      if (response.status === 'success' && response.user) {
        currentUser.value = response.user
        localStorage.setItem('user', JSON.stringify(response.user))
      }
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
  }
}

const loadPapers = async () => {
  loading.value = true
  try {
    // This endpoint needs to be implemented in the backend
    const response = await api.getPapers({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value
    })
    
    if (response.status === 'success') {
      papers.value = response.data.papers || []
      total.value = response.data.total || 0
    }
  } catch (error) {
    ElMessage.error('加载论文失败: ' + (error.message || '未知错误'))
    papers.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const viewDetail = (paper) => {
  // 显示论文详情对话框
  ElMessageBox.alert(
    `<div style="text-align: left;">
      <p><strong>标题:</strong> ${paper.title}</p>
      <p><strong>摘要:</strong> ${paper.abstract || '无摘要'}</p>
      <p><strong>来源:</strong> ${paper.source}</p>
      <p><strong>日期:</strong> ${paper.date}</p>
      <p><strong>评分:</strong> ${paper.score}</p>
      ${paper.link ? `<p><strong>链接:</strong> <a href="${paper.link}" target="_blank">${paper.link}</a></p>` : ''}
    </div>`,
    '论文详情',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '关闭'
    }
  )
}

const deletePaper = async (paper) => {
  // 权限检查
  if (!isAdmin.value) {
    ElMessage.warning('只有管理员可以删除论文')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除论文 "${paper.title.substring(0, 50)}..." 吗？`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    loading.value = true
    await api.deletePaper(paper.id)
    ElMessage.success('论文已删除')
    loadPapers()
  } catch (error) {
    if (error !== 'cancel') {
      const errorMsg = error.response?.data?.detail || error.message || '未知错误'
      ElMessage.error('删除失败: ' + errorMsg)
    }
  } finally {
    loading.value = false
  }
}

const generateSamplePapers = () => {
  return [
    {
      id: 1,
      title: 'Novel insights into nitrogen fixation mechanisms in legume-rhizobium symbiosis',
      abstract: 'This study reveals new molecular mechanisms underlying the nitrogen fixation process...',
      score: 95.5,
      source: 'bioRxiv',
      date: '2024-01-06',
      link: 'https://example.com/paper1'
    },
    {
      id: 2,
      title: 'Structural analysis of nitrogenase complex using cryo-EM',
      abstract: 'High-resolution cryo-EM structure of the nitrogenase complex provides insights...',
      score: 92.3,
      source: 'Nature',
      date: '2024-01-05',
      link: 'https://example.com/paper2'
    }
  ]
}

onMounted(() => {
  loadCurrentUser()
  loadPapers()
})
</script>

<style scoped>
.papers {
  width: 100%;
}
</style>
