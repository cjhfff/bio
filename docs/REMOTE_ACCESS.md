# 远程访问配置指南

本文档说明如何配置系统以支持远程访问和管理。

## 功能特性

系统现已支持：
- ✅ 远程访问Web界面
- ✅ 远程调整配置（推送设置、抓取参数等）
- ✅ 远程触发任务
- ✅ 定时任务配置和管理

## 快速开始

### 使用 Docker（推荐）

1. 启动服务：
```bash
cd docker
docker-compose up -d
```

2. 通过服务器IP访问：
```
前端界面: http://<your-server-ip>:3000
后端API: http://<your-server-ip>:8000
```

### 手动部署

#### 后端服务

后端已默认绑定到 `0.0.0.0:8000`，支持远程访问。

```bash
# 启动后端
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

#### 前端服务

前端开发服务器配置为绑定 `0.0.0.0:3000`：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

## 远程配置管理

### 通过 Web 界面

访问 Web 界面的"配置中心"，可以修改：
- 推送设置（PushPlus Token、邮箱）
- 抓取参数（窗口天数、Top K数量）
- 其他系统设置

修改后点击"保存"即可，部分配置需要重启服务生效。

### 通过 API

```bash
# 获取当前配置
curl http://<server-ip>:8000/api/config

# 更新配置
curl -X PUT http://<server-ip>:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "general": {
      "defaultWindowDays": 2,
      "topK": 15
    },
    "push": {
      "pushplusTokens": ["token1", "token2"],
      "email": "your@email.com"
    }
  }'
```

## 定时任务管理

### 通过 Web 界面

1. 访问"定时任务"页面
2. 配置任务参数：
   - 启用/禁用
   - Cron 表达式（如 `0 9 * * *` 表示每天9点）
   - 抓取窗口和Top K参数
3. 保存配置
4. 根据系统提示设置系统级定时任务

### 通过 API

```bash
# 获取当前定时任务配置
curl http://<server-ip>:8000/api/schedule

# 更新定时任务配置
curl -X PUT http://<server-ip>:8000/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "cron": "0 9 * * *",
    "window_days": 1,
    "top_k": 12,
    "description": "每天上午9点推送"
  }'

# 获取 Cron 表达式示例
curl http://<server-ip>:8000/api/schedule/cron-examples
```

### 设置系统级定时任务

配置定时任务后，需要在操作系统层面设置实际的定时触发：

#### Linux/Mac (使用 crontab)

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天9点触发）
0 9 * * * curl -X POST http://localhost:8000/api/run
```

#### Windows (使用任务计划程序)

1. 打开任务计划程序
2. 创建新任务
3. 设置触发器（如每天9:00）
4. 设置操作：
   - 程序：`powershell.exe`
   - 参数：`-Command "Invoke-RestMethod -Uri 'http://localhost:8000/api/run' -Method POST"`

#### Docker 环境

在宿主机的 crontab 中添加：

```bash
# 每天9点通过 Docker exec 触发
0 9 * * * docker exec bio-backend curl -X POST http://localhost:8000/api/run
```

或者在宿主机直接调用 API：

```bash
0 9 * * * curl -X POST http://localhost:8000/api/run
```

## 常见 Cron 表达式

| 表达式 | 说明 |
|--------|------|
| `0 9 * * *` | 每天上午9点 |
| `0 */6 * * *` | 每6小时 |
| `0 9,18 * * *` | 每天上午9点和下午6点 |
| `0 9 * * 1` | 每周一上午9点 |
| `0 9 1 * *` | 每月1日上午9点 |
| `*/30 * * * *` | 每30分钟 |

## 安全建议

对于生产环境，建议：

1. **使用反向代理（Nginx）**
   - 配置 HTTPS
   - 限制访问IP
   - 添加基本认证

2. **防火墙配置**
   - 只开放必要端口
   - 限制访问来源

3. **添加认证机制**
   - 建议在 FastAPI 中添加 JWT 认证
   - 或使用 OAuth2

示例 Nginx 配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 故障排查

### 无法远程访问

1. 检查服务是否绑定到 0.0.0.0：
```bash
netstat -tlnp | grep 8000
netstat -tlnp | grep 3000
```

2. 检查防火墙规则：
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 3000
sudo ufw allow 8000

# CentOS/RHEL
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=3000/tcp --permanent
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

3. 检查云服务器安全组：
   - 确保入站规则允许 3000 和 8000 端口

### 配置更新不生效

部分配置需要重启服务：

```bash
# Docker 环境
docker-compose restart

# 手动部署
# 重启后端和前端服务
```

## 技术支持

遇到问题请查看：
- API 文档：http://<server-ip>:8000/docs
- 系统日志：`data/logs/` 目录
- GitHub Issues
