# 服务器部署指南

## 服务器信息
- IP: 192.3.28.35
- OS: Ubuntu 22.04 64 Bit (推荐)
- Root密码: h8Ox3dw9BbtX72P1IR

## 部署步骤

### 1. 连接服务器
```bash
ssh root@192.3.28.35
# 输入密码: h8Ox3dw9BbtX72P1IR
```

### 2. 系统初始化
```bash
# 更新系统
apt update && apt upgrade -y

# 安装必要工具
apt install -y python3 python3-pip git vim tmux

# 检查 Python 版本（应该是 3.10+）
python3 --version
```

### 3. 安装 Python 依赖
```bash
# 安装项目依赖
pip3 install openai requests feedparser biopython

# 验证安装
python3 -c "import openai, requests, feedparser; from Bio import Entrez; print('所有依赖安装成功')"
```

### 4. 上传脚本文件
方式1：使用 scp 从本地上传
```bash
# 在本地终端执行
scp doubao_standalone.py root@192.3.28.35:/root/
```

方式2：在服务器上直接创建
```bash
# 在服务器上执行
cd /root
mkdir bio_monitor
cd bio_monitor

# 使用 vim 或 nano 创建文件
vim doubao_standalone.py
# 粘贴代码内容
```

### 5. 测试运行
```bash
cd /root/bio_monitor
python3 doubao_standalone.py
```

### 6. 设置定时任务（每天自动运行）
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天早上 8 点运行）
0 8 * * * cd /root/bio_monitor && python3 doubao_standalone.py >> /root/bio_monitor/cron.log 2>&1

# 或者每天运行两次（早8点和晚8点）
0 8,20 * * * cd /root/bio_monitor && python3 doubao_standalone.py >> /root/bio_monitor/cron.log 2>&1

# 保存并退出
# vim: 按 i 进入编辑模式，输入后按 ESC，然后输入 :wq 保存退出
# nano: Ctrl+O 保存，Ctrl+X 退出
```

### 7. 使用 tmux 保持长期运行（可选）
```bash
# 创建新会话
tmux new -s bio

# 在 tmux 中运行脚本
cd /root/bio_monitor
python3 doubao_standalone.py

# 分离会话（脚本继续运行）：Ctrl+B 然后按 D
# 重新连接：tmux attach -t bio
```

## 文件结构
```
/root/bio_monitor/
├── doubao_standalone.py   # 主脚本
├── sent_list.txt          # 去重数据库（自动生成）
├── sent_meta.jsonl        # 元数据记录（自动生成）
├── 生化领域突破汇总_YYYYMMDD.txt  # 报告文件（自动生成）
└── cron.log               # 定时任务日志（如果使用 cron）
```

## 常用命令

### 查看定时任务
```bash
crontab -l
```

### 查看运行日志
```bash
tail -f /root/bio_monitor/cron.log
```

### 查看去重数据库
```bash
cat /root/bio_monitor/sent_list.txt | wc -l  # 查看已记录条数
```

### 手动运行测试
```bash
cd /root/bio_monitor
python3 doubao_standalone.py
```

### 停止定时任务
```bash
crontab -e
# 在对应行前添加 # 注释掉，保存退出
```

## 故障排查

### 问题1：连接超时
```bash
# 检查网络
ping 8.8.8.8

# 检查 DNS
nslookup api.deepseek.com
```

### 问题2：Python 依赖问题
```bash
# 重新安装依赖
pip3 install --upgrade openai requests feedparser biopython
```

### 问题3：定时任务不运行
```bash
# 检查 cron 服务
systemctl status cron

# 启动 cron 服务
systemctl start cron

# 查看 cron 日志
grep CRON /var/log/syslog
```

### 问题4：微信推送失败
```bash
# 测试 PushPlus API
curl -X POST "https://www.pushplus.plus/send" \
  -H "Content-Type: application/json" \
  -d '{"token":"353188ca63a443269aea986befa6ea48","title":"测试","content":"测试消息"}'
```

## 安全建议

1. 修改 root 密码
```bash
passwd
# 输入新密码
```

2. 创建普通用户（可选）
```bash
adduser biouser
usermod -aG sudo biouser
# 切换到普通用户运行脚本
su - biouser
```

3. 设置防火墙（可选）
```bash
apt install ufw -y
ufw allow 22/tcp  # 允许 SSH
ufw enable
```

## 监控和维护

### 查看系统资源
```bash
# CPU和内存使用
top

# 磁盘使用
df -h

# 查看运行的 Python 进程
ps aux | grep python
```

### 定期清理
```bash
# 清理旧的报告文件（保留最近7天）
find /root/bio_monitor -name "生化领域突破汇总_*.txt" -mtime +7 -delete

# 清理日志文件（保留最近30天）
find /root/bio_monitor -name "*.log" -mtime +30 -delete
```

## 备份建议

定期备份重要文件：
```bash
# 创建备份
cd /root
tar -czf bio_monitor_backup_$(date +%Y%m%d).tar.gz bio_monitor/

# 下载到本地
# 在本地终端执行：
scp root@192.3.28.35:/root/bio_monitor_backup_*.tar.gz ./
```

## 代码更新

### 快速更新（使用自动化脚本）
```bash
cd /root/bio_monitor
bash scripts/update_server.sh
```

### 手动更新步骤
1. **备份数据**
```bash
mkdir -p /root/backups/$(date +%Y%m%d)
cp -r data/ /root/backups/$(date +%Y%m%d)/
cp .env /root/backups/$(date +%Y%m%d)/
```

2. **停止服务**
```bash
# 停止运行的进程
ps aux | grep python
kill <PID>

# 或停止Docker容器
docker-compose down
```

3. **更新代码**
```bash
cd /root/bio_monitor
git pull origin main
pip3 install -r requirements.txt --upgrade
```

4. **重启服务**
```bash
# 重启Docker
docker-compose up -d

# 或重启Python服务
nohup python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 &
```

5. **验证更新**
```bash
# 查看日志
tail -f logs/api.log

# 测试服务
python3 -m backend test-sources
```

### 更新注意事项
- 更新前务必备份数据库和配置文件
- 如果有新的配置项，需要更新`.env`文件
- 如果有数据库结构变更，需要运行迁移脚本
- 更新后检查日志确保服务正常运行
- 保留备份至少7天，以便出问题时回滚

**详细的更新指南请参考：[代码更新部署指南](./UPDATE_GUIDE.md)**






