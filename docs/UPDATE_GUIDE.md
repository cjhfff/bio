# 代码更新部署指南

本指南详细说明如何安全地更新运行在服务器上的代码，包括更新前的准备工作、更新步骤、回滚方案和常见问题处理。

## 📋 更新前检查清单

### 1. 确认当前状态
```bash
# 连接到服务器
ssh root@192.3.28.35

# 检查当前运行状态
ps aux | grep python  # 查看运行的Python进程
systemctl status cron  # 检查定时任务服务

# 查看当前代码版本
cd /root/bio_monitor  # 或你的项目目录
git log -1  # 查看最新提交
git status  # 查看是否有未提交的更改
```

### 2. 备份重要数据
```bash
# 创建备份目录
mkdir -p /root/backups/$(date +%Y%m%d)

# 备份数据库
cp -r data/ /root/backups/$(date +%Y%m%d)/data_backup
# 或者如果使用SQLite
cp data/database/paper_push.db /root/backups/$(date +%Y%m%d)/paper_push.db.backup

# 备份配置文件
cp .env /root/backups/$(date +%Y%m%d)/.env.backup

# 备份整个项目（可选）
cd /root
tar -czf /root/backups/$(date +%Y%m%d)/bio_full_backup.tar.gz bio_monitor/
```

### 3. 检查依赖更新
```bash
# 查看requirements.txt的变更
git diff origin/main requirements.txt

# 如果有新依赖，提前准备安装命令
```

## 🔄 更新步骤

### 方法一：标准更新流程（推荐）

#### 1. 停止运行中的服务
```bash
# 如果使用Docker
cd /root/bio_monitor/docker
docker-compose down

# 如果直接运行Python
# 找到并停止运行的进程
ps aux | grep python
kill <PID>  # 替换为实际的进程ID

# 暂时禁用定时任务
crontab -e
# 在相关行前添加 # 注释掉，保存退出
```

#### 2. 拉取最新代码
```bash
cd /root/bio_monitor

# 保存本地修改（如果有）
git stash

# 拉取最新代码
git pull origin main

# 或者拉取特定分支
git fetch origin
git checkout <branch-name>
git pull origin <branch-name>

# 如果有本地修改需要恢复
git stash pop
```

#### 3. 更新依赖
```bash
# Python后端依赖
pip install -r requirements.txt --upgrade

# 前端依赖（如果有前端更新）
cd frontend
npm install
npm run build
cd ..
```

#### 4. 数据库迁移（如有需要）
```bash
# 如果有数据库结构变更，运行迁移脚本
python scripts/migrate_database.py

# 或使用提供的迁移工具
python -m backend migrate
```

#### 5. 验证配置
```bash
# 检查.env文件是否有新增配置项
diff .env.example .env

# 如果有新配置项，添加到.env文件
vim .env
```

#### 6. 测试运行
```bash
# 手动测试运行
python -m backend test-sources

# 或运行完整测试
python -m backend run --window-days 1 --top-k 5
```

#### 7. 重启服务
```bash
# 如果使用Docker
cd docker
docker-compose up -d

# 如果使用API服务
nohup python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 > /root/bio_monitor/logs/api.log 2>&1 &

# 重新启用定时任务
crontab -e
# 移除注释，保存退出
```

#### 8. 验证更新
```bash
# 检查服务状态
ps aux | grep python

# 如果使用Docker
docker-compose ps

# 查看日志
tail -f logs/api.log  # API日志
tail -f logs/cron.log  # 定时任务日志

# 测试API接口（如果有Web界面）
curl http://localhost:8000/api/health  # 健康检查
```

### 方法二：零停机更新（适用于生产环境）

#### 使用Docker的蓝绿部署
```bash
# 1. 构建新镜像
cd /root/bio_monitor
git pull origin main
cd docker
docker-compose build

# 2. 启动新容器（不停止旧容器）
docker-compose up -d --no-deps --scale backend=2 backend

# 3. 测试新容器
docker ps  # 查看所有容器
docker logs <new-container-id>  # 检查新容器日志

# 4. 如果新容器正常，停止旧容器
docker-compose up -d --no-deps --scale backend=1 backend
```

#### 使用tmux保持服务运行
```bash
# 1. 在新tmux会话中启动更新后的服务
tmux new -s bio_new
cd /root/bio_monitor
git pull origin main
pip install -r requirements.txt --upgrade
python -m backend run

# 2. 测试新服务
# Ctrl+B 然后按 D 分离会话

# 3. 停止旧服务
tmux attach -t bio_old
# Ctrl+C 停止
# exit 或 Ctrl+D 退出

# 4. 将新会话重命名
tmux rename-session -t bio_new bio
```

## ⚠️ 回滚方案

如果更新后出现问题，可以快速回滚：

### 1. 代码回滚
```bash
cd /root/bio_monitor

# 回滚到上一个提交
git reset --hard HEAD^

# 或回滚到特定提交
git reset --hard <commit-hash>

# 或回滚到特定标签
git checkout tags/<tag-name>
```

