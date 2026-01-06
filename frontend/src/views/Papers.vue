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
            <el-button type="danger" link>删除</el-button>
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
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const papers = ref([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

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
    // For now, show sample data
    ElMessage.warning('论文管理API开发中，显示示例数据')
    papers.value = generateSamplePapers()
    total.value = papers.value.length
  } finally {
    loading.value = false
  }
}

const viewDetail = (paper) => {
  ElMessage.info('详情功能开发中...')
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
  loadPapers()
})
</script>

<style scoped>
.papers {
  width: 100%;
}
</style>
