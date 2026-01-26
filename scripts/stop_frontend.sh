#!/bin/bash

# =================================================================
# 停止前端服务
# =================================================================

FRONTEND_PORT=3000

echo ">>> 正在停止前端服务..."

# 查找占用端口的进程
PID=$(lsof -t -i:$FRONTEND_PORT 2>/dev/null)

if [ -z "$PID" ]; then
    echo "未找到占用端口 $FRONTEND_PORT 的进程"
    
    # 尝试通过进程名查找
    PID=$(pgrep -f "vite.*3000" 2>/dev/null)
    if [ -z "$PID" ]; then
        # 再尝试查找所有 vite 进程
        PID=$(pgrep -f "vite" 2>/dev/null)
        if [ -z "$PID" ]; then
            echo "前端服务可能未运行"
            exit 0
        else
            echo "找到 vite 进程: $PID"
        fi
    else
        echo "找到 vite 进程: $PID"
    fi
else
    echo "找到占用端口 $FRONTEND_PORT 的进程: $PID"
fi

# 杀死进程
kill $PID 2>/dev/null
sleep 2

# 如果还在运行，强制杀死
if kill -0 $PID 2>/dev/null; then
    echo "进程仍在运行，强制终止..."
    kill -9 $PID 2>/dev/null
fi

# 清理所有 vite 进程
pkill -f "vite" 2>/dev/null

echo "✅ 前端服务已停止"