### 2. 恢复备份数据
```bash
# 恢复数据库
cp /root/backups/$(date +%Y%m%d)/paper_push.db.backup data/database/paper_push.db

# 恢复配置
cp /root/backups/$(date +%Y%m%d)/.env.backup .env

# 或恢复整个项目
cd /root
rm -rf bio_monitor
tar -xzf /root/backups/$(date +%Y%m%d)/bio_full_backup.tar.gz
```

### 3. 重启服务
```bash
# 重新安装旧版本依赖
pip install -r requirements.txt

# 重启服务
docker-compose restart
# 或
systemctl restart cron
```

## 🔍 监控和验证

### 1. 实时监控
```bash
# 监控进程
watch -n 5 'ps aux | grep python'

# 监控日志
tail -f logs/*.log

# 监控系统资源
htop
df -h  # 磁盘使用
free -h  # 内存使用
```

### 2. 验证功能
```bash
# 测试数据源连接
python -m backend test-sources

# 测试API接口
curl http://localhost:8000/api/health
curl http://localhost:8000/api/runs | jq  # 需要安装jq

# 检查数据库
sqlite3 data/database/paper_push.db "SELECT COUNT(*) FROM papers;"

# 测试推送功能（发送测试消息）
python -m backend test-push
```

### 3. 检查定时任务
```bash
# 查看定时任务配置
crontab -l

# 查看最近的cron执行日志
grep CRON /var/log/syslog | tail -20

# 手动触发一次定时任务
cd /root/bio_monitor && python -m backend run
```

## 🚨 常见问题处理

### 问题1：依赖安装失败
```bash
# 清理pip缓存
pip cache purge

# 升级pip
pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 如果某个包安装失败，尝试单独安装
pip install <package-name> --force-reinstall
```

### 问题2：数据库迁移失败
```bash
# 检查数据库文件权限
ls -la data/database/paper_push.db

# 修复权限
chmod 664 data/database/paper_push.db

# 手动备份并重建
cp data/database/paper_push.db data/database/paper_push.db.old
python scripts/migrate_database.py --force
```

### 问题3：端口被占用
```bash
# 查找占用端口的进程
lsof -i :8000  # 替换为实际端口号
netstat -tulpn | grep :8000

# 停止占用端口的进程
kill -9 <PID>

# 或更改配置使用其他端口
```

### 问题4：git pull冲突
```bash
# 查看冲突文件
git status

# 如果本地没有重要修改，直接覆盖
git reset --hard origin/main

# 如果需要保留本地修改
git stash
git pull origin main
git stash pop
# 手动解决冲突后
git add .
git commit -m "Resolve conflicts"
```

### 问题5：Docker容器启动失败
```bash
# 查看容器日志
docker-compose logs backend
docker-compose logs frontend

# 重建容器
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 检查Docker资源
docker system df
docker system prune  # 清理未使用的资源
```

### 问题6：定时任务未执行
```bash
# 检查cron服务
systemctl status cron
systemctl restart cron

# 检查cron日志
grep CRON /var/log/syslog

# 确认定时任务配置
crontab -l

# 手动测试命令
cd /root/bio_monitor && python -m backend run

# 检查脚本路径和权限
ls -la /root/bio_monitor/
which python3
```

## 📝 最佳实践

### 1. 版本控制
- 使用git标签标记稳定版本
- 在生产环境使用特定版本，不要使用`latest`

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# 部署特定版本
git checkout tags/v1.0.0
```

### 2. 环境变量管理
- 不要在git中提交`.env`文件
- 使用`.env.example`作为模板
- 为不同环境维护不同配置

### 3. 数据库管理
- 定期备份数据库（建议每天）
- 使用数据库迁移脚本，不要手动修改结构
- 在更新前测试迁移脚本

### 4. 日志管理
- 定期清理旧日志文件
- 使用日志轮转（logrotate）
- 保留足够的日志用于问题排查

### 5. 监控告警
- 设置监控系统检测服务健康状态
- 配置告警通知（邮件、微信等）
- 定期检查系统资源使用情况

## 🛠️ 自动化脚本

可以使用提供的自动化脚本简化更新流程：

```bash
# 使用自动更新脚本
bash scripts/update_server.sh

# 脚本会自动执行：
# 1. 备份数据
# 2. 停止服务
# 3. 更新代码
# 4. 安装依赖
# 5. 数据库迁移
# 6. 重启服务
# 7. 验证状态
```

## 📞 紧急联系

如果更新过程中遇到严重问题：
1. 立即执行回滚方案
2. 查看日志文件定位问题
3. 检查备份是否完整
4. 如有必要，联系技术支持

## 📚 相关文档

- [部署指南](./deploy.md)
- [服务器部署指南](./服务器部署指南.md)
- [定时任务设置](./README_定时任务设置.md)
- [优化文档](./optimization.md)
