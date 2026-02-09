<template>
  <div class="papers">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
          <span>📄 论文管理</span>
          <el-space wrap>
            <el-input
              v-model="searchQuery"
              placeholder="搜索: 关键词 / &quot;精确短语&quot; / AND OR NOT / source:biorxiv"
              style="width: 400px"
              clearable
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            >
              <template #append>
                <el-button @click="handleSearch" :icon="Search" />
              </template>
            </el-input>
            <el-button :icon="Filter" @click="showFilters = !showFilters" :type="hasActiveFilters ? 'primary' : ''">
              筛选
            </el-button>
          </el-space>
        </div>
        <!-- 高级筛选面板 -->
        <div v-show="showFilters" style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #ebeef5;">
          <el-row :gutter="16" align="middle">
            <el-col :span="5">
              <el-select v-model="filterSource" placeholder="来源" clearable style="width: 100%;" @change="handleSearch">
                <el-option label="全部来源" value="" />
                <el-option label="bioRxiv" value="biorxiv" />
                <el-option label="PubMed" value="pubmed" />
                <el-option label="Semantic Scholar" value="semanticscholar" />
                <el-option label="Europe PMC" value="europepmc" />
                <el-option label="RSS (顶刊)" value="rss_topjournal" />
                <el-option label="GitHub" value="github" />
                <el-option label="EurekAlert" value="eurekalert" />
              </el-select>
            </el-col>
            <el-col :span="5">
              <el-input-number v-model="filterMinScore" :min="0" :max="500" placeholder="最低评分" controls-position="right" style="width: 100%;" @change="handleSearch" />
            </el-col>
            <el-col :span="5">
              <el-date-picker v-model="filterDateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 100%;" @change="handleSearch" />
            </el-col>
            <el-col :span="5">
              <el-select v-model="sortBy" style="width: 100%;" @change="handleSearch">
                <el-option label="按评分排序" value="score" />
                <el-option label="按日期排序" value="date" />
                <el-option label="按引用数排序" value="citation_count" />
                <el-option label="按入库时间排序" value="created_at" />
              </el-select>
            </el-col>
            <el-col :span="4">
              <el-radio-group v-model="sortOrder" @change="handleSearch">
                <el-radio-button value="desc">降序</el-radio-button>
                <el-radio-button value="asc">升序</el-radio-button>
              </el-radio-group>
            </el-col>
          </el-row>
          <div style="margin-top: 8px; color: #909399; font-size: 12px;">
            搜索语法: <code>"精确短语"</code> | <code>nitrogen AND enzyme</code> | <code>+nitrogen -cancer</code> | <code>source:biorxiv</code> | <code>doi:10.1234</code>
          </div>
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
              <p v-if="row.doi"><strong>DOI:</strong> {{ row.doi }}</p>
              <p v-if="row.link"><strong>链接:</strong> <a :href="row.link" target="_blank">{{ row.link }}</a></p>
              <p><strong>引用数:</strong> {{ row.citation_count }}</p>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="300" show-overflow-tooltip />
        <el-table-column prop="score" label="评分" width="100" sortable />
        <el-table-column prop="source" label="来源" width="140" />
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="citation_count" label="引用" width="80" />
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
import { Search, Filter } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const papers = ref([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 高级筛选
const showFilters = ref(false)
const filterSource = ref('')
const filterMinScore = ref(undefined)
const filterDateRange = ref(null)
const sortBy = ref('score')
const sortOrder = ref('desc')

const hasActiveFilters = computed(() => {
  return filterSource.value || filterMinScore.value || filterDateRange.value
})

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

const handleSearch = () => {
  currentPage.value = 1
  loadPapers()
}

const loadPapers = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
      source: filterSource.value || undefined,
      min_score: filterMinScore.value || undefined,
      sort_by: sortBy.value,
      sort_order: sortOrder.value
    }

    if (filterDateRange.value && filterDateRange.value.length === 2) {
      params.date_from = filterDateRange.value[0]
      params.date_to = filterDateRange.value[1]
    }

    const response = await api.getPapers(params)

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
      <p><strong>引用数:</strong> ${paper.citation_count || 0}</p>
      ${paper.doi ? `<p><strong>DOI:</strong> ${paper.doi}</p>` : ''}
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
