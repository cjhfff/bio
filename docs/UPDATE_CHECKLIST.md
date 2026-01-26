# 服务器代码更新快速检查清单

## ⏰ 更新前（5-10分钟）

- [ ] 连接到服务器 `ssh root@IP`
- [ ] 检查当前服务状态 `ps aux | grep python`
- [ ] 备份数据库 `cp data/database/paper_push.db backup/`
- [ ] 备份配置文件 `cp .env backup/`
- [ ] 记录当前版本 `git log -1`

## 🔄 更新中（10-20分钟）

- [ ] 停止运行的服务
  - Docker: `docker-compose down`
  - 进程: `kill <PID>`
  - 定时任务: `crontab -e` (注释掉)
- [ ] 拉取最新代码 `git pull origin main`
- [ ] 更新Python依赖 `pip install -r requirements.txt --upgrade`
- [ ] 更新前端依赖（如有）`cd frontend && npm install && npm run build`
- [ ] 运行数据库迁移（如有）`python scripts/migrate_database.py`
- [ ] 检查新配置项 `diff .env.example .env`

## ✅ 更新后（5-10分钟）

- [ ] 测试运行 `python -m backend test-sources`
- [ ] 重启服务
  - Docker: `docker-compose up -d`
  - 进程: `nohup python -m uvicorn backend.api.main:app &`
  - 定时任务: `crontab -e` (取消注释)
- [ ] 验证服务状态 `ps aux | grep python`
- [ ] 检查日志 `tail -f logs/api.log`
- [ ] 测试API `curl http://localhost:8000/api/health`
- [ ] 观察10-15分钟确保稳定

## 🚨 如果出现问题

### 立即回滚
```bash
# 停止服务
kill <PID> 或 docker-compose down

# 代码回滚
git reset --hard <旧版本commit>

# 恢复数据库
cp backup/paper_push.db.backup data/database/paper_push.db

# 恢复配置
cp backup/.env.backup .env

# 重启服务
docker-compose up -d
```

### 常见问题快速修复

**依赖安装失败**
```bash
pip cache purge
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**端口被占用**
```bash
lsof -i :8000
kill -9 <PID>
```

**Git冲突**
```bash
git reset --hard origin/main
```

**Docker容器失败**
```bash
docker-compose logs
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 📞 紧急联系信息

- 技术文档：`docs/UPDATE_GUIDE.md`
- 备份位置：`/root/backups/`
- 日志位置：`logs/`

## 💡 最佳实践

1. ✅ **在非高峰时段更新**（如凌晨或周末）
2. ✅ **更新前通知用户**（如果有多个用户）
3. ✅ **保留最近7天的备份**
4. ✅ **更新后监控至少15分钟**
5. ✅ **记录每次更新的时间和版本**
6. ✅ **测试环境先验证再生产更新**
7. ✅ **使用自动化脚本** `bash scripts/update_server.sh`

## 📝 更新记录模板

```
更新时间：2024-01-26 10:30
更新人员：张三
旧版本：abc123def
新版本：xyz789ghi
更新内容：
- 修复论文抓取bug
- 优化推送逻辑
- 更新依赖版本
更新结果：✅ 成功 / ❌ 失败（已回滚）
备注：更新后运行正常，无异常
```

## 🔗 相关文档

- [完整更新指南](./UPDATE_GUIDE.md)
- [服务器部署指南](./deploy.md)
- [定时任务设置](./README_定时任务设置.md)
