# Windows 定时任务设置指南

## 方法一：使用 PowerShell 脚本（推荐）

### 步骤

1. **以管理员身份运行 PowerShell**
   - 右键点击 PowerShell
   - 选择"以管理员身份运行"

2. **切换到项目目录**
   ```powershell
   cd C:\Users\d\Desktop\worksapce\bio
   ```

3. **执行设置脚本**
   ```powershell
   .\setup_scheduled_task.ps1
   ```

4. **验证任务**
   ```powershell
   Get-ScheduledTask -TaskName "BioPaperPushDaily"
   ```

### 任务详情

- **任务名称**: `BioPaperPushDaily`
- **执行时间**: 每天早上 8:30
- **执行文件**: `run_daily.bat`
- **工作目录**: `C:\Users\d\Desktop\worksapce\bio`

---

## 方法二：手动设置（图形界面）

### 步骤

1. **打开任务计划程序**
   - 按 `Win + R`
   - 输入 `taskschd.msc`
   - 按回车

2. **创建基本任务**
   - 点击右侧"创建基本任务"
   - 名称: `BioPaperPushDaily`
   - 描述: `每天早上 8:30 自动运行生物化学论文推送任务`

3. **设置触发器**
   - 选择"每天"
   - 开始时间: `8:30:00`
   - 重复任务间隔: `1 天`

4. **设置操作**
   - 选择"启动程序"
   - 程序或脚本: `C:\Users\d\Desktop\worksapce\bio\run_daily.bat`
   - 起始于: `C:\Users\d\Desktop\worksapce\bio`

5. **完成设置**
   - 勾选"当单击完成时，打开此任务属性的对话框"
   - 点击"完成"

6. **高级设置（可选）**
   - 在"常规"选项卡中：
     - 勾选"不管用户是否登录都要运行"
     - 勾选"使用最高权限运行"
   - 在"条件"选项卡中：
     - 勾选"只有在以下网络连接可用时才启动"
   - 在"设置"选项卡中：
     - 勾选"允许按需运行任务"
     - 勾选"如果请求的任务正在运行，则停止现有实例"
     - 失败时重启任务：最多重启 3 次，间隔 1 分钟

---

## 验证和测试

### 立即测试任务

```powershell
# 立即运行任务
Start-ScheduledTask -TaskName "BioPaperPushDaily"

# 查看任务状态
Get-ScheduledTaskInfo -TaskName "BioPaperPushDaily"
```

### 查看任务历史

1. 打开任务计划程序
2. 找到任务 `BioPaperPushDaily`
3. 点击"历史记录"选项卡
4. 查看运行记录和错误信息

### 查看日志

任务执行的日志会保存在：
- `logs/paper_push_YYYY-MM-DD_HHMMSS_RUNID.log` - 每次运行的详细日志
- `logs/error.log` - 错误日志（如果有）

---

## 管理任务

### 查看任务

```powershell
Get-ScheduledTask -TaskName "BioPaperPushDaily"
```

### 删除任务

```powershell
Unregister-ScheduledTask -TaskName "BioPaperPushDaily" -Confirm:$false
```

### 修改任务

```powershell
# 查看任务详情
Get-ScheduledTask -TaskName "BioPaperPushDaily" | Get-ScheduledTaskInfo

# 修改触发器（例如改为 9:00）
$task = Get-ScheduledTask -TaskName "BioPaperPushDaily"
$trigger = New-ScheduledTaskTrigger -Daily -At "9:00AM"
Set-ScheduledTask -TaskName "BioPaperPushDaily" -Trigger $trigger
```

---

## 故障排除

### 任务不运行

1. **检查任务计划程序服务**
   ```powershell
   Get-Service Schedule
   ```
   如果服务未运行，启动它：
   ```powershell
   Start-Service Schedule
   ```

2. **检查任务状态**
   ```powershell
   Get-ScheduledTask -TaskName "BioPaperPushDaily" | Select-Object State
   ```
   如果状态是"禁用"，启用它：
   ```powershell
   Enable-ScheduledTask -TaskName "BioPaperPushDaily"
   ```

3. **检查任务历史**
   - 在任务计划程序中查看"历史记录"选项卡
   - 查看是否有错误信息

4. **检查批处理文件**
   - 手动运行 `run_daily.bat` 测试是否正常
   - 检查 Python 环境是否正确

### 任务运行但失败

1. **查看日志文件**
   - 检查 `logs/` 目录下的最新日志文件
   - 查看 `logs/error.log` 错误日志

2. **检查环境变量**
   - 确保 API 密钥等配置正确
   - 检查网络连接

3. **检查 Python 路径**
   - 确保任务计划程序能找到 Python
   - 可以在批处理文件中使用完整路径

---

## 注意事项

1. **权限问题**
   - 创建任务可能需要管理员权限
   - 任务运行时使用当前用户权限

2. **网络连接**
   - 任务需要网络连接才能抓取数据
   - 建议勾选"只有在以下网络连接可用时才启动"

3. **电脑休眠**
   - 如果电脑在 8:30 处于休眠状态，任务会在唤醒后运行
   - 可以设置"唤醒计算机运行此任务"

4. **日志管理**
   - 日志文件会不断增长，建议定期清理
   - 可以设置日志文件大小限制

---

## 快速命令参考

```powershell
# 创建任务
.\setup_scheduled_task.ps1

# 立即运行
Start-ScheduledTask -TaskName "BioPaperPushDaily"

# 查看状态
Get-ScheduledTaskInfo -TaskName "BioPaperPushDaily"

# 查看任务
Get-ScheduledTask -TaskName "BioPaperPushDaily"

# 删除任务
Unregister-ScheduledTask -TaskName "BioPaperPushDaily" -Confirm:$false

# 启用任务
Enable-ScheduledTask -TaskName "BioPaperPushDaily"

# 禁用任务
Disable-ScheduledTask -TaskName "BioPaperPushDaily"
```





