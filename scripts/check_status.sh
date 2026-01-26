#!/bin/bash

# =================================================================
# Bio Paper System 检查服务状态脚本
# =================================================================

APP_PORT=8000

echo "=========================================="
echo "服务状态检查"
echo "=========================================="
echo ""

# 1. 检查端口占用
echo "[1] 检查端口 $APP_PORT 占用情况:"
PID=$(lsof -t -i:$APP_PORT 2>/dev/null)
if [ -z "$PID" ]; then
    echo "   ❌ 端口 $APP_PORT 未被占用（服务可能未运行）"
else
    echo "   ✅ 端口 $APP_PORT 被进程 $PID 占用"
    echo "   进程详情:"
    ps -p $PID -o pid,user,cmd,etime 2>/dev/null | tail -1 | sed 's/^/      /'
fi
echo ""

# 2. 检查 uvicorn 进程
echo "[2] 检查 uvicorn 进程:"
UVICORN_PIDS=$(pgrep -f "uvicorn.*backend.api.main:app" 2>/dev/null)
if [ -z "$UVICORN_PIDS" ]; then
    echo "   ❌ 未找到 uvicorn 进程"
else
    echo "   ✅ 找到 uvicorn 进程:"
    for pid in $UVICORN_PIDS; do
        ps -p $pid -o pid,user,cmd,etime 2>/dev/null | tail -1 | sed 's/^/      /'
    done
fi
echo ""

# 3. 检查健康接口
echo "[3] 检查服务健康状态:"
if curl -s http://127.0.0.1:$APP_PORT/health > /dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s http://127.0.0.1:$APP_PORT/health)
    echo "   ✅ 服务健康检查通过"
    echo "   响应: $HEALTH_RESPONSE"
else
    echo "   ❌ 服务健康检查失败（服务可能未启动或无法访问）"
fi
echo ""

# 4. 检查 API 根路径
echo "[4] 检查 API 根路径:"
if curl -s http://127.0.0.1:$APP_PORT/ > /dev/null 2>&1; then
    API_RESPONSE=$(curl -s http://127.0.0.1:$APP_PORT/ | head -c 100)
    echo "   ✅ API 可访问"
    echo "   响应: $API_RESPONSE..."
else
    echo "   ❌ API 无法访问"
fi
echo ""

# 5. 检查日志文件
echo "[5] 检查日志文件:"
if [ -f "logs/api.log" ]; then
    echo "   ✅ 日志文件存在: logs/api.log"
    echo "   最后 5 行日志:"
    tail -5 logs/api.log 2>/dev/null | sed 's/^/      /'
else
    echo "   ⚠️  日志文件不存在: logs/api.log"
fi
echo ""

echo "=========================================="
echo "检查完成"
echo "=========================================="
