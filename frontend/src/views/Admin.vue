<template>
  <div class="admin">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>🔐 管理员后台</span>
        </div>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="用户管理" name="users">
          <div style="margin-bottom: 20px;">
            <el-button type="primary" @click="showCreateDialog = true">创建用户</el-button>
          </div>
          
          <el-table :data="users" v-loading="usersLoading" style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="username" label="用户名" width="150" />
            <el-table-column prop="email" label="邮箱" width="200" />
            <el-table-column prop="role" label="角色" width="100">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : ''">
                  {{ row.role === 'admin' ? '管理员' : '普通用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column prop="last_login" label="最后登录" width="180" />
            <el-table-column label="操作" width="300">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="editUser(row)">编辑</el-button>
                <el-button 
                  type="warning" 
                  size="small" 
                  link 
                  @click="resetPassword(row)"
                >
                  重置密码
                </el-button>
                <el-button 
                  :type="row.is_active ? 'danger' : 'success'" 
                  size="small" 
                  link 
                  @click="toggleUserStatus(row)"
                >
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        
        <el-tab-pane label="数据管理" name="data">
          <el-alert
            title="数据管理"
            type="info"
            :closable="false"
            style="margin-bottom: 20px;"
          >
            <template #default>
              <p>当前数据库统计信息：</p>
              <ul style="margin: 10px 0; padding-left: 20px;">
                <li>用户总数: {{ stats.total_users || 0 }}</li>
                <li>论文总数: {{ stats.total_papers || 0 }}</li>
                <li>运行记录: {{ stats.total_runs || 0 }}</li>
              </ul>
            </template>
          </el-alert>
          
          <el-card shadow="never">
            <template #header>
              <span>危险操作</span>
            </template>
            <el-alert
              title="警告"
              type="warning"
              :closable="false"
              style="margin-bottom: 20px;"
            >
              以下操作不可恢复，请谨慎使用！
            </el-alert>
            <el-space direction="vertical" style="width: 100%;">
              <el-button type="danger" @click="clearOldRuns">
                清理旧运行记录（保留最近10条）
              </el-button>
            </el-space>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 创建用户对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建用户" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="用户名" required>
          <el-input v-model="createForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="createForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" placeholder="请输入邮箱（可选）" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role" style="width: 100%;">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateUser" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
    
    <!-- 编辑用户对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%;">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateUser" :loading="updating">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 重置密码对话框 -->
    <el-dialog v-model="showResetDialog" title="重置密码" width="400px">
      <el-form :model="resetForm" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="resetForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="resetForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResetDialog = false">取消</el-button>
        <el-button type="primary" @click="handleResetPassword" :loading="resetting">重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const activeTab = ref('users')
const users = ref([])
const usersLoading = ref(false)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showResetDialog = ref(false)
const creating = ref(false)
const updating = ref(false)
const resetting = ref(false)

const createForm = ref({
  username: '',
  password: '',
  email: '',
  role: 'user'
})

const editForm = ref({
  id: null,
  username: '',
  email: '',
  role: 'user',
  is_active: true
})

const resetForm = ref({
  id: null,
  username: '',
  new_password: ''
})

const stats = ref({
  total_users: 0,
  total_papers: 0,
  total_runs: 0
})

const loadUsers = async () => {
  usersLoading.value = true
  try {
    const response = await api.adminListUsers()
    if (response.status === 'success') {
      users.value = response.data || []
      stats.value.total_users = users.value.length
    }
  } catch (error) {
    ElMessage.error('加载用户列表失败: ' + (error.message || '未知错误'))
  } finally {
    usersLoading.value = false
  }
}

const handleCreateUser = async () => {
  if (!createForm.value.username || !createForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  
  creating.value = true
  try {
    await api.adminCreateUser({
      username: createForm.value.username,
      password: createForm.value.password,
      email: createForm.value.email || undefined,
      role: createForm.value.role
    })
    ElMessage.success('用户创建成功')
    showCreateDialog.value = false
    createForm.value = { username: '', password: '', email: '', role: 'user' }
    loadUsers()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('创建用户失败: ' + errorMsg)
  } finally {
    creating.value = false
  }
}

const editUser = (user) => {
  editForm.value = {
    id: user.id,
    username: user.username,
    email: user.email || '',
    role: user.role,
    is_active: user.is_active
  }
  showEditDialog.value = true
}

const handleUpdateUser = async () => {
  updating.value = true
  try {
    await api.adminUpdateUser(editForm.value.id, {
      role: editForm.value.role,
      is_active: editForm.value.is_active
    })
    ElMessage.success('用户更新成功')
    showEditDialog.value = false
    loadUsers()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('更新用户失败: ' + errorMsg)
  } finally {
    updating.value = false
  }
}

const resetPassword = (user) => {
  resetForm.value = {
    id: user.id,
    username: user.username,
    new_password: ''
  }
  showResetDialog.value = true
}

const handleResetPassword = async () => {
  if (!resetForm.value.new_password) {
    ElMessage.warning('请输入新密码')
    return
  }
  
  resetting.value = true
  try {
    await api.adminResetPassword(resetForm.value.id, resetForm.value.new_password)
    ElMessage.success('密码重置成功')
    showResetDialog.value = false
    resetForm.value = { id: null, username: '', new_password: '' }
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '未知错误'
    ElMessage.error('重置密码失败: ' + errorMsg)
  } finally {
    resetting.value = false
  }
}

const toggleUserStatus = async (user) => {
  const action = user.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户 "${user.username}" 吗？`,
      `确认${action}`,
      {
        confirmButtonText: action,
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await api.adminUpdateUser(user.id, {
      is_active: !user.is_active
    })
    ElMessage.success(`用户已${action}`)
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      const errorMsg = error.response?.data?.detail || error.message || '未知错误'
      ElMessage.error(`${action}用户失败: ` + errorMsg)
    }
  }
}

const clearOldRuns = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清理旧运行记录吗？此操作不可恢复！',
      '确认清理',
      {
        confirmButtonText: '清理',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    ElMessage.info('清理功能待实现')
  } catch (error) {
    // 用户取消
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.admin {
  width: 100%;
}
</style>

