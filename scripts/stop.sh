#!/bin/bash

# =================================================================
# Bio Paper System 停止服务脚本
# =================================================================

APP_PORT=8000

echo ">>> 正在停止服务..."

# 方法1: 通过端口查找并杀死进程
PID=$(lsof -t -i:$APP_PORT 2>/dev/null)

if [ -z "$PID" ]; then
    echo "未找到占用端口 $APP_PORT 的进程"
    
    # 尝试通过进程名查找
    PID=$(pgrep -f "uvicorn.*backend.api.main:app" 2>/dev/null)
    if [ -z "$PID" ]; then
        echo "未找到 uvicorn 进程，服务可能未运行"
        exit 0
    else
        echo "找到 uvicorn 进程: $PID"
    fi
else
    echo "找到占用端口 $APP_PORT 的进程: $PID"
fi

# 杀死进程
kill $PID 2>/dev/null
sleep 2

# 如果还在运行，强制杀死
if kill -0 $PID 2>/dev/null; then
    echo "进程仍在运行，强制终止..."
    kill -9 $PID 2>/dev/null
fi

# 清理所有 uvicorn 进程（防止残留）
pkill -f "uvicorn.*backend.api.main:app" 2>/dev/null

echo "✅ 服务已停止"
