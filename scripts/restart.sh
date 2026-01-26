#!/bin/bash

# =================================================================
# Bio Paper System 重启服务脚本
# =================================================================

# 自动检测 Python 版本（与 start.sh 保持一致）
if [ -z "$PYTHON_EXEC" ]; then
    if command -v python3.9 &> /dev/null; then
        PYTHON_EXEC="python3.9"
    elif command -v python3 &> /dev/null; then
        PYTHON_EXEC="python3"
    elif command -v python &> /dev/null; then
        PYTHON_EXEC="python"
    fi
fi

export PYTHON_EXEC

echo ">>> 正在重启服务..."
echo "使用 Python: ${PYTHON_EXEC:-python3}"
echo ""

# 先停止服务
bash scripts/stop.sh

echo ""
echo "等待 2 秒..."
sleep 2

# 再启动服务
bash scripts/start.sh
