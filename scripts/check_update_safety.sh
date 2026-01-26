#!/bin/bash
# 代码更新前安全检查脚本

echo "=== 代码更新前安全检查 ==="
echo ""

# 1. 检查是否有进程在运行
echo "1. 检查运行中的进程..."
if ps aux | grep -q "[p]ython.*backend\|[p]ython.*app"; then
    echo "⚠️  警告：检测到 Python 进程正在运行！"
    ps aux | grep "[p]ython.*backend\|[p]ython.*app"
    echo "建议：等待进程结束或手动停止"
else
    echo "✅ 没有进程运行"
fi
echo ""

# 2. 检查数据库备份
echo "2. 检查数据库备份..."
if ls data/paper_push.db.backup.$(date +%Y%m%d)* 1> /dev/null 2>&1; then
    echo "✅ 今天的数据库备份已存在"
    ls -lh data/paper_push.db.backup.$(date +%Y%m%d)*
else
    echo "⚠️  警告：今天还没有备份数据库！"
    echo "建议：运行 cp data/paper_push.db data/paper_push.db.backup.\$(date +%Y%m%d_%H%M%S)"
fi
echo ""

# 3. 检查磁盘空间
echo "3. 检查磁盘空间..."
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "⚠️  警告：磁盘使用率 ${DISK_USAGE}%，空间不足！"
else
    echo "✅ 磁盘空间充足 (使用率: ${DISK_USAGE}%)"
fi
df -h .
echo ""

# 4. 检查 Git 状态
echo "4. 检查 Git 状态..."
if git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "✅ 没有未提交的更改"
else
    echo "⚠️  警告：有未提交的更改！"
    git status -s
fi
echo ""

# 5. 检查即将更新的内容
echo "5. 检查待更新内容..."
git fetch origin -q 2>/dev/null
COMMITS=$(git log HEAD..origin/main --oneline 2>/dev/null | wc -l)
if [ "$COMMITS" -gt 0 ]; then
    echo "📦 有 $COMMITS 个新提交待更新："
    git log HEAD..origin/main --oneline
else
    echo "✅ 已是最新版本（或无法连接到远程仓库）"
fi
echo ""

# 6. 检查依赖变化
echo "6. 检查依赖变化..."
if git diff HEAD..origin/main requirements.txt 2>/dev/null | grep -q "^+\|^-"; then
    echo "⚠️  requirements.txt 有变化，需要重新安装依赖："
    git diff HEAD..origin/main requirements.txt
else
    echo "✅ 依赖无变化"
fi
echo ""

# 7. 检查环境配置
echo "7. 检查环境配置..."
if [ -f ".env" ]; then
    echo "✅ .env 文件存在"
    if git diff HEAD..origin/main .env.example 2>/dev/null | grep -q "^+\|^-"; then
        echo "⚠️  .env.example 有更新，建议检查是否有新的配置项："
        git diff HEAD..origin/main .env.example
    fi
else
    echo "⚠️  警告：.env 文件不存在！"
fi
echo ""

# 8. 检查定时任务
echo "8. 检查定时任务..."
if crontab -l 2>/dev/null | grep -q "backend\|app"; then
    echo "📅 当前 crontab 配置："
    crontab -l | grep "backend\|app"
else
    echo "ℹ️  未检测到 crontab 定时任务"
fi

if systemctl list-unit-files 2>/dev/null | grep -q "paper-push"; then
    echo "📅 当前 systemd timer 配置："
    systemctl status paper-push.timer --no-pager 2>/dev/null || echo "paper-push.timer 未运行"
fi
echo ""

echo "=== 检查完成 ==="
echo ""
echo "如果所有检查都通过 ✅，可以安全进行更新"
echo "如果有警告 ⚠️，请先处理相关问题"
