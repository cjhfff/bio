#!/bin/bash

# =================================================================
# 重启前后端服务
# =================================================================

echo "=========================================="
echo "重启前后端服务"
echo "=========================================="
echo ""

# 停止服务
echo ">>> [1/3] 停止现有服务..."
bash scripts/stop.sh
bash scripts/stop_frontend.sh

echo ""
echo "等待 2 秒..."
sleep 2

# 启动后端
echo ""
echo ">>> [2/3] 启动后端服务..."
bash scripts/start.sh

if [ $? -ne 0 ]; then
    echo "❌ 后端启动失败"
    exit 1
fi

echo ""
echo "等待 3 秒..."
sleep 3

# 启动前端
echo ""
echo ">>> [3/3] 启动前端服务..."
bash scripts/start_frontend.sh

echo ""
echo "=========================================="
echo "重启完成"
echo "=========================================="
echo ""
echo "检查服务状态: bash scripts/check_all.sh"
echo ""
