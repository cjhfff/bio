#!/bin/bash
# 服务器自动部署脚本

echo "========================================"
echo "生物化学研究监控系统 - 服务器部署脚本"
echo "========================================"

# 1. 更新系统
echo "步骤1: 更新系统..."
apt update && apt upgrade -y

# 2. 安装必要工具
echo "步骤2: 安装必要工具..."
apt install -y python3 python3-pip git vim tmux curl

# 3. 检查 Python 版本
echo "步骤3: 检查 Python 版本..."
python3 --version

# 4. 安装 Python 依赖
echo "步骤4: 安装 Python 依赖..."
pip3 install openai requests feedparser biopython

# 5. 创建工作目录
echo "步骤5: 创建工作目录..."
mkdir -p /root/bio_monitor
cd /root/bio_monitor

# 6. 验证安装
echo "步骤6: 验证依赖安装..."
python3 -c "import openai, requests, feedparser; from Bio import Entrez; print('✓ 所有依赖安装成功')"

# 7. 设置定时任务
echo "步骤7: 设置定时任务..."
(crontab -l 2>/dev/null; echo "0 8 * * * cd /root/bio_monitor && python3 doubao_standalone.py >> /root/bio_monitor/cron.log 2>&1") | crontab -

echo ""
echo "========================================"
echo "部署完成！"
echo "========================================"
echo "工作目录: /root/bio_monitor"
echo "定时任务: 每天早上8点运行"
echo ""
echo "下一步："
echo "1. 上传 doubao_standalone.py 到 /root/bio_monitor/"
echo "2. 运行测试: cd /root/bio_monitor && python3 doubao_standalone.py"
echo "3. 查看日志: tail -f /root/bio_monitor/cron.log"
echo "========================================"






